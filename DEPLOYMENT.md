# Reva Deployment Guide

Deploy Reva on a VPS using Docker Compose, managed by systemd. Docker images are built in CI and pushed to GitHub Container Registry (GHCR). Auto-deploy via GitHub Actions on push to main. cloudflared runs separately on the VPS (not part of this project).

## Architecture Overview

```
Internet → Cloudflare → Tunnel → cloudflared (separate on VPS)
                                   → localhost:3000 → [web]  (Next.js)
                                   → localhost:8000 → [api]  (FastAPI)

Docker Compose services (pre-built images from GHCR):
  [postgres :5432] [redis :6379] [api :8000] [worker] [web :3000]

Static: widget.js → Cloudflare R2 CDN
```

## Prerequisites

- VPS with 4GB+ RAM running Ubuntu/Debian
- Docker and Docker Compose installed
- Domain name with DNS managed by Cloudflare
- cloudflared installed and configured separately on the VPS
- GitHub account with repository access

## 1. One-Time VPS Setup

### Clone the repository

```bash
sudo mkdir -p /opt/reva && sudo chown $USER:$USER /opt/reva
git clone <repo-url> /opt/reva
cd /opt/reva
```

### Authenticate with GHCR

Create a GitHub Personal Access Token with `read:packages` scope, then:

```bash
echo "<PAT>" | docker login ghcr.io -u <github-username> --password-stdin
```

### Create .env.production

```bash
cp .env.production.example .env.production
nano .env.production
```

Fill in all values. Generate secrets with:

```bash
openssl rand -hex 24   # For POSTGRES_PASSWORD, REDIS_PASSWORD
openssl rand -hex 32   # For SECRET_KEY, ENCRYPTION_KEY, BETTER_AUTH_SECRET
```

> **Note:** Use `openssl rand -hex` (not `-base64`) for passwords embedded in connection URLs — base64 produces `/`, `+`, `=` which break URL parsing.

**Required variables** (see `.env.production.example` for the full list):
- `POSTGRES_PASSWORD` — database password
- `DATABASE_URL` — API connection string (uses Docker hostname `postgres`)
- `AUTH_DATABASE_URL` — Better Auth connection string (uses `postgres` hostname, standard `postgresql://` driver)
- `REDIS_PASSWORD` / `REDIS_URL` — cache/queue connection
- `SECRET_KEY`, `ENCRYPTION_KEY`, `BETTER_AUTH_SECRET` — security keys
- `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_APP_URL` — public URLs
- `OPENAI_API_KEY` — for RAG chat

### Create systemd unit

This ensures the stack starts on boot:

```bash
sudo tee /etc/systemd/system/reva.service << 'EOF'
[Unit]
Description=Reva Production Stack
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/reva
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env.production up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml --env-file .env.production down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable reva
sudo systemctl start reva
```

### Run initial migrations

```bash
docker exec $(docker ps -qf "name=api") alembic upgrade head
```

## 2. Cloudflare Tunnel Configuration

cloudflared runs as a separate service on the VPS (not managed by this project). Update hostname targets in the Cloudflare dashboard:

| Hostname | Target |
|----------|--------|
| `get-reva.ibtisam.dev` | `http://localhost:3000` |
| `get-reva-api.ibtisam.dev` | `http://localhost:8000` |

In Cloudflare dashboard: **Zero Trust** → **Networks** → **Tunnels** → select tunnel → **Public Hostnames**.

## 3. GitHub Configuration

### Secrets

Add in **Settings** → **Secrets and variables** → **Actions** → **Secrets**:

| Secret | Description |
|--------|-------------|
| `VPS_HOST` | VPS IP address or hostname |
| `VPS_USER` | SSH username on the VPS |
| `VPS_SSH_KEY` | Private SSH key for the VPS user |
| `CLOUDFLARE_API_TOKEN` | For widget R2 deployment |
| `CLOUDFLARE_ACCOUNT_ID` | For widget R2 deployment |

### Variables

Add in **Settings** → **Secrets and variables** → **Actions** → **Variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Public API URL | `https://get-reva-api.ibtisam.dev` |
| `NEXT_PUBLIC_APP_URL` | Public app URL | `https://get-reva.ibtisam.dev` |

## 4. CI/CD Pipeline

Push to `main` triggers the CI pipeline (`.github/workflows/ci.yml`):

1. **Lint** — frontend + backend in parallel
2. **Test** — backend tests + frontend tests in parallel
3. **Build & Push** — Docker images built and pushed to GHCR (tagged with commit SHA + `latest`)
4. **Deploy** — SSH into VPS, pull pre-built images, sequential service updates with health checks, auto-rollback on failure

### Deploy flow

```
CI builds images → pushes to GHCR → SSHs to VPS
  → pulls images → updates api (waits for healthy)
  → updates worker → updates web (waits for healthy)
  → if health fails → auto-rollback to previous version
```

### Manual deploy

SSH into the VPS and run:

```bash
cd /opt/reva && bash scripts/deploy.sh
```

### Rollback

```bash
cd /opt/reva && bash scripts/deploy.sh --rollback
```

### Deploy with migrations

```bash
cd /opt/reva && bash scripts/deploy.sh --migrate
```

### Local Docker builds

To build images locally (for testing), use the build override file:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.build.yml --env-file .env.production build
```

## 5. Database Migrations

Migrations are NOT auto-run during deploys. Run manually when deploying schema changes:

```bash
# Via deploy script
bash scripts/deploy.sh --migrate

# Or directly
docker exec $(docker ps -qf "name=api") alembic upgrade head
```

## 6. Database Backups

```bash
# Copy backup script
sudo cp /opt/reva/scripts/backup-db.sh /usr/local/bin/reva-backup.sh
sudo chmod +x /usr/local/bin/reva-backup.sh

# Add to crontab (daily at 3 AM)
sudo crontab -e
```

Add this line:

```cron
0 3 * * * /usr/local/bin/reva-backup.sh >> /var/log/reva-backup.log 2>&1
```

### Restore from backup

```bash
ls -lh /var/backups/reva/
docker exec -i $(docker ps -qf "name=postgres") pg_restore -U postgres -d reva < /var/backups/reva/reva_YYYYMMDD_HHMMSS.dump
```

## 7. Verify Deployment

```bash
# Check deployed version
cat /opt/reva/.current-deploy-tag

# Local health checks (from VPS)
curl http://localhost:8000/api/v1/health
curl http://localhost:3000/api/health

# External access (after cloudflared is configured)
curl https://get-reva-api.ibtisam.dev/api/v1/health
curl https://get-reva.ibtisam.dev

# Container status
docker compose -f docker-compose.prod.yml ps

# Boot persistence
sudo systemctl restart reva
```

## Resource Usage

| Service | RAM |
|---------|-----|
| API | ~300MB |
| Worker | ~500MB |
| Web | ~200MB |
| Postgres | ~400MB |
| Redis | ~128MB |
| **Total** | **~1.5GB** |

> Note: builds now happen in CI, not on the VPS, so there is no build spike on production.

## Troubleshooting

### View logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f worker
```

### Containers not starting

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f <service>
```

### Database connection errors

```bash
docker exec $(docker ps -qf "name=postgres") pg_isready -U postgres
```

### Postgres password changed but not taking effect

If you changed `POSTGRES_PASSWORD` after initial setup, the DB retains the old password (stored in the volume). Reset with:

```bash
cd /opt/reva
docker compose -f docker-compose.prod.yml --env-file .env.production down -v
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
# WARNING: This destroys all data. Restore from backup afterward.
```

### Widget not loading

1. Check GitHub Actions workflow logs for `deploy-widget.yml`
2. Verify R2 bucket public access
3. Check CORS settings on R2 bucket

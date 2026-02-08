# Reva Deployment Guide

This guide covers deploying Reva on a homelab using Coolify for orchestration.

## Architecture Overview

```
Internet → [Cloudflare Tunnel] → [Coolify Traefik :80/:443]
                                   → get-reva.ibtisam.dev  → [web :3000]  (Next.js)
                                   → get-reva-api.ibtisam.dev  → [api :8000]  (FastAPI)

Internal:  [postgres :5432] [redis :6379]
Background: [worker] (Celery)
Static:    widget.js → Cloudflare R2 CDN
```

## Prerequisites

- Homelab server with 16GB RAM running Ubuntu Server
- Docker and Docker Compose installed
- Domain name with DNS managed by Cloudflare
- GitHub account (for widget CI/CD)
- Cloudflare R2 bucket for widget hosting

## 1. Install Coolify

On your homelab server:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Access Coolify UI at `http://your-homelab-ip:8000`

## 2. Add Reva Project to Coolify

1. In Coolify UI, go to **Projects** → **New Resource**
2. Select **Docker Compose** resource type
3. Connect your GitHub repository
4. Select `docker-compose.prod.yml` as the compose file
5. Choose a name for your deployment (e.g., "reva-production")

## 3. Configure Environment Variables

In Coolify UI, add these environment variables (use `.env.production.example` as reference):

### Generate Secrets

Run these commands locally and copy the output:

```bash
# Database password
openssl rand -base64 24

# Redis password
openssl rand -base64 24

# API secret key
openssl rand -hex 32

# Encryption key
openssl rand -hex 32

# Better Auth secret
openssl rand -base64 32
```

### Required Variables

Set these in Coolify's Environment Variables section:

```env
# Database
POSTGRES_PASSWORD=<generated-above>

# Redis
REDIS_PASSWORD=<generated-above>

# Security
SECRET_KEY=<generated-above>
ENCRYPTION_KEY=<generated-above>
BETTER_AUTH_SECRET=<generated-above>

# Environment
ENVIRONMENT=production

# Domains
NEXT_PUBLIC_API_URL=https://get-reva-api.ibtisam.dev
NEXT_PUBLIC_APP_URL=https://get-reva.ibtisam.dev
ALLOWED_ORIGINS=https://get-reva.ibtisam.dev,https://www.get-reva.ibtisam.dev

# API Keys (get from respective platforms)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
RESEND_API_KEY=re_...

# Shopify (get from Partner Dashboard)
SHOPIFY_API_KEY=...
SHOPIFY_API_SECRET=...
SHOPIFY_WEBHOOK_SECRET=...

# Google OAuth (optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

## 4. Configure Domains in Coolify

1. Go to your Reva deployment in Coolify
2. For the **web** service:
   - Click on service settings
   - Set domain: `get-reva.ibtisam.dev`
   - Enable SSL (Let's Encrypt)
3. For the **api** service:
   - Click on service settings
   - Set domain: `get-reva-api.ibtisam.dev`
   - Enable SSL (Let's Encrypt)

## 5. Setup Cloudflare Tunnel

Configure Cloudflare Tunnel to route traffic to your homelab:

1. In Cloudflare dashboard, go to **Zero Trust** → **Access** → **Tunnels**
2. Create a new tunnel
3. Install the tunnel connector on your homelab
4. Add public hostnames:
   - `get-reva.ibtisam.dev` → `http://localhost:80`
   - `get-reva-api.ibtisam.dev` → `http://localhost:80`

Coolify's Traefik will handle routing based on hostname.

## 6. Deploy

1. In Coolify UI, click **Deploy** on your Reva resource
2. Coolify will:
   - Pull the latest code from GitHub
   - Build Docker images for api, worker, and web
   - Start all services
   - Configure SSL certificates
   - Setup reverse proxy routing

Monitor the deployment logs in Coolify UI.

## 7. Run Database Migrations

After the first deployment, run migrations:

```bash
# Find the API container name
docker ps | grep api

# Run migrations
docker exec -it <api-container-name> alembic upgrade head
```

Or use Coolify's exec feature in the UI.

## 8. Setup Database Backups

On your homelab server:

```bash
# Copy backup script to a permanent location
sudo cp /path/to/reva/scripts/backup-db.sh /usr/local/bin/reva-backup.sh

# Make it executable
sudo chmod +x /usr/local/bin/reva-backup.sh

# Edit the script to set correct paths
sudo nano /usr/local/bin/reva-backup.sh
# Update COMPOSE_FILE path

# Add to crontab (runs daily at 3 AM)
sudo crontab -e
```

Add this line:

```cron
0 3 * * * /usr/local/bin/reva-backup.sh >> /var/log/reva-backup.log 2>&1
```

## 9. Configure Widget CI/CD

### Setup Cloudflare R2 Bucket

1. Create an R2 bucket named `get-reva-cdn`
2. Enable public access
3. Note your Account ID

### Add GitHub Secrets

In your GitHub repository settings, add:

- `CLOUDFLARE_API_TOKEN` - Create from Cloudflare dashboard with R2 edit permissions
- `CLOUDFLARE_ACCOUNT_ID` - Your Cloudflare Account ID

### Update Workflow

Edit `.github/workflows/deploy-widget.yml`:

- Replace `get-reva-api.ibtisam.dev` with your actual API domain
- Replace `get-reva-cdn.ibtisam.dev` with your R2 bucket's public URL

The widget will auto-deploy on every push to `main` that touches `apps/widget/`.

## 10. Verify Deployment

Check these endpoints:

```bash
# API health
curl https://get-reva-api.ibtisam.dev/api/v1/health

# Web app
curl https://get-reva.ibtisam.dev

# Widget (after CI/CD runs)
curl https://get-reva-cdn.ibtisam.dev/reva-widget.iife.js
```

## Resource Usage

Expected memory usage on 16GB homelab:

| Service | RAM |
|---------|-----|
| Reva API | ~300MB |
| Reva Worker | ~500MB |
| Reva Web | ~200MB |
| Postgres | ~400MB |
| Redis | ~128MB |
| **Reva Total** | **~1.5GB** |
| Coolify + Traefik | ~600MB |
| Build spike (temporary) | +2-4GB |

Total peak usage: ~8-10GB (leaves headroom on 16GB)

## Maintenance

### View Logs

Use Coolify UI to view real-time logs for each service.

### Update Deployment

Push changes to your GitHub repository. Coolify can auto-deploy on push (configure in settings).

### Rollback

Use Coolify's deployment history to rollback to a previous version.

### Scale Services

Adjust the number of replicas in Coolify UI if needed.

### Backup Restore

To restore from backup:

```bash
# Find backup file
ls -lh /var/backups/reva/

# Restore database
docker exec -i <postgres-container> pg_restore -U postgres -d reva < /var/backups/reva/reva_20240207_030000.dump
```

## Troubleshooting

### Containers not starting

Check logs in Coolify UI or:

```bash
docker compose -f /path/to/docker-compose.prod.yml logs -f
```

### Database connection errors

Verify Postgres is healthy:

```bash
docker ps | grep postgres
docker exec <postgres-container> pg_isready -U postgres
```

### Widget not loading

1. Check GitHub Actions workflow logs
2. Verify R2 bucket public access
3. Check CORS settings on R2 bucket

### SSL certificate issues

Coolify handles Let's Encrypt automatically. Verify:
- Domains are correctly configured in Coolify
- Cloudflare Tunnel is routing correctly
- Firewall allows ports 80/443

## Support

For issues:
- Check Coolify logs
- Review application logs in Coolify UI
- Verify environment variables are set correctly
- Ensure all external API keys are valid

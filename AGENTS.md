# AGENTS.md - AI Coding Agent Guidelines

Guidelines for AI agents working in the Reva codebase.

## Project Overview

Reva is an AI-powered customer support agent for Shopify stores. This is a monorepo with:

- **Backend**: FastAPI (Python 3.12+) in `apps/api/`
- **Web Dashboard**: Next.js 15 + React 19 in `apps/web/`
- **Chat Widget**: Preact + Vite in `apps/widget/`
- **Package Managers**: `uv` (Python), `pnpm` (Node.js)

## Build/Lint/Test Commands

### Backend (apps/api)

```bash
uv run pytest                                   # Run all tests
uv run pytest tests/test_health.py              # Single test file
uv run pytest tests/test_health.py::test_root   # Single test function
uv run pytest -k "pattern"                      # Tests matching pattern
uv run ruff check . && uv run ruff format .     # Lint and format
uv run mypy app --ignore-missing-imports        # Type check
```

### Frontend (repo root)

```bash
pnpm dev         # Run all apps
pnpm build       # Build all apps
pnpm lint        # Lint all apps
pnpm format      # Format code
```

## Running the Project

### Prerequisites

- Node.js >= 20
- Python >= 3.12
- pnpm 9.1.0
- uv (Python package manager)
- Docker & Docker Compose

### Infrastructure

```bash
docker-compose up -d
```

This starts:
- **Postgres** (pgvector/pg16) on port 5432 — creates `reva` database (init script also creates `reva_auth`)
- **Redis** (7-alpine) on port 6379

### Environment Setup

Copy `.env.example` files in three locations:

```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
```

Key variables: `DATABASE_URL`, `REDIS_URL`, `AUTH_DATABASE_URL`, `BETTER_AUTH_SECRET`, API keys.

Generate secrets with: `openssl rand -hex 32`

> **Note:** Use `openssl rand -hex` (not `-base64`) for passwords embedded in connection URLs (`DATABASE_URL`, `REDIS_URL`) — base64 produces `/`, `+`, `=` which break URL parsing.

### Install & Migrate

```bash
pnpm install                                    # Node dependencies (from root)
cd apps/api && uv sync                          # Python dependencies
cd apps/api && uv run alembic upgrade head      # Run database migrations
```

### Running

```bash
pnpm dev          # Starts all apps via Turborepo (+ Celery worker)
```

Individual apps:
- API: `cd apps/api && uv run uvicorn app.main:app --reload --port 8000`
- Web: `cd apps/web && pnpm dev`
- Widget: `cd apps/widget && pnpm dev`
- Worker: `cd apps/api && uv run celery -A app.workers.celery_app worker --loglevel=info`

### Testing

```bash
cd apps/api && uv run pytest                    # API tests
cd apps/web && pnpm test                        # Web unit tests (Vitest)
cd apps/web && pnpm test:e2e                    # Web E2E (Playwright, needs dev server)
cd apps/widget && npx playwright test           # Widget E2E (needs dev server)
```

### Development URLs

| App    | URL                                  |
|--------|--------------------------------------|
| Web    | http://localhost:3000                |
| API    | http://localhost:8000                |
| API Docs | http://localhost:8000/api/v1/docs |
| Widget | http://localhost:5173                |

## Critical Rules

### Database Migrations

**NEVER write or apply Alembic migrations without explicit user approval.**

- Do NOT run `alembic revision` without asking first
- Do NOT run `alembic upgrade` or `alembic downgrade` without approval
- Always show proposed schema changes and wait for confirmation

### Multi-Tenancy

**ALWAYS scope queries by `store_id` or `organization_id`:**

```python
# CORRECT
select(Product).where(Product.id == id, Product.store_id == store.id)

# WRONG - data leak!
select(Product).where(Product.id == id)
```

### Security

- Never commit `.env` files or credentials
- Never log sensitive data (tokens, passwords, API keys)

## Code Style - Python

**Ruff config:** Line length 100, double quotes, 4-space indent

**Imports:** stdlib → third-party → first-party (`app.*`)

```python
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.product import ProductCreate
```

**Type hints required.** Use modern syntax (`list[str]`, `dict[str, Any]`, `X | None`)

**Naming:** snake_case (functions/vars), PascalCase (classes), UPPER_SNAKE (constants)

**Error handling:** Use HTTPException with status codes:

```python
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
```

## Code Style - TypeScript

**Prettier:** Single quotes, semicolons, trailing commas, 100 char lines, 2-space indent

**Imports:** react → next → third-party → `@/` aliases → relative

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
```

- Function components with TypeScript
- `'use client'` directive for client components
- shadcn/ui components from `@/components/ui/`

## Design System

See **[DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)** for complete design documentation and **[design-tokens.json](./design-tokens.json)** for the source of truth on colors, typography, and spacing.

## Architecture

### Backend Structure

```
apps/api/app/
├── api/v1/      # Route handlers (thin)
├── core/        # Config, database, deps
├── models/      # SQLAlchemy ORM
├── schemas/     # Pydantic schemas
├── services/    # Business logic (fat)
└── workers/     # Celery tasks
```

### Service Layer

Business logic in services, not route handlers:

```python
class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, store_id: UUID, data: ProductCreate) -> Product:
        product = Product(store_id=store_id, **data.model_dump())
        self.db.add(product)
        await self.db.flush()
        return product
```

### Pydantic Schemas

- `*Base` - shared fields
- `*Create` - creation payload
- `*Update` - partial (optional fields)
- `*Response` - API response with `from_attributes=True`

## Deployment

### Production Architecture

```
get-reva.ibtisam.dev     → VPS via CF Tunnel → localhost:3000 (Next.js dashboard)
get-reva-api.ibtisam.dev → VPS via CF Tunnel → localhost:8000 (FastAPI + Celery worker)
get-reva-cdn.ibtisam.dev → Cloudflare R2 CDN                  (Preact widget)
```

### Infrastructure

Single VPS running Docker Compose (managed by systemd), with cloudflared running separately:

- **postgres** — PostgreSQL with pgvector
- **redis** — Task queue and caching
- **api** — FastAPI application (2 uvicorn workers)
- **worker** — Celery worker (shares API image, healthcheck disabled)
- **web** — Next.js dashboard (standalone mode)

### CI/CD

Push to `main` triggers: lint → test → build → deploy. Widget auto-deploys to Cloudflare R2 via GitHub Actions. API + dashboard deploy via GitHub Actions SSH to VPS.

### Key Files

- `docker-compose.prod.yml` — Production Docker Compose stack
- `.github/workflows/ci.yml` — CI/CD pipeline (includes deploy job)
- `.github/workflows/deploy-widget.yml` — Widget CDN deployment
- `scripts/deploy.sh` — Manual deploy script
- `docker/postgres/init-prod.sql` — Production database init

### Environment Variables

- **VPS**: `.env.production` at `/opt/reva/.env.production` (not committed to git)
- **CI**: GitHub Secrets for deploy (`VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`) and widget R2 deploy (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`)

### Production Hardening

- Rate limiting (per-IP and per-store)
- Structured JSON logging with request IDs
- Sentry/GlitchTip error tracking
- Celery task time limits

## Testing

pytest with async support. Run tests before committing:

```python
@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/v1/products", headers=auth_headers, json={...})
    assert response.status_code == 201
```

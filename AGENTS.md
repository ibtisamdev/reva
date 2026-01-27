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

## Testing

pytest with async support. Run tests before committing:

```python
@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers: dict):
    response = await client.post("/api/v1/products", headers=auth_headers, json={...})
    assert response.status_code == 201
```

# CLAUDE.md

See **[AGENTS.md](./AGENTS.md)** for full project guidelines, code style, architecture, and setup instructions.

## Quick Commands

```bash
# Dev
pnpm dev                                        # All apps (Turbo)
pnpm build                                      # Build all
pnpm lint                                       # Lint all
pnpm format                                     # Format all

# API
cd apps/api && uv run pytest                    # Tests
cd apps/api && uv run ruff check . && uv run ruff format .  # Lint + format
cd apps/api && uv run mypy app --ignore-missing-imports      # Type check

# Web
cd apps/web && pnpm test                        # Unit tests (Vitest)
cd apps/web && pnpm test:e2e                    # E2E (Playwright)
```

## Project Structure

```
get-reva/                   # Monorepo root (Turborepo + pnpm workspaces)
├── apps/api/               # FastAPI backend (Python, uv)
├── apps/web/               # Next.js 15 dashboard (React 19, pnpm)
├── apps/widget/            # Preact chat widget (Vite, pnpm)
├── docker-compose.yml      # Postgres (pgvector) + Redis
└── AGENTS.md               # Full coding guidelines
```

## Key Patterns

- **Multi-tenancy**: Always scope DB queries by `store_id` — never fetch without it
- **Migrations**: Never write or apply Alembic migrations without explicit approval
- **Python**: Use `uv` (not pip). Ruff for linting/formatting. Type hints required.
- **Node**: Use `pnpm` (not npm/yarn). Prettier for formatting.
- **Components**: shadcn/ui from `@/components/ui/`
- **Client components**: Add `'use client'` directive
- **Service layer**: Business logic goes in `services/`, not route handlers

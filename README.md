# Reva

AI-powered customer support agent for Shopify stores.

## Overview

Reva is an AI support agent that handles customer questions, order inquiries, sales recommendations, and cart recovery for e-commerce stores. Built specifically for Shopify with plans for multi-platform support.

## Features (Roadmap)

- **Product Q&A** - Answer questions about products, shipping, policies
- **Order Status** - "Where is my order?" handling
- **Sales Assistant** - Product recommendations and comparisons
- **Cart Recovery** - Abandoned cart outreach
- **Action Agent** - Cancellations, refunds, returns

## Project Structure

```
get-reva/
├── apps/
│   ├── api/          # FastAPI backend (Python)
│   ├── web/          # Next.js dashboard (TypeScript)
│   └── widget/       # Embeddable chat widget (Preact)
├── packages/
│   ├── eslint-config/
│   └── typescript-config/
├── docs/
│   └── plans/        # Implementation plans
├── ROADMAP.md        # Product roadmap
└── docker-compose.yml
```

## Tech Stack

| Component | Technology                     |
| --------- | ------------------------------ |
| Backend   | FastAPI, SQLAlchemy, Celery    |
| Frontend  | Next.js 15, React 19, Tailwind |
| Widget    | Preact, Vite                   |
| Database  | PostgreSQL + pgvector          |
| Queue     | Redis + Celery                 |
| Auth      | Better Auth                    |
| AI        | OpenAI GPT-4o, LangChain       |

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- pnpm
- Docker (for local Postgres/Redis)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/get-reva.git
cd get-reva

# Install dependencies
pnpm install

# Start infrastructure
docker-compose up -d

# Start all apps
pnpm dev
```

### Environment Variables

Copy `.env.example` to `.env` in each app and configure:

```bash
# apps/api/.env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/reva
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your_key

# apps/web/.env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Documentation

- [Product Roadmap](ROADMAP.md) - Vision, milestones, features
- [Implementation Plans](docs/plans/) - Detailed technical plans
  - [M1: Product Q&A Bot](docs/plans/m1-product-qa.md)
- [API Documentation](apps/api/README.md) - Backend setup

## Development

```bash
# Run all apps in development
pnpm dev

# Run tests
pnpm test

# Lint and format
pnpm lint
pnpm format

# Type check
pnpm type-check
```

## Current Status

**Milestone 1: Product Q&A Bot** - In Progress

See [M1 Implementation Plan](docs/plans/m1-product-qa.md) for details.

## License

Proprietary - All rights reserved.

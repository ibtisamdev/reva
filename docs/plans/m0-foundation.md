# Technical Implementation Plan v0.1

# Reva - E-commerce AI Support Agent

> **Document Type:** Technical Implementation Plan  
> **Version:** 0.1  
> **Last Updated:** January 2026  
> **Status:** Draft

---

## Overview

**Architecture:** FastAPI monolith (Python) + Next.js dashboard (TypeScript)  
**Monorepo:** Turborepo  
**Package Manager:** uv (Python), pnpm (Node)  
**Task Queue:** Celery + Redis  
**Database:** PostgreSQL (Railway) + pgvector for embeddings

---

## Repository Structure

```
get-reva/
├── apps/
│   ├── api/                    # FastAPI backend (Python)
│   │   ├── app/
│   │   │   ├── main.py         # FastAPI app entry
│   │   │   ├── core/           # Config, security, dependencies
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   └── deps.py
│   │   │   ├── api/            # Route handlers
│   │   │   │   └── v1/
│   │   │   │       ├── chat.py
│   │   │   │       ├── shopify.py
│   │   │   │       ├── knowledge.py
│   │   │   │       └── organizations.py
│   │   │   ├── agent/          # LangChain/LangGraph
│   │   │   │   ├── graphs/     # LangGraph state machines
│   │   │   │   ├── tools/      # Agent tools (Shopify, search)
│   │   │   │   ├── prompts/    # Prompt templates
│   │   │   │   └── chains/     # LangChain chains
│   │   │   ├── integrations/   # External services
│   │   │   │   ├── shopify/
│   │   │   │   └── resend/
│   │   │   ├── knowledge/      # RAG pipeline
│   │   │   │   ├── ingestion.py
│   │   │   │   ├── embeddings.py
│   │   │   │   └── retrieval.py
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── schemas/        # Pydantic schemas
│   │   │   ├── services/       # Business logic
│   │   │   └── workers/        # Celery tasks
│   │   │       ├── celery_app.py
│   │   │       ├── sync_tasks.py
│   │   │       └── recovery_tasks.py
│   │   ├── tests/
│   │   ├── alembic/            # Database migrations
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   ├── web/                    # Next.js dashboard
│   │   ├── src/
│   │   │   ├── app/            # App router
│   │   │   ├── components/
│   │   │   ├── lib/
│   │   │   └── hooks/
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── widget/                 # Embeddable chat widget
│       ├── src/
│       ├── package.json
│       └── vite.config.ts      # Builds to single JS file
│
├── packages/
│   └── shared-types/           # Shared TypeScript types
│       ├── src/
│       └── package.json
│
├── turbo.json
├── package.json
├── docker-compose.yml          # Local dev (Postgres, Redis)
├── ROADMAP.md
└── technical-plan-v0.1.md
```

---

## Phase 0: Project Foundation (Week 1)

### 0.1 Repository Setup
- [ ] Initialize Turborepo structure
- [ ] Set up `apps/api` with uv + FastAPI skeleton
- [ ] Set up `apps/web` with Next.js 14 (App Router)
- [ ] Set up `apps/widget` with Vite + React
- [ ] Configure shared ESLint, Prettier, TypeScript configs
- [ ] Create docker-compose.yml (Postgres + Redis)

### 0.2 FastAPI Foundation
- [ ] Configure FastAPI with proper project structure
- [ ] Set up SQLAlchemy 2.0 with async support
- [ ] Set up Alembic for migrations
- [ ] Configure Pydantic settings (environment variables)
- [ ] Set up CORS for local development
- [ ] Create health check endpoint

### 0.3 Database Schema (Core Tables)
- [ ] `organizations` - Shopify stores
- [ ] `users` - Dashboard users (merchants)
- [ ] `products` - Synced from Shopify
- [ ] `knowledge_articles` - FAQs, policies
- [ ] `conversations` - Chat sessions
- [ ] `messages` - Individual messages
- [ ] Enable pgvector extension

### 0.4 Celery Setup
- [ ] Configure Celery with Redis broker
- [ ] Create basic task structure
- [ ] Set up Flower for monitoring (optional)

### 0.5 Development Tooling
- [ ] Pre-commit hooks (ruff, black, mypy)
- [ ] GitHub Actions for CI (lint, test)
- [ ] Environment variable management (.env.example)

---

## Phase 1: Milestone 1 - Product Q&A Bot (Weeks 2-4)

### 1.1 Shopify Integration
- [ ] Create Shopify Partner app
- [ ] Implement OAuth flow (install/callback endpoints)
- [ ] Store access tokens securely (encrypted)
- [ ] Product sync: initial full sync
- [ ] Product sync: webhook for updates (`products/create`, `products/update`, `products/delete`)
- [ ] Shop info sync (store name, domain, etc.)

### 1.2 Knowledge Base
- [ ] Upload endpoint for documents (PDF, TXT, URLs)
- [ ] Document processing pipeline (LangChain document loaders)
- [ ] Text chunking with appropriate overlap
- [ ] Embedding generation (OpenAI or local)
- [ ] Store embeddings in pgvector
- [ ] Sync Shopify pages as knowledge articles

### 1.3 RAG Pipeline
- [ ] Retrieval chain with pgvector
- [ ] Prompt template for e-commerce Q&A
- [ ] Source citation in responses
- [ ] Product context awareness (current page)
- [ ] Conversation memory (last N messages)

### 1.4 Chat API
- [ ] `POST /v1/chat/message` - Send message, get response
- [ ] `GET /v1/chat/conversations` - List conversations
- [ ] `GET /v1/chat/conversations/{id}` - Get conversation with messages
- [ ] Session management (anonymous + identified)
- [ ] Rate limiting per organization

### 1.5 Chat Widget
- [ ] React component with message input
- [ ] Message history display
- [ ] Typing indicator
- [ ] Source citations display
- [ ] Customizable colors/branding
- [ ] Build script -> single embeddable JS file
- [ ] Widget loader snippet for merchants

### 1.6 Dashboard (Basic)
- [ ] Authentication (NextAuth with email/password or OAuth)
- [ ] Shopify connection flow
- [ ] Products list (synced from Shopify)
- [ ] Knowledge base management (add/edit/delete articles)
- [ ] Conversations list with search
- [ ] Single conversation view
- [ ] Widget embed code generator
- [ ] Basic settings page

### 1.7 Testing & Quality
- [ ] Unit tests for RAG pipeline
- [ ] Integration tests for Shopify sync
- [ ] E2E test for chat flow
- [ ] Load testing baseline

---

## Phase 2: Milestone 2 - Order Status Agent (Weeks 5-6)

### 2.1 Customer Verification
- [ ] Order lookup by email + order number
- [ ] Verification flow in agent
- [ ] Session-based authentication state

### 2.2 Order Tools
- [ ] `get_orders_by_email` tool
- [ ] `get_order_details` tool
- [ ] `get_order_fulfillments` tool
- [ ] Order status -> friendly message mapping

### 2.3 Shipping Integration
- [ ] Shopify fulfillment tracking extraction
- [ ] Tracking status parsing
- [ ] Fulfillment status → friendly message mapping

### 2.4 Agent Enhancement
- [ ] Intent classification (Q&A vs Order Status)
- [ ] Tool calling with LangChain
- [ ] Response formatting for order info

---

## Phase 3: Milestone 3 - Sales Agent (Weeks 7-8)

### 3.1 Product Search
- [ ] Natural language product search
- [ ] Filtering by attributes (price, category, tags)
- [ ] Inventory-aware results

### 3.2 Recommendations
- [ ] Similar products
- [ ] Complementary products (upsell)
- [ ] Size/fit guidance from product data

### 3.3 LangGraph Introduction
- [ ] Define conversation state schema
- [ ] Create basic routing graph (Q&A -> Order -> Sales)
- [ ] Implement conditional edges

### 3.4 Add to Cart
- [ ] Generate Shopify cart URLs
- [ ] Track add-to-cart clicks

---

## Phase 4: Milestone 4 - Cart Recovery (Weeks 9-10)

### 4.1 Webhook Handling
- [ ] `carts/create`, `carts/update` webhooks
- [ ] `checkouts/create` webhook
- [ ] `orders/create` webhook (stop recovery)

### 4.2 Recovery Engine
- [ ] Abandoned cart detection logic
- [ ] Recovery sequence definition
- [ ] Celery scheduled tasks for follow-ups
- [ ] Sequence cancellation on purchase

### 4.3 Email Integration
- [ ] Resend API integration
- [ ] Email templates for recovery
- [ ] AI-generated personalized messages

### 4.4 Klaviyo Coordination
- [ ] Check if Klaviyo already sent email
- [ ] Avoid duplicate outreach

### 4.5 Dashboard
- [ ] Abandoned carts list
- [ ] Recovery sequence status
- [ ] Recovery analytics

---

## Phase 5: Milestone 5 - Action Agent (Weeks 11-12)

### 5.1 Permission System
- [ ] Action permissions per organization
- [ ] Configurable limits (refund cap, etc.)

### 5.2 Action Tools
- [ ] `cancel_order` tool
- [ ] `process_refund` tool
- [ ] `update_shipping_address` tool
- [ ] `apply_discount` tool

### 5.3 Confirmation Flow
- [ ] Human-in-the-loop with LangGraph
- [ ] Checkpointing for paused conversations
- [ ] Confirmation UI in widget

### 5.4 Audit Logging
- [ ] Log all actions with details
- [ ] Dashboard view for audit trail

### 5.5 Escalation
- [ ] Escalate to human when needed
- [ ] Basic escalation notification (email)

---

## Phase 6: Milestone 6 - Omnichannel (Weeks 13-14)

### 6.1 Channel Integrations
- [ ] Email inbound parsing
- [ ] WhatsApp Business integration
- [ ] SMS (Twilio) integration

### 6.2 Unified Customer Profile
- [ ] Cross-channel memory
- [ ] Customer profile system
- [ ] Channel-specific formatters

### 6.3 Helpdesk Escalation
- [ ] Slack notifications
- [ ] Zendesk ticket creation
- [ ] Unified inbox dashboard

---

## Phase 7: Milestone 7 - Analytics (Week 15)

### 7.1 Analytics Pipeline
- [ ] Event tracking infrastructure
- [ ] Metrics calculation (resolution rate, response time, etc.)

### 7.2 Dashboard
- [ ] Executive dashboard
- [ ] ROI calculator
- [ ] Weekly email reports

### 7.3 Self-Improvement
- [ ] Content gap detection
- [ ] Quality scoring system
- [ ] LangSmith integration

---

## Phase 8: Milestone 8 - Developer Platform (Week 16+)

### 8.1 Public API
- [ ] REST API with OAuth 2.0
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Rate limiting infrastructure

### 8.2 Webhooks
- [ ] Webhook system with retry logic
- [ ] Signature verification

### 8.3 Custom Tools SDK
- [ ] Tool definition format
- [ ] Tool validator
- [ ] Dynamic tool loading

### 8.4 Developer Portal
- [ ] API key management
- [ ] Usage analytics
- [ ] Sandbox environment

---

## Infrastructure & Deployment

### Local Development

```bash
# Start infrastructure
docker-compose up -d  # Postgres, Redis

# Start API
cd apps/api && uv run uvicorn app.main:app --reload

# Start Celery worker
cd apps/api && uv run celery -A app.workers.celery_app worker

# Start dashboard
cd apps/web && pnpm dev

# Start widget dev
cd apps/widget && pnpm dev
```

### Railway Deployment

| Service | Source | Notes |
|---------|--------|-------|
| API | `apps/api` Dockerfile | Main FastAPI application |
| Celery Worker | `apps/api` Dockerfile | Different start command |
| Web Dashboard | `apps/web` | Next.js auto-deploy |
| PostgreSQL | Railway managed | With pgvector extension |
| Redis | Railway managed | For Celery + caching |

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/reva

# Redis
REDIS_URL=redis://localhost:6379

# Shopify
SHOPIFY_CLIENT_ID=xxx
SHOPIFY_CLIENT_SECRET=xxx

# LLM
ANTHROPIC_API_KEY=xxx
OPENAI_API_KEY=xxx  # For embeddings

# Email
RESEND_API_KEY=xxx

# Security
SECRET_KEY=xxx
ENCRYPTION_KEY=xxx
```

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend | FastAPI (Python) | LangChain native, async support |
| Frontend | Next.js 14 | App Router, React Server Components |
| Database | PostgreSQL + pgvector | Single DB for relational + vectors |
| Task Queue | Celery + Redis | Workflow orchestration for sequences |
| LLM | Claude API | Best reasoning (per roadmap) |
| Embeddings | OpenAI text-embedding-3-small | Good quality, reasonable cost |
| Monorepo | Turborepo | Fast builds, good caching |
| Python deps | uv | Fast, modern |
| Hosting | Railway | Simple, good DX |

---

## Success Criteria

### Phase 0 Complete When:
- [ ] `turbo dev` starts all services
- [ ] API responds at `localhost:8000/health`
- [ ] Dashboard loads at `localhost:3000`
- [ ] Database migrations run successfully
- [ ] Celery worker processes test task

### Milestone 1 (MVP) Complete When:
- [ ] Merchant can install Shopify app
- [ ] Products sync automatically
- [ ] Merchant can add knowledge articles
- [ ] Widget can be embedded on store
- [ ] Customers can ask questions and get answers
- [ ] Conversations visible in dashboard

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM costs | Implement caching, use smaller models for classification |
| Shopify API rate limits | Queue requests, implement backoff |
| Vector search latency | Index optimization, caching frequent queries |
| Single point of failure | Background workers, graceful degradation |

---

## References

- [ROADMAP.md](./ROADMAP.md) - Product roadmap and feature specifications
- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Shopify Admin API](https://shopify.dev/docs/api/admin-rest)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

*This is a living document. Update as decisions are made and requirements evolve.*

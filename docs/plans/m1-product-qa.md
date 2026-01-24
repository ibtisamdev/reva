# Milestone 1: Product Q&A Bot - Implementation Plan

> **Status:** In Progress  
> **Timeline:** 4 weeks  
> **Goal:** Answer customer questions about products, shipping, policies - the basics every store needs.

---

## Overview

Milestone 1 delivers the core MVP: an AI-powered chat widget that can answer customer questions using product data and a merchant-uploaded knowledge base.

### Success Criteria

- [ ] Merchant can connect their Shopify store
- [ ] Products sync automatically from Shopify
- [ ] Merchant can upload knowledge base content (PDF, URL, text)
- [ ] Widget can be embedded on any store
- [ ] Customers can ask questions and get AI-generated answers
- [ ] Responses include citation links to sources
- [ ] Conversations are visible in the dashboard

### Success Metrics

| Metric                          | Target      |
| ------------------------------- | ----------- |
| Response time                   | < 3 seconds |
| Citation accuracy               | > 95%       |
| Widget load time                | < 500ms     |
| "I don't know" when appropriate | Yes         |

---

## Implementation Phases

M1 is broken into 4 sequential phases:

| Phase                                        | Focus                  | Duration  | Status      |
| -------------------------------------------- | ---------------------- | --------- | ----------- |
| [Phase 1](m1-phases/phase-1-rag-pipeline.md) | Core AI/RAG Pipeline   | 1.5 weeks | Not Started |
| [Phase 2](m1-phases/phase-2-widget-api.md)   | Widget API Integration | 0.5 weeks | Not Started |
| [Phase 3](m1-phases/phase-3-dashboard.md)    | Dashboard Features     | 1 week    | Not Started |
| [Phase 4](m1-phases/phase-4-shopify.md)      | Shopify Integration    | 1 week    | Not Started |

### Why This Order?

1. **Phase 1 (RAG)** - Build the "brain" first. This is the core value proposition.
2. **Phase 2 (Widget)** - Connect the existing widget UI to the API for an end-to-end demo.
3. **Phase 3 (Dashboard)** - Give merchants a way to manage content and view conversations.
4. **Phase 4 (Shopify)** - Add real store data last (requires Partner account setup).

This order allows for:

- Fastest path to a working demo (can use mock data initially)
- Parallel work if needed (dashboard can be built while testing RAG)
- No external dependencies until Phase 4

---

## Architecture

```
Widget                API                    Services                 External
  |                    |                        |                        |
  | POST /chat/messages|                        |                        |
  |------------------>|                        |                        |
  |                    | retrieve_context()     |                        |
  |                    |----------------------->|                        |
  |                    |                        | pgvector similarity    |
  |                    |                        |----------------------->|
  |                    |                        |<-----------------------|
  |                    |<-----------------------|                        |
  |                    | generate_response()    |                        |
  |                    |----------------------->|                        |
  |                    |                        | OpenAI chat completion |
  |                    |                        |----------------------->|
  |                    |                        |<-----------------------|
  |                    |<-----------------------|                        |
  |<------------------|                        |                        |
```

### Key Components

| Component           | Location                     | Purpose                       |
| ------------------- | ---------------------------- | ----------------------------- |
| Knowledge Ingestion | `app/knowledge/ingestion.py` | Process docs, chunk, embed    |
| RAG Retrieval       | `app/knowledge/retrieval.py` | Vector search in pgvector     |
| Chat Service        | `app/services/chat.py`       | Orchestrate RAG + LLM         |
| Chat API            | `app/api/v1/chat.py`         | HTTP endpoints                |
| Widget              | `apps/widget/`               | Embeddable UI (Preact)        |
| Dashboard           | `apps/web/`                  | Merchant management (Next.js) |

---

## Technical Decisions

| Decision     | Choice                        | Rationale                             |
| ------------ | ----------------------------- | ------------------------------------- |
| LLM          | OpenAI GPT-4o                 | Best quality, good function calling   |
| Embeddings   | OpenAI text-embedding-3-small | Good quality, reasonable cost         |
| Vector Store | pgvector (PostgreSQL)         | Single DB, no extra infrastructure    |
| Chunking     | 512 tokens, 50 overlap        | Balance between context and precision |

---

## Dependencies

### External Services

- OpenAI API (GPT-4o + embeddings)
- PostgreSQL with pgvector extension

### Internal Prerequisites

- Phase 0 complete (database, auth, basic API structure)

---

## Deliverables Checklist

From [ROADMAP.md](../../ROADMAP.md#milestone-1-product-qa-bot-mvp):

- [ ] Shopify OAuth app installation flow (Phase 4)
- [ ] Product sync pipeline - initial + incremental (Phase 4)
- [ ] Knowledge base upload - PDF, URL, text (Phase 1 + 3)
- [ ] RAG pipeline with product context (Phase 1)
- [ ] Embeddable chat widget (Phase 2)
- [ ] Merchant dashboard (Phase 3)
- [ ] ~~Shopify App Store listing~~ (Deferred to post-MVP)

---

## Risk Mitigation

| Risk                   | Mitigation                                      |
| ---------------------- | ----------------------------------------------- |
| LLM response quality   | Careful prompt engineering, citation validation |
| Vector search latency  | Index optimization, caching frequent queries    |
| OpenAI rate limits     | Implement retry with backoff, queue requests    |
| Large document uploads | Async processing with Celery                    |

---

## References

- [ROADMAP.md - Milestone 1](../../ROADMAP.md#milestone-1-product-qa-bot-mvp)
- [M0 Foundation Plan](m0-foundation.md)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

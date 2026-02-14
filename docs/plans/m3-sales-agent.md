# Milestone 3: Sales & Recommendation Agent - Implementation Plan

> **Status:** In Progress
> **Timeline:** 3 weeks
> **Goal:** Transform from support-only to sales assistant that helps customers find and buy products.

---

## Overview

Milestone 3 evolves Reva from a Q&A bot into an intelligent sales agent that can help customers discover products, provide recommendations, and guide purchase decisions using natural language processing and LangGraph state machines.

### Success Criteria

- [x] Natural language product search ("I need a gift for my mom who likes gardening")
- [x] Smart product recommendations based on customer preferences
- [x] Product comparison with side-by-side feature analysis
- [ ] ~~Size and fit guidance using size charts and customer reviews~~ — DEFERRED (see [deferred-features.md](deferred-features.md#size--fit-guidance-originally-phase-2-task-23))
- [x] Upsell and cross-sell suggestions for relevant add-ons
- [x] Inventory-aware responses (only recommend in-stock items)
- [ ] ~~Add-to-cart deep links for seamless purchase flow~~ — DEFERRED (see [deferred-features.md](deferred-features.md#add-to-cart-deep-links-originally-m3-roadmap))
- [x] LangGraph state machine for conversation routing
- [ ] ~~Sales analytics dashboard for merchants~~ — DEFERRED (see [deferred-features.md](deferred-features.md#sales-analytics-dashboard-originally-m3-success-criteria))

### Success Metrics

| Metric                      | Target      | Status  |
| --------------------------- | ----------- | ------- |
| Product search accuracy     | > 85%       | Active  |
| Recommendation relevance    | > 80%       | Active  |
| Response time (with search) | < 5 seconds | Active  |
| Inventory sync accuracy     | > 99%       | Active  |
| Add-to-cart conversion rate | > 15%       | DEFERRED |
| Size guidance accuracy      | > 90%       | DEFERRED |

---

## Implementation Phases

M3 is broken into 3 sequential phases:

| Phase                                            | Focus                            | Duration | Status             |
| ------------------------------------------------ | -------------------------------- | -------- | ------------------ |
| [Phase 1](m3-phases/phase-1-product-search.md)   | Product Search & Discovery       | 1 week   | Partially Complete |
| [Phase 2](m3-phases/phase-2-recommendations.md)  | Recommendations Engine           | 1 week   | Partially Complete |
| [Phase 3](m3-phases/phase-3-langgraph-router.md) | LangGraph Router & State Machine | 1 week   | Complete           |

### Why This Order?

1. **Phase 1 (Search)** - Build the foundation for finding products using NLP and semantic search.
2. **Phase 2 (Recommendations)** - Add intelligence for suggesting relevant products and upsells.
3. **Phase 3 (LangGraph)** - Implement sophisticated conversation routing and state management.

This order allows for:

- Incremental value delivery (search works before recommendations)
- Testing and refinement of core algorithms before complex routing
- Clear separation of concerns between search, recommendations, and conversation flow

---

## Architecture

```
Widget                API                    Services                 External
  |                    |                        |                        |
  | POST /chat/messages|                        |                        |
  |------------------>|                        |                        |
  |                    | LangGraph Router       |                        |
  |                    |----------------------->|                        |
  |                    |                        | Intent Classification  |
  |                    |                        |----------------------->|
  |                    |                        |<-----------------------|
  |                    |                        |                        |
  |                    |                        | Product Search         |
  |                    |                        |----------------------->|
  |                    |                        | Vector + Text Search   |
  |                    |                        |<-----------------------|
  |                    |                        |                        |
  |                    |                        | Recommendation Engine  |
  |                    |                        |----------------------->|
  |                    |                        | Similarity + Rules     |
  |                    |                        |<-----------------------|
  |                    |                        |                        |
  |                    |                        | Inventory Check        |
  |                    |                        |----------------------->|
  |                    |                        | Shopify API            |
  |                    |                        |<-----------------------|
  |                    |<-----------------------|                        |
  |<------------------|                        |                        |
```

### LangGraph State Machine

```
┌────────────────────────────────────────────────────────────┐
│                   SALES AGENT GRAPH                        │
│                                                            │
│  ┌─────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  START  │────▶│   CLASSIFY   │────▶│    ROUTE     │    │
│  └─────────┘     │    INTENT    │     └──────┬───────┘    │
│                  └──────────────┘            │             │
│            ┌─────────────┬─────────────┬─────┴────┐       │
│            ▼             ▼             ▼          ▼       │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌────────┐  │
│     │ PRODUCT  │  │  ORDER   │  │   FAQ    │ │ SMALL  │  │
│     │  SEARCH  │  │  STATUS  │  │  ANSWER  │ │  TALK  │  │
│     └────┬─────┘  └──────────┘  └──────────┘ └────────┘  │
│          ▼                                                │
│     ┌──────────┐                                          │
│     │  FILTER  │                                          │
│     │  & RANK  │                                          │
│     └────┬─────┘                                          │
│          ▼                                                │
│     ┌──────────┐                                          │
│     │ RECOMMEND│                                          │
│     └────┬─────┘                                          │
│          └──────────────────────────────────────────┐     │
│                                                     ▼     │
│                                              ┌──────────┐ │
│                                              │ RESPOND  │ │
│                                              └──────────┘ │
└────────────────────────────────────────────────────────────┘
```

### Key Components

| Component              | Location                                | Purpose                                       |
| ---------------------- | --------------------------------------- | --------------------------------------------- |
| Search Service         | `app/services/search_service.py`        | Hybrid vector + full-text search (RRF)        |
| Recommendation Service | `app/services/recommendation_service.py`| Similar, upsell, cross-sell, compare          |
| LangGraph State        | `app/services/graph/state.py`           | ConversationState TypedDict (10 fields)       |
| Intent Classifier      | `app/services/graph/nodes.py`           | GPT-4o intent classification (6 intents)      |
| Router                 | `app/services/graph/router.py`          | Conditional routing by intent + confidence    |
| Graph Nodes            | `app/services/graph/nodes.py`           | search, recommend, support, general, clarify  |
| Graph Workflow         | `app/services/graph/workflow.py`        | LangGraph compilation (create_sales_graph)    |
| System Prompts         | `app/services/graph/prompts.py`         | 6 specialized node prompts                    |
| Product Tools          | `app/services/tools/product_tools.py`   | 6 LangChain tools (per-request factory)       |
| Search Schemas         | `app/schemas/search.py`                 | ProductFilters, SearchRequest, SearchResponse |
| Search API             | `app/api/v1/search.py`                  | POST /products/search                         |
| Recommendations API    | `app/api/v1/recommendations.py`         | similar, upsell, compare endpoints            |
| Chat Service           | `app/services/chat_service.py`          | LangGraph orchestration entry point           |

---

## Technical Decisions

| Decision             | Choice                              | Rationale                                       |
| -------------------- | ----------------------------------- | ----------------------------------------------- |
| Search Engine        | Hybrid (Vector + Text) with RRF     | Reciprocal Rank Fusion combines both effectively |
| Recommendation       | Content-based (embeddings + rules)  | Works without user identity; sufficient for MVP  |
| State Management     | LangGraph                           | Visual workflow, easy debugging                  |
| Product Embeddings   | OpenAI text-embedding-3-small       | Consistent with existing knowledge base          |
| Inventory Data       | Shopify sync to Product.variants    | Webhook-driven, no real-time API calls needed    |
| Intent Classification| GPT-4o with temp=0, JSON response   | High accuracy, structured output                 |
| Tool Architecture    | Per-request factory pattern          | Multi-tenant isolation via closure-bound tools   |

---

## Dependencies

### External Services

- OpenAI API (GPT-4o for chat + intent classification, text-embedding-3-small for embeddings)
- Shopify Admin API (product data synced to local DB via webhooks)
- LangGraph + LangChain Core (conversation state machine and tool framework)

### Python Packages (already in pyproject.toml)

```toml
langgraph >= 0.2.0
langchain-core >= 0.3.0
langchain-openai >= 0.3.0
pgvector >= 0.3.6
```

### Internal Prerequisites

- M1 complete (RAG pipeline, chat API)
- M2 complete (Shopify integration, product sync)
- Product embeddings generated and indexed

---

## Deliverables Checklist

From [ROADMAP.md](../../ROADMAP.md#milestone-3-sales--recommendation-agent):

- [x] Natural language product search
- [x] Recommendation engine
- [x] Product comparison generation
- [ ] ~~Size/fit guidance system~~ — DEFERRED (see [deferred-features.md](deferred-features.md))
- [x] Inventory-aware responses
- [ ] ~~Add-to-cart deep links~~ — DEFERRED (see [deferred-features.md](deferred-features.md))
- [ ] ~~Sales analytics dashboard~~ — DEFERRED (see [deferred-features.md](deferred-features.md))
- [x] LangGraph state machine implementation
- [x] Intent classification system
- [x] Upsell and cross-sell logic

---

## Risk Mitigation

| Risk                       | Mitigation                                                                     |
| -------------------------- | ------------------------------------------------------------------------------ |
| Poor search relevance      | Hybrid search (RRF) combines vector + keyword; tune weights if needed          |
| Slow recommendation engine | Queries scoped to store_id with pgvector indexes; fast for typical catalog sizes|
| LangGraph complexity       | Started simple with 6 nodes; add complexity incrementally                      |
| Inventory sync delays      | Data synced from Shopify webhooks to Product.variants JSONB; no real-time dependency |
| High OpenAI costs          | Intent classification uses temp=0 + max_tokens=100; tool loop capped at 3 iterations |

---

## References

- [ROADMAP.md - Milestone 3](../../ROADMAP.md#milestone-3-sales--recommendation-agent)
- [M1 Product Q&A Bot](m1-product-qa.md)
- [M2 Shopify Integration](m2-shopify-integration.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Shopify Admin API](https://shopify.dev/docs/api/admin)

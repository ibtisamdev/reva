# Milestone 3: Sales & Recommendation Agent - Implementation Plan

> **Status:** Not Started  
> **Timeline:** 3 weeks  
> **Goal:** Transform from support-only to sales assistant that helps customers find and buy products.

---

## Overview

Milestone 3 evolves Reva from a Q&A bot into an intelligent sales agent that can help customers discover products, provide recommendations, and guide purchase decisions using natural language processing and LangGraph state machines.

### Success Criteria

- [ ] Natural language product search ("I need a gift for my mom who likes gardening")
- [ ] Smart product recommendations based on customer preferences
- [ ] Product comparison with side-by-side feature analysis
- [ ] Size and fit guidance using size charts and customer reviews
- [ ] Upsell and cross-sell suggestions for relevant add-ons
- [ ] Inventory-aware responses (only recommend in-stock items)
- [ ] Add-to-cart deep links for seamless purchase flow
- [ ] LangGraph state machine for conversation routing
- [ ] Sales analytics dashboard for merchants

### Success Metrics

| Metric                      | Target      |
| --------------------------- | ----------- |
| Product search accuracy     | > 85%       |
| Recommendation relevance    | > 80%       |
| Add-to-cart conversion rate | > 15%       |
| Size guidance accuracy      | > 90%       |
| Response time (with search) | < 5 seconds |
| Inventory sync accuracy     | > 99%       |

---

## Implementation Phases

M3 is broken into 3 sequential phases:

| Phase                                            | Focus                            | Duration | Status      |
| ------------------------------------------------ | -------------------------------- | -------- | ----------- |
| [Phase 1](m3-phases/phase-1-product-search.md)   | Product Search & Discovery       | 1 week   | Not Started |
| [Phase 2](m3-phases/phase-2-recommendations.md)  | Recommendations Engine           | 1 week   | Not Started |
| [Phase 3](m3-phases/phase-3-langgraph-router.md) | LangGraph Router & State Machine | 1 week   | Not Started |

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

| Component              | Location                           | Purpose                       |
| ---------------------- | ---------------------------------- | ----------------------------- |
| Product Search Service | `app/services/product_search.py`   | NLP-powered product discovery |
| Recommendation Engine  | `app/services/recommendations.py`  | Similar products, upsells     |
| LangGraph Router       | `app/services/langgraph_router.py` | Conversation state management |
| Inventory Service      | `app/services/inventory.py`        | Real-time stock checking      |
| Sales Analytics        | `app/services/sales_analytics.py`  | Conversion tracking           |
| Product API            | `app/api/v1/products.py`           | Product search endpoints      |

---

## Technical Decisions

| Decision           | Choice                        | Rationale                                  |
| ------------------ | ----------------------------- | ------------------------------------------ |
| Search Engine      | Hybrid (Vector + Text)        | Best of semantic and keyword search        |
| Recommendation     | Collaborative + Content       | Leverage both user behavior and features   |
| State Management   | LangGraph                     | Visual workflow, easy debugging            |
| Product Embeddings | OpenAI text-embedding-3-small | Consistent with existing knowledge base    |
| Inventory Sync     | Real-time Shopify API         | Ensure accurate stock information          |
| Size Guidance      | Rule-based + ML               | Combine size charts with customer feedback |

---

## Dependencies

### External Services

- OpenAI API (GPT-4o + embeddings)
- Shopify Admin API (product data, inventory)
- LangGraph (conversation state management)

### Internal Prerequisites

- M1 complete (RAG pipeline, chat API)
- M2 complete (Shopify integration, product sync)
- Product embeddings generated and indexed

---

## Deliverables Checklist

From [ROADMAP.md](../../ROADMAP.md#milestone-3-sales--recommendation-agent):

- [ ] Natural language product search
- [ ] Recommendation engine
- [ ] Product comparison generation
- [ ] Size/fit guidance system
- [ ] Inventory-aware responses
- [ ] Add-to-cart deep links
- [ ] Sales analytics dashboard
- [ ] LangGraph state machine implementation
- [ ] Intent classification system
- [ ] Upsell and cross-sell logic

---

## Risk Mitigation

| Risk                       | Mitigation                                      |
| -------------------------- | ----------------------------------------------- |
| Poor search relevance      | A/B test different embedding strategies         |
| Slow recommendation engine | Cache popular recommendations, async processing |
| LangGraph complexity       | Start simple, add complexity incrementally      |
| Inventory sync delays      | Implement fallback to last known stock levels   |
| Size guidance accuracy     | Collect feedback, continuously improve rules    |
| High OpenAI costs          | Implement caching, optimize prompt efficiency   |

---

## References

- [ROADMAP.md - Milestone 3](../../ROADMAP.md#milestone-3-sales--recommendation-agent)
- [M1 Product Q&A Bot](m1-product-qa.md)
- [M2 Shopify Integration](m2-shopify-integration.md)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Shopify Admin API](https://shopify.dev/docs/api/admin)

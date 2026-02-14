# Phase 1: Product Search & Discovery

> **Parent:** [M3 Sales & Recommendation Agent](../m3-sales-agent.md)
> **Duration:** 1 week
> **Status:** Partially Complete
> **Dependencies:** M1 (RAG pipeline), M2 (Shopify integration)

---

## Goal

Build a natural language product search system that can understand customer intent and find relevant products using semantic search, keyword matching, and intelligent filtering.

---

## Tasks

### 1.1 Product Embedding Generation

**Location:** `apps/api/app/models/product.py` (embedding column), `apps/api/app/services/embedding_service.py` (generation)
**Status:** COMPLETED

- [x] Generate embeddings for product titles, descriptions, and tags
- [x] Create composite embeddings combining multiple product fields
- [x] Store embeddings with pgvector (1536-dim on Product model directly)
- [x] Batch processing via Shopify sync pipeline
- [x] Handle product updates and re-embedding via Shopify webhooks

> **Implementation Note:** Embeddings live directly on the `Product.embedding` column (1536-dim pgvector) rather than a separate `product_embeddings` table. This simplifies queries by avoiding joins and keeps the search service a single-table operation. The existing `EmbeddingService` (OpenAI text-embedding-3-small) generates embeddings during Shopify product sync.

### 1.2 Hybrid Search Engine

**Location:** `apps/api/app/services/search_service.py`
**Status:** COMPLETED

- [x] Implement semantic search using product embeddings (cosine distance via pgvector)
- [x] Add keyword search using PostgreSQL full-text search (tsvector + ts_rank)
- [x] Combine results with Reciprocal Rank Fusion (RRF, K=60)
- [x] Support search filters (price range, category, tags, vendor, availability)
- [x] Implement search result ranking algorithm

**Key Methods:**

```python
class SearchService:
    async def hybrid_search(query, store_id, filters, limit) -> list[ProductSearchResult]
    async def _vector_search(query_embedding, store_id, limit) -> list[Product]
    async def _fulltext_search(query, store_id, limit) -> list[Product]
    def _apply_filters(query, filters) -> Query
    def _reciprocal_rank_fusion(vector_results, text_results, k=60) -> list[Product]
    async def get_product_by_id(product_id, store_id) -> Product | None
```

> **Implementation Note:** Uses Reciprocal Rank Fusion (RRF with K=60) instead of weighted scoring (the original plan used `semantic_weight=0.7, keyword_weight=0.3`). Both vector and full-text results are fetched at 2x limit, then combined via RRF. This is a standard ranking technique from information retrieval literature.

### 1.3 Search Intent Classification

**Location:** `apps/api/app/services/graph/nodes.py` (`classify_intent` function)
**Status:** COMPLETED (moved to Phase 3)

- [x] Classify search queries into categories
- [x] Extract key attributes from natural language
- [x] Handle ambiguous queries with clarifying questions

> **Implementation Note:** Intent classification was implemented in Phase 3 as part of the LangGraph workflow, not as a standalone `search_intent.py`. It uses GPT-4o with temp=0 and classifies into 6 intents (product_search, product_recommendation, order_status, faq_support, small_talk, complaint). See [Phase 3](phase-3-langgraph-router.md#32-intent-classification-node) for details.

### 1.4 Product Filtering & Ranking

**Location:** `apps/api/app/services/search_service.py` (`_apply_filters` method), `apps/api/app/schemas/search.py` (`ProductFilters` model)
**Status:** COMPLETED

- [x] Inventory-aware filtering (`in_stock_only`) — EXISTS query on variants JSONB
- [x] Price range filtering — via first variant price from JSONB
- [x] Category filtering — `product_type` column
- [x] Tag-based filtering — PostgreSQL array overlap
- [x] Vendor filtering (added beyond original plan)
- [ ] ~~Popularity-based ranking boost~~ — not implemented (no popularity data)
- [ ] ~~Personalization based on store preferences~~ — DEFERRED

**ProductFilters Schema:**

```python
class ProductFilters(BaseModel):
    price_min: float | None = None
    price_max: float | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    vendors: list[str] | None = None  # Added beyond original plan
    in_stock_only: bool = False
```

### 1.5 Search API Endpoints

**Location:** `apps/api/app/api/v1/search.py`
**Status:** PARTIALLY COMPLETE

- [x] `POST /api/v1/products/search` — Natural language product search
- [ ] `GET /api/v1/products/suggestions` — Search suggestions/autocomplete (not built)
- [ ] `GET /api/v1/products/filters` — Available filter options for store (not built)
- [ ] `POST /api/v1/products/embeddings/refresh` — Regenerate embeddings (not built)

> **Implementation Note:** Only the core search endpoint was built. It's registered under the `/products` prefix via `router.py`. Request/response schemas are in `app/schemas/search.py` (SearchRequest, SearchResponse, ProductSearchResult).

### 1.6 Search Analytics & Optimization

**Location:** Not built
**Status:** DEFERRED → [deferred-features.md](../deferred-features.md#search-analytics--optimization-originally-phase-1-task-16)

- [ ] ~~Track search queries and results clicked~~
- [ ] ~~Identify zero-result searches for improvement~~
- [ ] ~~A/B test different ranking algorithms~~
- [ ] ~~Monitor search performance metrics~~
- [ ] ~~Generate search insights for merchants~~

### 1.7 Inventory Integration

**Location:** `apps/api/app/services/search_service.py` (`_apply_filters` with `in_stock_only`), `apps/api/app/models/product.py` (`variants` JSONB column)
**Status:** COMPLETED (via Shopify sync)

- [x] Inventory data from Shopify synced to `Product.variants` JSONB
- [x] Variant-level inventory tracking (per-variant `inventory_quantity` in JSONB)
- [x] Filter by stock availability in search
- [ ] ~~Real-time Shopify API calls during search~~ — not needed; data synced via webhooks
- [ ] ~~Cache inventory with TTL~~ — not needed; webhook-driven sync
- [ ] ~~Low-stock warnings in search results~~ — not implemented

> **Implementation Note:** Inventory data comes from Shopify product sync and lives in `Product.variants` JSONB column. Each variant object contains `inventory_quantity`. The search service's `_apply_filters` method checks inventory via an EXISTS subquery on the JSONB array. No separate `InventoryService` was needed.

---

## Files Created/Modified

| File                         | Action   | Purpose                                        |
| ---------------------------- | -------- | ---------------------------------------------- |
| `app/services/search_service.py` | Created  | Hybrid search engine (vector + full-text + RRF) |
| `app/schemas/search.py`         | Created  | ProductFilters, SearchRequest, SearchResponse   |
| `app/api/v1/search.py`          | Created  | POST /products/search endpoint                  |
| `app/api/v1/router.py`          | Modified | Registered search router under /products prefix |

---

## Dependencies

No new dependencies needed. The search service uses existing packages already in `pyproject.toml`:

- `pgvector` — vector similarity operations
- `langchain-openai` — embedding generation (via existing EmbeddingService)
- `sqlalchemy` — full-text search queries

---

## Testing

- [x] Unit test: hybrid search combines vector + fulltext results (`tests/test_search_service.py::TestHybridSearch`)
- [x] Unit test: filters work correctly — price, category, stock, vendor, tags (`tests/test_search_service.py::TestApplyFilters`)
- [x] Unit test: RRF score computation (`tests/test_search_service.py::TestRRF`)
- [x] Unit test: product-to-search-result conversion (`tests/test_search_service.py::TestProductToSearchResult`)
- [ ] Integration test: full search flow with real product data
- [ ] Performance test: search response time under load
- [ ] ~~A/B test: different ranking algorithms~~ — DEFERRED

---

## Acceptance Criteria

1. **Semantic Search**: Finds relevant products even without exact keyword matches — DONE (via pgvector cosine distance)
2. **Hybrid Ranking**: Combines semantic and keyword relevance effectively — DONE (RRF with K=60)
3. **Real-time Inventory**: Only shows in-stock products when requested — DONE (via synced variant data)
4. **Filtering**: Supports price, category, tags, vendor, and availability filters — DONE
5. **Performance**: Search results returned within 2 seconds — not formally benchmarked
6. **Analytics**: ~~Tracks search performance~~ — DEFERRED

---

## Notes

- Hybrid search uses RRF (Reciprocal Rank Fusion) which is superior to simple weighted scoring for combining ranked lists
- Product embeddings live on the Product model itself, avoiding an extra join table
- The search service is multi-tenant safe — all queries scoped by store_id
- Search suggestions and filter options endpoints can be added later without changing the core search logic

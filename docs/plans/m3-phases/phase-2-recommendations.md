# Phase 2: Recommendations Engine

> **Parent:** [M3 Sales & Recommendation Agent](../m3-sales-agent.md)
> **Duration:** 1 week
> **Status:** Partially Complete
> **Dependencies:** Phase 1 (Product Search), M2 (Shopify integration)

---

## Goal

Build a recommendation system that suggests relevant products, upsells, and cross-sells, and provides side-by-side product comparisons to help customers make informed purchase decisions.

---

## Tasks

### 2.1 Similar Products Engine

**Location:** `apps/api/app/services/recommendation_service.py`
**Status:** COMPLETED

- [x] Implement content-based similarity using product embeddings (cosine distance via pgvector)
- [x] Calculate product similarity scores
- [x] Filter out-of-stock and discontinued products (status == "active")
- [x] Exclude the source product from results
- [x] Rank by similarity score

**Key Method:**

```python
class RecommendationService:
    async def get_similar_products(
        self, product_id: UUID, store_id: UUID, limit: int = 5
    ) -> list[ProductSearchResult]:
        """Find products similar to the given product via embedding cosine distance."""
```

> **Implementation Note:** Uses the source product's `embedding` column directly for pgvector cosine distance comparison. Simpler than the originally planned approach (no `price_tolerance` or `same_category_only` parameters).

### 2.2 Upsell & Cross-sell Logic

**Location:** `apps/api/app/services/recommendation_service.py`
**Status:** PARTIALLY COMPLETE

- [x] Identify upsell opportunities — `get_upsell_products()`: 10-30% higher price, same category or vendor
- [x] Generate cross-sell suggestions — `get_cross_sell_products()`: overlapping tags, different product type
- [ ] Rule-based product bundles — not built
- [ ] ~~Customer purchase history patterns~~ — DEFERRED (requires personalization)
- [ ] ~~Revenue impact calculation~~ — not built

**Key Methods:**

```python
class RecommendationService:
    async def get_upsell_products(
        self, product_id: UUID, store_id: UUID, limit: int = 3
    ) -> list[ProductSearchResult]:
        """Find higher-priced alternatives (10-30% more, same category/vendor)."""

    async def get_cross_sell_products(
        self, product_id: UUID, store_id: UUID, limit: int = 3
    ) -> list[ProductSearchResult]:
        """Find complementary products (overlapping tags, different type)."""
```

> **Implementation Note:** Upsell and cross-sell are methods on RecommendationService, not a separate `upsell_engine.py`. Both are exposed as LangChain tools via the `suggest_alternatives` tool in `product_tools.py`, which calls both methods and combines results.

### 2.3 Size & Fit Guidance System

**Location:** Not built
**Status:** DEFERRED → [deferred-features.md](../deferred-features.md#size--fit-guidance-originally-phase-2-task-23)

- [ ] ~~Parse and store product size charts~~
- [ ] ~~Implement size recommendation algorithm~~
- [ ] ~~Analyze customer reviews for fit feedback~~
- [ ] ~~Handle different sizing systems (US, EU, UK)~~
- [ ] ~~Provide size conversion and guidance~~

> **Note:** The LLM can already answer basic sizing questions from product descriptions and variant names (e.g., "S, M, L, XL"). A structured size guidance system with dedicated DB tables is deferred until apparel-focused merchants request it.

### 2.4 Personalization Engine

**Location:** Not built
**Status:** DEFERRED → [deferred-features.md](../deferred-features.md#personalization-engine-originally-phase-2-task-24)

- [ ] ~~Track customer browsing and purchase behavior~~
- [ ] ~~Build customer preference profiles~~
- [ ] ~~Implement collaborative filtering for recommendations~~
- [ ] ~~Consider seasonal and trending products~~
- [ ] ~~Handle cold start problem for new customers~~

### 2.5 Product Comparison Generator

**Location:** `apps/api/app/services/recommendation_service.py`
**Status:** COMPLETED

- [x] Generate side-by-side product comparisons
- [x] Extract and compare key product features (title, description, price, vendor, type, tags)
- [x] Include per-variant pricing and availability
- [x] Format comparison as structured dict

**Key Method:**

```python
class RecommendationService:
    async def compare_products(
        self, product_ids: list[UUID], store_id: UUID
    ) -> dict:
        """Compare multiple products side-by-side with per-variant breakdown."""
```

> **Implementation Note:** `compare_products()` fetches products by IDs, extracts per-variant pricing and availability, and returns a structured dict. Exposed as `compare_products` LangChain tool and `POST /products/compare` API endpoint.

### 2.6 Inventory-Aware Recommendations

**Location:** `apps/api/app/services/search_service.py` (`_apply_filters`), `apps/api/app/services/recommendation_service.py`
**Status:** COMPLETED (via search filters)

- [x] Filter recommendations by current stock levels (`in_stock_only` filter, `status == "active"` check)
- [x] Suggest alternatives for out-of-stock items (`suggest_alternatives` tool)
- [ ] ~~Prioritize products with healthy inventory~~ — not implemented
- [ ] ~~Low-stock warnings in recommendations~~ — not implemented
- [ ] ~~Consider lead times for restocking~~ — not applicable

> **Implementation Note:** Handled by `in_stock_only` filter in SearchService._apply_filters() and by `Product.status == "active"` filter in RecommendationService. No separate `inventory_aware_recommendations.py` was needed.

### 2.7 Recommendation API Endpoints

**Location:** `apps/api/app/api/v1/recommendations.py`
**Status:** PARTIALLY COMPLETE

- [x] `GET /api/v1/products/{product_id}/similar` — Similar products
- [x] `GET /api/v1/products/{product_id}/upsell` — Upsell suggestions
- [x] `POST /api/v1/products/compare` — Product comparison
- [ ] ~~`GET /api/v1/products/{id}/bundles`~~ — Not built (bundles not implemented)
- [ ] ~~`GET /api/v1/products/{id}/size-guide`~~ — DEFERRED
- [ ] ~~`POST /api/v1/recommendations/personalized`~~ — DEFERRED

### 2.8 Recommendation Analytics

**Location:** Not built
**Status:** DEFERRED → [deferred-features.md](../deferred-features.md#recommendation-analytics-originally-phase-2-task-28)

- [ ] ~~Track recommendation click-through rates~~
- [ ] ~~Monitor conversion rates for different recommendation types~~
- [ ] ~~A/B test recommendation algorithms~~
- [ ] ~~Measure revenue impact of recommendations~~
- [ ] ~~Generate insights for merchants~~

---

## Files Created/Modified

| File                                   | Action   | Purpose                                 |
| -------------------------------------- | -------- | --------------------------------------- |
| `app/services/recommendation_service.py` | Created  | Similar, upsell, cross-sell, compare    |
| `app/api/v1/recommendations.py`          | Created  | similar, upsell, compare endpoints      |
| `app/api/v1/router.py`                   | Modified | Registered recommendations router       |

---

## Dependencies

No new dependencies needed. The recommendation service uses existing packages already in `pyproject.toml`:

- `pgvector` — cosine distance for similarity
- `sqlalchemy` — product queries with filters

---

## Testing

- [x] Unit test: similar product algorithm accuracy (`tests/test_recommendation_service.py::TestGetSimilarProducts`)
- [x] Unit test: upsell suggestions are higher value (`tests/test_recommendation_service.py::TestGetUpsellProducts`)
- [x] Unit test: cross-sell suggestions are complementary (`tests/test_recommendation_service.py::TestGetCrossSellProducts`)
- [x] Unit test: product comparison (`tests/test_recommendation_service.py::TestCompareProducts`)
- [x] Unit test: price extraction from variants (`tests/test_recommendation_service.py::TestExtractPrice`)
- [ ] Integration test: full recommendation flow
- [ ] ~~A/B test: different recommendation algorithms~~ — DEFERRED

---

## Acceptance Criteria

1. **Similar Products**: Finds similar products via embedding cosine distance — DONE
2. **Upsell Logic**: Suggests 10-30% higher-priced alternatives from same category/vendor — DONE
3. **Cross-sell Accuracy**: Recommends complementary products (tag overlap, different type) — DONE
4. **Product Comparison**: Side-by-side comparison with per-variant detail — DONE
5. **Inventory Awareness**: Filters by stock availability and active status — DONE
6. **Size Guidance**: ~~Accurate size recommendations~~ — DEFERRED
7. **Personalization**: ~~Adapts to customer preferences~~ — DEFERRED
8. **Analytics**: ~~Tracks recommendation effectiveness~~ — DEFERRED

---

## Notes

- All recommendation logic is consolidated into a single `RecommendationService` class (not split across multiple files as originally planned)
- Content-based recommendations work without user identity — no login/profile required
- Upsell and cross-sell are combined into a single `suggest_alternatives` LangChain tool for the agent
- The recommendation service is multi-tenant safe — all queries scoped by store_id
- Bundles could be added as a new method on RecommendationService without architectural changes

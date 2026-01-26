# Phase 1: Product Search & Discovery

> **Parent:** [M3 Sales & Recommendation Agent](../m3-sales-agent.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** M1 (RAG pipeline), M2 (Shopify integration)

---

## Goal

Build a natural language product search system that can understand customer intent and find relevant products using semantic search, keyword matching, and intelligent filtering.

---

## Tasks

### 1.1 Product Embedding Generation

**Location:** `apps/api/app/services/product_embeddings.py`

- [ ] Generate embeddings for product titles, descriptions, and tags
- [ ] Create composite embeddings combining multiple product fields
- [ ] Store embeddings in `product_embeddings` table with pgvector
- [ ] Implement batch processing for large product catalogs
- [ ] Handle product updates and re-embedding

**Database Schema:**

```sql
CREATE TABLE product_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    content_hash VARCHAR(64) NOT NULL, -- For detecting changes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_product_embeddings_vector ON product_embeddings
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_product_embeddings_store ON product_embeddings(store_id);
```

### 1.2 Hybrid Search Engine

**Location:** `apps/api/app/services/product_search.py`

- [ ] Implement semantic search using product embeddings
- [ ] Add keyword search using PostgreSQL full-text search
- [ ] Combine semantic and keyword scores with weighted ranking
- [ ] Support search filters (price range, category, availability)
- [ ] Implement search result ranking algorithm

**Search Function:**

```python
async def search_products(
    query: str,
    store_id: UUID,
    filters: ProductFilters | None = None,
    limit: int = 10,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3
) -> list[ProductSearchResult]:
    """
    Hybrid product search combining semantic and keyword matching.

    Args:
        query: Natural language search query
        store_id: Store to search within
        filters: Price, category, availability filters
        limit: Maximum results to return
        semantic_weight: Weight for semantic similarity (0-1)
        keyword_weight: Weight for keyword matching (0-1)

    Returns:
        List of products with relevance scores
    """
```

### 1.3 Search Intent Classification

**Location:** `apps/api/app/services/search_intent.py`

- [ ] Classify search queries into categories (gift, specific item, browse)
- [ ] Extract key attributes (color, size, price range, occasion)
- [ ] Identify product categories from natural language
- [ ] Handle ambiguous queries with clarifying questions

**Intent Categories:**

```python
class SearchIntent(str, Enum):
    SPECIFIC_PRODUCT = "specific_product"  # "red Nike shoes size 10"
    GIFT_SEARCH = "gift_search"           # "gift for my mom"
    BROWSE_CATEGORY = "browse_category"   # "summer dresses"
    PROBLEM_SOLVING = "problem_solving"   # "something for back pain"
    PRICE_COMPARISON = "price_comparison" # "cheap wireless headphones"
```

### 1.4 Product Filtering & Ranking

**Location:** `apps/api/app/services/product_filters.py`

- [ ] Implement inventory-aware filtering (in-stock only)
- [ ] Price range filtering with dynamic suggestions
- [ ] Category and tag-based filtering
- [ ] Popularity-based ranking boost
- [ ] Personalization based on store preferences

**Filter Implementation:**

```python
class ProductFilters(BaseModel):
    price_min: float | None = None
    price_max: float | None = None
    categories: list[str] | None = None
    tags: list[str] | None = None
    in_stock_only: bool = True
    min_rating: float | None = None

class ProductSearchResult(BaseModel):
    product: Product
    relevance_score: float
    match_reasons: list[str]  # Why this product matched
    in_stock: bool
    inventory_count: int | None
```

### 1.5 Search API Endpoints

**Location:** `apps/api/app/api/v1/products.py`

- [ ] `POST /api/v1/products/search` - Natural language product search
- [ ] `GET /api/v1/products/suggestions` - Search suggestions/autocomplete
- [ ] `GET /api/v1/products/filters` - Available filter options for store
- [ ] `POST /api/v1/products/embeddings/refresh` - Regenerate embeddings

**Search Endpoint:**

```python
@router.post("/search", response_model=ProductSearchResponse)
async def search_products(
    request: ProductSearchRequest,
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """
    Search products using natural language query.

    Example request:
    {
        "query": "comfortable running shoes for women under $100",
        "filters": {
            "price_max": 100,
            "in_stock_only": true
        },
        "limit": 10
    }
    """
```

### 1.6 Search Analytics & Optimization

**Location:** `apps/api/app/services/search_analytics.py`

- [ ] Track search queries and results clicked
- [ ] Identify zero-result searches for improvement
- [ ] A/B test different ranking algorithms
- [ ] Monitor search performance metrics
- [ ] Generate search insights for merchants

**Analytics Schema:**

```sql
CREATE TABLE search_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    query TEXT NOT NULL,
    results_count INTEGER NOT NULL,
    clicked_product_id UUID REFERENCES products(id),
    click_position INTEGER, -- Position of clicked result
    session_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 1.7 Inventory Integration

**Location:** `apps/api/app/services/inventory.py`

- [ ] Real-time inventory checking via Shopify API
- [ ] Cache inventory data with TTL for performance
- [ ] Handle inventory webhooks for immediate updates
- [ ] Implement low-stock warnings in search results
- [ ] Support variant-level inventory tracking

**Inventory Service:**

```python
class InventoryService:
    async def check_availability(
        self,
        product_ids: list[UUID],
        store_id: UUID
    ) -> dict[UUID, InventoryStatus]:
        """Check real-time inventory for multiple products."""

    async def get_stock_level(
        self,
        product_id: UUID,
        variant_id: UUID | None = None
    ) -> int:
        """Get current stock level for product/variant."""
```

---

## Files to Create/Modify

| File                                   | Action | Purpose                        |
| -------------------------------------- | ------ | ------------------------------ |
| `app/services/product_embeddings.py`   | Create | Product embedding generation   |
| `app/services/product_search.py`       | Create | Hybrid search engine           |
| `app/services/search_intent.py`        | Create | Query intent classification    |
| `app/services/product_filters.py`      | Create | Search filtering and ranking   |
| `app/services/search_analytics.py`     | Create | Search performance tracking    |
| `app/services/inventory.py`            | Create | Real-time inventory checking   |
| `app/api/v1/products.py`               | Modify | Add search endpoints           |
| `app/schemas/product_search.py`        | Create | Search request/response models |
| `app/models/product_embeddings.py`     | Create | Database model for embeddings  |
| `app/workers/embedding_tasks.py`       | Create | Async embedding generation     |
| `migrations/add_product_embeddings.py` | Create | Database migration             |

---

## Dependencies

```toml
# Add to pyproject.toml
scikit-learn = "^1.3"     # For search ranking algorithms
numpy = "^1.24"           # Numerical operations
sentence-transformers = "^2.2"  # Alternative embedding models
```

---

## Testing

- [ ] Unit test: product embedding generation accuracy
- [ ] Unit test: semantic search returns relevant results
- [ ] Unit test: keyword search handles typos and variations
- [ ] Unit test: hybrid scoring combines results correctly
- [ ] Unit test: filters work correctly (price, category, stock)
- [ ] Integration test: full search flow with real product data
- [ ] Performance test: search response time under load
- [ ] A/B test: different ranking algorithms

---

## Acceptance Criteria

1. **Natural Language Understanding**: Can interpret queries like "gift for my mom who likes gardening"
2. **Semantic Search**: Finds relevant products even without exact keyword matches
3. **Hybrid Ranking**: Combines semantic and keyword relevance effectively
4. **Real-time Inventory**: Only shows in-stock products when requested
5. **Performance**: Search results returned within 2 seconds
6. **Filtering**: Supports price, category, and availability filters
7. **Analytics**: Tracks search performance and zero-result queries

---

## Example Queries & Expected Results

**Query:** "comfortable running shoes for women under $100"

- **Intent:** Specific product search
- **Filters:** Category=shoes, gender=women, price<$100
- **Results:** Running shoes sorted by comfort rating and price

**Query:** "gift for my teenage daughter"

- **Intent:** Gift search
- **Clarification:** "What are her interests? Here are some popular items for teens..."
- **Results:** Trending products in teen categories

**Query:** "something warm for winter"

- **Intent:** Browse category
- **Filters:** Season=winter, category=clothing
- **Results:** Jackets, sweaters, winter accessories

---

## Notes

- Start with simple keyword + semantic search, optimize ranking iteratively
- Consider using Shopify's search API as fallback for complex queries
- Implement search suggestions to guide users toward better queries
- Monitor search analytics to identify improvement opportunities

# Phase 2: Recommendations Engine

> **Parent:** [M3 Sales & Recommendation Agent](../m3-sales-agent.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Product Search), M2 (Shopify integration)

---

## Goal

Build an intelligent recommendation system that suggests relevant products, upsells, cross-sells, and provides size/fit guidance to help customers make informed purchase decisions.

---

## Tasks

### 2.1 Similar Products Engine

**Location:** `apps/api/app/services/recommendations.py`

- [ ] Implement content-based similarity using product embeddings
- [ ] Calculate product similarity scores using cosine similarity
- [ ] Consider product attributes (category, price range, brand)
- [ ] Filter out-of-stock and discontinued products
- [ ] Rank by similarity score and popularity

**Similarity Function:**

```python
async def find_similar_products(
    product_id: UUID,
    store_id: UUID,
    limit: int = 5,
    price_tolerance: float = 0.3,  # ±30% price range
    same_category_only: bool = False
) -> list[SimilarProduct]:
    """
    Find products similar to the given product.

    Args:
        product_id: Reference product
        store_id: Store to search within
        limit: Maximum recommendations
        price_tolerance: Acceptable price range variation
        same_category_only: Restrict to same category

    Returns:
        List of similar products with similarity scores
    """
```

### 2.2 Upsell & Cross-sell Logic

**Location:** `apps/api/app/services/upsell_engine.py`

- [ ] Identify upsell opportunities (higher-priced similar products)
- [ ] Generate cross-sell suggestions (complementary products)
- [ ] Implement rule-based product bundles
- [ ] Consider customer purchase history patterns
- [ ] Calculate revenue impact for each suggestion

**Upsell Categories:**

```python
class RecommendationType(str, Enum):
    UPSELL = "upsell"           # Higher-priced alternative
    CROSS_SELL = "cross_sell"   # Complementary product
    BUNDLE = "bundle"           # Product bundle deal
    ALTERNATIVE = "alternative" # Similar price point
    ACCESSORY = "accessory"     # Related accessories

class ProductRecommendation(BaseModel):
    product: Product
    type: RecommendationType
    reason: str  # Why this is recommended
    confidence_score: float  # 0-1 confidence
    potential_revenue: float  # Expected additional revenue
    bundle_discount: float | None = None
```

### 2.3 Size & Fit Guidance System

**Location:** `apps/api/app/services/size_guidance.py`

- [ ] Parse and store product size charts
- [ ] Implement size recommendation algorithm
- [ ] Analyze customer reviews for fit feedback
- [ ] Handle different sizing systems (US, EU, UK)
- [ ] Provide size conversion and guidance

**Size Chart Schema:**

```sql
CREATE TABLE size_charts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id),
    size_system VARCHAR(10) NOT NULL, -- 'US', 'EU', 'UK', 'UNISEX'
    measurements JSONB NOT NULL, -- Size measurements data
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Example measurements JSONB:
{
    "XS": {"chest": "32-34", "waist": "26-28", "length": "26"},
    "S": {"chest": "34-36", "waist": "28-30", "length": "27"},
    "M": {"chest": "36-38", "waist": "30-32", "length": "28"}
}
```

**Size Guidance Service:**

```python
class SizeGuidanceService:
    async def recommend_size(
        self,
        product_id: UUID,
        customer_measurements: CustomerMeasurements | None = None,
        customer_preferences: SizePreferences | None = None
    ) -> SizeRecommendation:
        """Recommend best size for customer."""

    async def get_size_chart(
        self,
        product_id: UUID,
        size_system: str = "US"
    ) -> SizeChart | None:
        """Get size chart for product."""

    async def analyze_fit_reviews(
        self,
        product_id: UUID
    ) -> FitAnalysis:
        """Analyze customer reviews for fit insights."""
```

### 2.4 Personalization Engine

**Location:** `apps/api/app/services/personalization.py`

- [ ] Track customer browsing and purchase behavior
- [ ] Build customer preference profiles
- [ ] Implement collaborative filtering for recommendations
- [ ] Consider seasonal and trending products
- [ ] Handle cold start problem for new customers

**Customer Profile Schema:**

```sql
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    customer_identifier VARCHAR(255) NOT NULL, -- Email, phone, or session
    preferences JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Example preferences JSONB:
{
    "categories": ["clothing", "accessories"],
    "price_range": {"min": 20, "max": 100},
    "brands": ["Nike", "Adidas"],
    "colors": ["black", "white", "blue"],
    "size": "M",
    "style": "casual"
}
```

### 2.5 Product Comparison Generator

**Location:** `apps/api/app/services/product_comparison.py`

- [ ] Generate side-by-side product comparisons
- [ ] Extract and compare key product features
- [ ] Highlight differences and similarities
- [ ] Include price, ratings, and availability
- [ ] Format comparison in conversational style

**Comparison Service:**

```python
async def compare_products(
    product_ids: list[UUID],
    store_id: UUID,
    comparison_aspects: list[str] | None = None
) -> ProductComparison:
    """
    Generate detailed comparison between products.

    Args:
        product_ids: Products to compare (2-4 products)
        store_id: Store context
        comparison_aspects: Specific aspects to focus on

    Returns:
        Structured comparison with highlights
    """
```

### 2.6 Inventory-Aware Recommendations

**Location:** `apps/api/app/services/inventory_aware_recommendations.py`

- [ ] Filter recommendations by current stock levels
- [ ] Prioritize products with healthy inventory
- [ ] Handle low-stock warnings in recommendations
- [ ] Suggest alternatives for out-of-stock items
- [ ] Consider lead times for restocking

**Inventory Integration:**

```python
async def get_inventory_aware_recommendations(
    base_recommendations: list[ProductRecommendation],
    store_id: UUID,
    min_stock_level: int = 1
) -> list[ProductRecommendation]:
    """Filter and rerank recommendations based on inventory."""
```

### 2.7 Recommendation API Endpoints

**Location:** `apps/api/app/api/v1/recommendations.py`

- [ ] `GET /api/v1/products/{id}/similar` - Similar products
- [ ] `GET /api/v1/products/{id}/upsells` - Upsell suggestions
- [ ] `GET /api/v1/products/{id}/bundles` - Bundle recommendations
- [ ] `POST /api/v1/products/compare` - Product comparison
- [ ] `GET /api/v1/products/{id}/size-guide` - Size guidance
- [ ] `POST /api/v1/recommendations/personalized` - Personalized recs

**Recommendation Endpoints:**

```python
@router.get("/{product_id}/similar", response_model=SimilarProductsResponse)
async def get_similar_products(
    product_id: UUID,
    limit: int = Query(5, ge=1, le=20),
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Get products similar to the specified product."""

@router.post("/compare", response_model=ProductComparisonResponse)
async def compare_products(
    request: ProductComparisonRequest,
    store: Store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Compare multiple products side-by-side."""
```

### 2.8 Recommendation Analytics

**Location:** `apps/api/app/services/recommendation_analytics.py`

- [ ] Track recommendation click-through rates
- [ ] Monitor conversion rates for different recommendation types
- [ ] A/B test recommendation algorithms
- [ ] Measure revenue impact of recommendations
- [ ] Generate insights for merchants

**Analytics Schema:**

```sql
CREATE TABLE recommendation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    session_id VARCHAR(255),
    recommendation_type VARCHAR(50) NOT NULL,
    source_product_id UUID REFERENCES products(id),
    recommended_product_id UUID NOT NULL REFERENCES products(id),
    position INTEGER NOT NULL, -- Position in recommendation list
    clicked BOOLEAN DEFAULT FALSE,
    purchased BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Files to Create/Modify

| File                                              | Action | Purpose                                |
| ------------------------------------------------- | ------ | -------------------------------------- |
| `app/services/recommendations.py`                 | Create | Core recommendation engine             |
| `app/services/upsell_engine.py`                   | Create | Upsell and cross-sell logic            |
| `app/services/size_guidance.py`                   | Create | Size and fit recommendations           |
| `app/services/personalization.py`                 | Create | Customer preference tracking           |
| `app/services/product_comparison.py`              | Create | Product comparison generator           |
| `app/services/inventory_aware_recommendations.py` | Create | Inventory-filtered recommendations     |
| `app/services/recommendation_analytics.py`        | Create | Recommendation performance tracking    |
| `app/api/v1/recommendations.py`                   | Create | Recommendation endpoints               |
| `app/schemas/recommendations.py`                  | Create | Recommendation request/response models |
| `app/models/size_charts.py`                       | Create | Size chart database model              |
| `app/models/customer_profiles.py`                 | Create | Customer profile database model        |
| `app/workers/recommendation_tasks.py`             | Create | Async recommendation processing        |
| `migrations/add_recommendation_tables.py`         | Create | Database migration                     |

---

## Dependencies

```toml
# Add to pyproject.toml
scikit-learn = "^1.3"     # For collaborative filtering
pandas = "^2.0"           # Data manipulation for analytics
scipy = "^1.11"           # Statistical functions
```

---

## Testing

- [ ] Unit test: similar product algorithm accuracy
- [ ] Unit test: upsell suggestions are higher value
- [ ] Unit test: cross-sell suggestions are complementary
- [ ] Unit test: size recommendations are accurate
- [ ] Unit test: inventory filtering works correctly
- [ ] Integration test: full recommendation flow
- [ ] A/B test: different recommendation algorithms
- [ ] Performance test: recommendation generation speed

---

## Acceptance Criteria

1. **Similar Products**: Finds genuinely similar products with >80% relevance
2. **Upsell Logic**: Suggests higher-value alternatives appropriately
3. **Cross-sell Accuracy**: Recommends complementary products correctly
4. **Size Guidance**: Provides accurate size recommendations
5. **Inventory Awareness**: Only recommends available products
6. **Performance**: Recommendations generated within 1 second
7. **Personalization**: Adapts to customer preferences over time
8. **Analytics**: Tracks recommendation effectiveness

---

## Example Recommendation Scenarios

**Similar Products:**

- Customer viewing "Nike Air Max 90" → Recommend "Nike Air Force 1", "Adidas Stan Smith"

**Upsell:**

- Customer viewing $50 sneakers → Recommend $80 premium version with better materials

**Cross-sell:**

- Customer viewing running shoes → Recommend running socks, fitness tracker, water bottle

**Bundle:**

- Customer viewing winter jacket → Recommend jacket + gloves + beanie bundle with 15% discount

**Size Guidance:**

- Customer asks "What size should I get?" → Analyze size chart + reviews → "Based on your measurements and customer feedback, I'd recommend size M"

---

## Notes

- Start with content-based recommendations, add collaborative filtering later
- Use A/B testing to optimize recommendation algorithms
- Consider seasonal trends in recommendation logic
- Implement feedback loops to improve recommendations over time
- Monitor recommendation performance and adjust algorithms accordingly

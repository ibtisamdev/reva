# Deferred Features

Features deferred from their original milestones for future consideration.

---

## Shipping Integrations (originally M2)

**Deferred from:** [M2 Order Status Agent](m2-order-status.md), [Phase 2](m2-phases/phase-2-shipping-integration.md)

**Why deferred:** Shopify's fulfillment data (tracking numbers, carrier names, tracking URLs) covers ~90% of WISMO queries without adding external dependencies. Customers get a tracking link to the carrier's page directly in chat. This is sufficient for the MVP.

**When to reconsider:**
- Merchants request inline tracking events in chat (e.g., "in transit in Memphis, TN")
- Merchants want proactive delivery notifications ("your package was delivered")
- Estimated delivery date predictions are needed within chat responses
- Volume justifies the added complexity and cost

### AfterShip (originally P0)

Unified tracking aggregator for 1000+ carriers worldwide.

| Feature | Description |
|---------|-------------|
| Unified API | Single integration for USPS, FedEx, UPS, DHL, and 1000+ carriers |
| Auto-detection | Identifies carrier from tracking number automatically |
| Real-time events | Granular tracking events (picked up, in transit, out for delivery, etc.) |
| Webhooks | Push-based tracking updates instead of polling |
| Estimated delivery | Delivery date predictions based on carrier + route data |
| Normalized statuses | Consistent status codes across all carriers |

**Pricing:** Free tier (100 trackings/month), paid plans scale with volume.

**Original plan:** Created an `AfterShipService` client, tracking_info/tracking_events DB tables, webhook endpoints, and Celery tasks for async processing.

### ShipStation (originally P1)

Shipping management platform with enriched shipment data.

| Feature | Description |
|---------|-------------|
| Shipping labels | Access to label and rate information |
| Fulfillment centers | Detailed fulfillment center data |
| Enhanced tracking | Richer tracking data for ShipStation merchants |

### Shippo (originally P2)

Multi-carrier shipping API.

| Feature | Description |
|---------|-------------|
| Multi-carrier tracking | Alternative to AfterShip |
| Shipping rates | Compare carrier rates |

### Route (originally P2)

Package protection and claims platform.

| Feature | Description |
|---------|-------------|
| Protection status | Check if order has package protection |
| Claims | Initiate and track protection claims |

---

## M3 Deferred Features (originally M3)

**Deferred from:** [M3 Sales & Recommendation Agent](m3-sales-agent.md), [Phase 1](m3-phases/phase-1-product-search.md), [Phase 2](m3-phases/phase-2-recommendations.md)

**Why deferred:** The core M3 deliverables (hybrid search, recommendations, LangGraph routing) are complete without these features. Each deferred item is either a complex standalone system or an optimization that requires sufficient usage data to be meaningful.

### Size & Fit Guidance (originally Phase 2, Task 2.3)

Complex feature requiring size chart parsing, review NLP analysis, and multi-system conversion (US/EU/UK).

**Why deferred:** The LLM can already answer basic sizing questions from product descriptions and variant names. Building a structured size guidance system with dedicated DB tables (`size_charts`), measurement parsing, and review sentiment analysis is substantial work with limited current demand.

**When to reconsider:**
- Merchants in apparel/fashion verticals request structured size recommendations
- High volume of sizing-related returns suggests customers need better guidance
- Customer feedback indicates need for measurement-based recommendations

**Original plan:** `size_guidance.py` service, `size_charts` DB table, `GET /products/{id}/size-guide` endpoint, size conversion logic.

### Personalization Engine (originally Phase 2, Task 2.4)

Customer preference tracking with collaborative filtering and profile-based recommendations.

**Why deferred:** Requires customer profile tracking, purchase history analysis, collaborative filtering algorithms, and cold-start handling. Current content-based recommendations (embedding similarity, tag overlap, price-tier upsell) are sufficient for MVP and work without needing user identity.

**When to reconsider:**
- Repeat customer rate is high enough to justify profile tracking
- Merchants request personalized recommendations
- Sufficient purchase data volume exists for collaborative filtering to be effective

**Original plan:** `personalization.py` service, `customer_profiles` DB table, `POST /recommendations/personalized` endpoint, collaborative filtering algorithms.

### Sales Analytics Dashboard (originally M3 Success Criteria)

Merchant-facing dashboard for search quality, recommendation performance, and conversion tracking.

**Why deferred:** Existing conversation analytics from M2 (`GET /api/v1/analytics/conversations`, `GET /api/v1/analytics/messages`) cover basic metrics. A full sales-specific dashboard with recommendation CTR, search quality metrics, and conversion attribution is a separate frontend + backend effort.

**When to reconsider:**
- Merchants need visibility into how recommendations drive sales
- Enough data volume to make analytics meaningful
- Product-market fit validated and dashboard becomes a differentiator

**Original plan:** `sales_analytics.py` service, dashboard pages in `apps/web/`, aggregation queries.

### Search Analytics & Optimization (originally Phase 1, Task 1.6)

Zero-result search tracking, click-through tracking, and A/B testing infrastructure for search ranking.

**Why deferred:** Core search functionality works well without analytics instrumentation. These are optimization features that require sufficient search volume to be actionable.

**When to reconsider:**
- Search quality issues are identified through customer feedback
- Need data-driven ranking improvements
- Search volume warrants optimization investment

**Original plan:** `search_analytics.py` service, `search_analytics` DB table, click tracking, A/B test framework.

### Recommendation Analytics (originally Phase 2, Task 2.8)

CTR tracking, conversion attribution, and A/B testing for recommendation algorithms.

**Why deferred:** Measuring recommendation effectiveness requires tracking user actions through the widget (clicks, purchases) which needs widget-side instrumentation not yet built.

**When to reconsider:**
- Need to measure and optimize recommendation quality
- Merchants want recommendation performance data
- Widget has event tracking infrastructure

**Original plan:** `recommendation_analytics.py` service, `recommendation_analytics` DB table, conversion attribution logic.

### Add-to-Cart Deep Links (originally M3 Roadmap)

In-chat links that add products directly to the customer's Shopify cart.

**Why deferred:** Requires Shopify cart permalink generation (`/cart/{variant_id}:{quantity}`), widget UI for clickable product cards, and variant selection UX. The chat agent already provides product information (name, price, availability) that customers can use to navigate to the store and purchase.

**When to reconsider:**
- Conversion data shows customers drop off between viewing a recommendation and completing purchase
- Merchants specifically request in-chat purchase flow
- Widget UI is mature enough to support product card components

**Original plan:** Cart permalink generation, widget product card components, variant selector UI.

---

## How to Reintroduce

When the time comes to add these features:

### Shipping Integrations (M2)

1. The Phase 2 doc (`m2-phases/phase-2-shipping-integration.md`) already has the service layer pattern established — add the external service as an enrichment layer on top of Shopify fulfillment data
2. Create a `TrackingProvider` interface so AfterShip can be swapped in without changing the tools or chat integration
3. Add the tracking_info/tracking_events DB tables only if you need to store historical tracking data (for analytics or proactive notifications)
4. The webhook infrastructure pattern from Shopify webhooks can be reused for AfterShip/ShipStation webhooks

### M3 Sales Features

1. **Size guidance & personalization** — The `RecommendationService` (`app/services/recommendation_service.py`) already provides the extension point. Add new methods alongside existing `get_similar_products()`, `get_upsell_products()`, etc. New LangChain tools can be added to `app/services/tools/product_tools.py` using the same factory pattern.
2. **Analytics features** — Add event tracking to existing services. The `ConversationState` in `app/services/graph/state.py` already tracks `tools_used`, `tool_calls_record`, and `tool_results_record` which can feed analytics.
3. **Add-to-cart deep links** — Add cart URL generation to product tool responses in `product_tools.py`. The widget (`apps/widget/`) needs new components for product cards with action buttons.
4. **Sales dashboard** — Extend existing analytics endpoints in `app/api/v1/analytics.py` with sales-specific aggregations. Add dashboard pages in `apps/web/`.

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

## How to Reintroduce

When the time comes to add these integrations:

1. The Phase 2 doc (`m2-phases/phase-2-shipping-integration.md`) already has the service layer pattern established — add the external service as an enrichment layer on top of Shopify fulfillment data
2. Create a `TrackingProvider` interface so AfterShip can be swapped in without changing the tools or chat integration
3. Add the tracking_info/tracking_events DB tables only if you need to store historical tracking data (for analytics or proactive notifications)
4. The webhook infrastructure pattern from Shopify webhooks can be reused for AfterShip/ShipStation webhooks

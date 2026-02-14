# Phase 2: Shopify Fulfillment Tracking

> **Parent:** [M2 Order Status Agent](../m2-order-status.md)
> **Duration:** 1 week
> **Status:** Not Started
> **Dependencies:** Phase 1 complete (customer verification & order lookup)

---

## Goal

Extract and present tracking information from Shopify fulfillment data so customers can get shipping status and tracking links directly in chat. No external tracking service required — Shopify fulfillments already provide tracking numbers, carrier names, and tracking URLs.

---

## Tasks

### 2.1 Tracking Data Extraction Service

**Location:** `apps/api/app/services/tracking.py`

- [ ] Create service to extract tracking info from Shopify fulfillment responses
- [ ] Parse fulfillment data: tracking_number, tracking_url, tracking_company
- [ ] Handle multiple fulfillments per order (partial shipments)
- [ ] Handle orders with no fulfillment yet (unfulfilled)
- [ ] Cache fulfillment data with appropriate TTL (15 minutes, same as order cache)
- [ ] Map fulfillment statuses to customer-friendly messages

**Tracking Service:**

```python
class TrackingService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_tracking_info(
        self,
        fulfillments: list[dict],
    ) -> list[TrackingInfo]:
        """Extract tracking info from Shopify fulfillment data."""
        # 1. Parse each fulfillment for tracking details
        # 2. Return structured tracking info with carrier links

    def format_tracking_response(
        self,
        tracking_info: list[TrackingInfo],
    ) -> str:
        """Format tracking info for customer-friendly chat response."""
        # 1. Format each tracking entry with carrier name + link
        # 2. Handle single vs multiple packages
        # 3. Handle missing tracking (label created but not shipped)
```

### 2.2 Shopify Fulfillment Data Model

**Location:** `apps/api/app/schemas/tracking.py`

- [ ] Create Pydantic schemas for fulfillment tracking data
- [ ] Map Shopify fulfillment statuses to internal statuses
- [ ] Support multiple tracking numbers per fulfillment

**No new database tables needed** — tracking data is fetched on-demand from Shopify and cached in Redis.

**Pydantic Schemas:**

```python
class TrackingInfo(BaseModel):
    tracking_number: str | None
    tracking_url: str | None
    carrier: str | None  # tracking_company from Shopify
    fulfillment_status: str  # success, pending, open, failure, cancelled
    shipment_status: str | None  # in_transit, delivered, etc. (if available)
    created_at: datetime  # when fulfillment was created

class OrderTrackingResponse(BaseModel):
    order_number: str
    fulfillment_status: str  # fulfilled, partial, unfulfilled
    packages: list[TrackingInfo]
```

**Shopify Fulfillment Status Mapping:**

| Shopify Status | Customer Message |
|----------------|------------------|
| `unfulfilled` | "Your order is being prepared for shipping" |
| `partial` | "Part of your order has shipped!" |
| `fulfilled` | "Your order has shipped!" + tracking links |

### 2.3 Enhanced Order Tools with Tracking

**Location:** `apps/api/app/tools/order_tools.py` (modify existing)

- [ ] Add `TrackingLookupTool` for LangChain integration
- [ ] Enhance `OrderLookupTool` to include fulfillment/tracking data
- [ ] Handle orders with no tracking info gracefully

**LangChain Tools:**

```python
class TrackingLookupTool(BaseTool):
    name = "tracking_lookup"
    description = "Get tracking information for an order's shipments"

    def _run(self, order_number: str) -> str:
        # 1. Get order with fulfillments from Shopify (or cache)
        # 2. Extract tracking info from fulfillments
        # 3. Format response with tracking links
        # 4. Return customer-friendly tracking update
```

### 2.4 Tracking Response Templates

**Location:** `apps/api/app/templates/tracking_responses.py`

- [ ] Create templates for different fulfillment statuses
- [ ] Include tracking links for each package
- [ ] Handle multiple packages per order
- [ ] Handle missing tracking numbers (fulfilled but no tracking)

**Tracking Templates:**

```python
TRACKING_STATUS_TEMPLATES = {
    "fulfilled_with_tracking": (
        "Your order has shipped!\n\n"
        "Carrier: {carrier}\n"
        "Tracking number: {tracking_number}\n"
        "Track your package: {tracking_url}"
    ),

    "fulfilled_no_tracking": (
        "Your order has been fulfilled! "
        "A tracking number hasn't been added yet — "
        "it should be available shortly."
    ),

    "partial_fulfillment": (
        "Part of your order has shipped!\n\n"
        "{shipped_items}\n\n"
        "The rest of your order is being prepared."
    ),

    "unfulfilled": (
        "Your order is confirmed and being prepared for shipping. "
        "You'll get tracking information once it ships."
    ),

    "multiple_packages": (
        "Your order shipped in {count} packages:\n\n"
        "{package_details}"
    ),
}
```

### 2.5 Enhanced Chat Integration

**Location:** `apps/api/app/services/chat.py` (modify existing)

- [ ] Integrate tracking tools into chat pipeline
- [ ] Detect tracking-related queries
- [ ] Include tracking info in order status responses automatically

**Tracking Intent Detection:**

```python
TRACKING_INTENT_KEYWORDS = [
    "tracking", "shipped", "delivery", "package",
    "where is", "when will", "shipping status"
]

async def enhance_order_response_with_tracking(
    order: dict,
) -> str:
    """Add tracking information to order response."""
    # 1. Get fulfillments from order data
    # 2. Extract tracking info
    # 3. Format response with tracking links
```

---

## Files to Create/Modify

| File                                  | Action | Purpose                              |
| ------------------------------------- | ------ | ------------------------------------ |
| `app/services/tracking.py`            | Create | Fulfillment tracking extraction      |
| `app/schemas/tracking.py`             | Create | Tracking Pydantic schemas            |
| `app/templates/tracking_responses.py` | Create | Tracking response templates          |
| `app/tools/order_tools.py`            | Modify | Add tracking tools                   |
| `app/services/chat.py`                | Modify | Integrate tracking in chat responses |

---

## Dependencies

No new external dependencies required. Uses existing:
- `httpx` — for Shopify API calls (already in project)
- `redis` — for caching fulfillment data (already in project)

---

## Configuration

No new configuration needed. Tracking data comes from the same Shopify API credentials used for order lookup.

---

## API Endpoints

| Endpoint                                 | Method | Purpose                    |
| ---------------------------------------- | ------ | -------------------------- |
| `/api/v1/orders/{order_number}/tracking` | GET    | Get tracking for an order  |

---

## Testing

- [ ] Unit test: Tracking info extraction from Shopify fulfillment data
- [ ] Unit test: Tracking response formatting (single/multiple packages)
- [ ] Unit test: Handling unfulfilled orders and missing tracking numbers
- [ ] Unit test: LangChain tracking tool functionality
- [ ] Integration test: Full tracking lookup flow via chat
- [ ] Test: Redis caching of fulfillment data
- [ ] Test: Multiple fulfillments per order (partial shipments)

---

## Acceptance Criteria

1. Can extract tracking info from Shopify fulfillment data
2. Provides tracking links for shipped orders
3. Handles unfulfilled, partially fulfilled, and fully fulfilled orders
4. Multiple packages per order are handled correctly
5. Tracking status is displayed in customer-friendly language
6. Fulfillment data is cached to reduce Shopify API calls
7. LangChain tools provide accurate tracking information

---

## Notes

- This approach uses Shopify as the sole source of tracking data
- Customers click through to the carrier's tracking page for real-time details
- For inline tracking events (e.g., "in transit in Memphis"), a third-party service like AfterShip would be needed — see [deferred features](../deferred-features.md)
- Shopify provides `tracking_url` which is a direct link to the carrier's tracking page
- The `tracking_company` field identifies the carrier (USPS, FedEx, UPS, DHL, etc.)

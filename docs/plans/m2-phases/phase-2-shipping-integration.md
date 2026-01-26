# Phase 2: Shipping Integration & Carrier Tracking

> **Parent:** [M2 Order Status Agent](../m2-order-status.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 complete (customer verification & order lookup)

---

## Goal

Integrate with shipping carriers and tracking services to provide real-time package tracking information. Primary integration with AfterShip for unified tracking across 1000+ carriers.

---

## Tasks

### 2.1 AfterShip Integration Service

**Location:** `apps/api/app/services/tracking.py`

- [ ] Create AfterShip API client wrapper
- [ ] Implement tracking number lookup
- [ ] Support multiple carriers (USPS, FedEx, UPS, DHL, etc.)
- [ ] Handle tracking webhooks for real-time updates
- [ ] Cache tracking data with appropriate TTL (30 minutes)
- [ ] Map carrier tracking events to customer-friendly messages

**AfterShip Client:**

```python
class AfterShipService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.aftership.com/v4"

    async def create_tracking(
        self,
        tracking_number: str,
        carrier: str = None
    ) -> TrackingInfo:
        """Add tracking number to AfterShip for monitoring."""

    async def get_tracking(self, tracking_number: str) -> TrackingInfo:
        """Get current tracking status and events."""

    async def detect_carrier(self, tracking_number: str) -> list[str]:
        """Auto-detect possible carriers for tracking number."""
```

### 2.2 Tracking Data Models

**Location:** `apps/api/app/models/tracking.py`

- [ ] Create tracking information database models
- [ ] Store tracking events and status updates
- [ ] Link tracking data to Shopify fulfillments
- [ ] Support multiple tracking numbers per order

**Database Schema:**

```sql
-- Tracking information table
CREATE TABLE tracking_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    order_id VARCHAR(100) NOT NULL,
    tracking_number VARCHAR(100) NOT NULL,
    carrier VARCHAR(50),
    status VARCHAR(50),
    estimated_delivery TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tracking_number, carrier)
);

-- Tracking events table
CREATE TABLE tracking_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tracking_info_id UUID NOT NULL REFERENCES tracking_info(id),
    event_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50),
    message TEXT,
    location VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2.3 Enhanced Order Tools with Tracking

**Location:** `apps/api/app/tools/order_tools.py` (modify existing)

- [ ] Add `TrackingLookupTool` for LangChain integration
- [ ] Enhance `OrderLookupTool` to include tracking information
- [ ] Create `EstimatedDeliveryTool` for delivery predictions
- [ ] Handle tracking errors gracefully (invalid numbers, carrier issues)

**Enhanced LangChain Tools:**

```python
class TrackingLookupTool(BaseTool):
    name = "tracking_lookup"
    description = "Get real-time tracking information for a package"

    def _run(self, tracking_number: str, carrier: str = None) -> str:
        # 1. Query AfterShip for tracking info
        # 2. Format tracking events for customer
        # 3. Include estimated delivery if available
        # 4. Return formatted tracking update

class EstimatedDeliveryTool(BaseTool):
    name = "estimated_delivery"
    description = "Get estimated delivery date for an order"

    def _run(self, order_number: str) -> str:
        # 1. Get order fulfillments
        # 2. Check tracking data for delivery estimates
        # 3. Return estimated delivery information
```

### 2.4 Tracking Event Processing

**Location:** `apps/api/app/workers/tracking_tasks.py`

- [ ] Create Celery task for tracking updates
- [ ] Process AfterShip webhooks asynchronously
- [ ] Update tracking status in database
- [ ] Send notifications for delivery updates (optional)
- [ ] Handle tracking data cleanup (old events)

**Tracking Tasks:**

```python
@celery_app.task
async def update_tracking_info(tracking_number: str, carrier: str):
    """Update tracking information from AfterShip."""
    # 1. Fetch latest tracking data
    # 2. Update database records
    # 3. Process new tracking events
    # 4. Cache updated information

@celery_app.task
async def process_tracking_webhook(webhook_data: dict):
    """Process real-time tracking updates from AfterShip."""
    # 1. Validate webhook signature
    # 2. Extract tracking information
    # 3. Update database
    # 4. Trigger any notifications
```

### 2.5 Tracking Response Templates

**Location:** `apps/api/app/templates/tracking_responses.py`

- [ ] Create templates for different tracking statuses
- [ ] Include location and timing information
- [ ] Handle delivery exceptions and delays
- [ ] Support multiple packages per order

**Tracking Templates:**

```python
TRACKING_STATUS_TEMPLATES = {
    "in_transit": "📦 Your package is on its way!\n\nTracking: {tracking_number}\nLast update: {last_event}\nLocation: {current_location}\nEstimated delivery: {estimated_delivery}",

    "out_for_delivery": "🚚 Great news! Your package is out for delivery today!\n\nTracking: {tracking_number}\nExpected delivery: Today by {delivery_time}",

    "delivered": "✅ Your package has been delivered!\n\nDelivered: {delivery_time}\nLocation: {delivery_location}\nSigned by: {signature}",

    "exception": "⚠️ There's an update on your package:\n\n{exception_message}\n\nTracking: {tracking_number}\nCarrier: {carrier}\n\nContact the carrier for more details.",

    "pending": "📋 Your tracking number has been created but the package hasn't been picked up yet.\n\nTracking: {tracking_number}\nCarrier: {carrier}"
}
```

### 2.6 ShipStation Integration (Optional)

**Location:** `apps/api/app/services/shipstation.py`

- [ ] Create ShipStation API client for enhanced shipping data
- [ ] Fetch shipping labels and rates information
- [ ] Get detailed fulfillment center information
- [ ] Support ShipStation-specific tracking features

**ShipStation Service:**

```python
class ShipStationService:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://ssapi.shipstation.com"

    async def get_shipment(self, shipment_id: str) -> ShipmentInfo:
        """Get detailed shipment information from ShipStation."""

    async def get_tracking_info(self, order_number: str) -> list[TrackingInfo]:
        """Get tracking information for ShipStation orders."""
```

### 2.7 Webhook Endpoints

**Location:** `apps/api/app/api/v1/webhooks/tracking.py`

- [ ] Create AfterShip webhook endpoint
- [ ] Validate webhook signatures
- [ ] Process tracking updates asynchronously
- [ ] Handle webhook retry logic
- [ ] Support multiple webhook sources (AfterShip, ShipStation)

**Webhook Endpoints:**

```python
@router.post("/aftership")
async def aftership_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle AfterShip tracking webhooks."""
    # 1. Validate webhook signature
    # 2. Parse tracking update
    # 3. Queue background task for processing
    # 4. Return 200 OK

@router.post("/shipstation")
async def shipstation_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle ShipStation webhooks."""
    # Similar processing for ShipStation events
```

### 2.8 Enhanced Chat Integration

**Location:** `apps/api/app/services/chat.py` (modify existing)

- [ ] Integrate tracking tools into chat pipeline
- [ ] Detect tracking-related queries
- [ ] Provide proactive tracking updates
- [ ] Handle multiple tracking numbers per conversation

**Tracking Intent Detection:**

```python
TRACKING_INTENT_KEYWORDS = [
    "tracking", "shipped", "delivery", "package", "carrier",
    "ups", "fedex", "usps", "dhl", "where is", "when will"
]

async def enhance_order_response_with_tracking(
    order: Order,
    fulfillments: list[Fulfillment]
) -> str:
    """Add tracking information to order response."""
    # 1. Get tracking numbers from fulfillments
    # 2. Fetch latest tracking data
    # 3. Format comprehensive response
    # 4. Include delivery estimates
```

---

## Files to Create/Modify

| File                                  | Action | Purpose                       |
| ------------------------------------- | ------ | ----------------------------- |
| `app/services/tracking.py`            | Create | AfterShip integration service |
| `app/services/shipstation.py`         | Create | ShipStation integration       |
| `app/models/tracking.py`              | Create | Tracking data models          |
| `app/templates/tracking_responses.py` | Create | Tracking response templates   |
| `app/workers/tracking_tasks.py`       | Create | Async tracking processing     |
| `app/api/v1/webhooks/__init__.py`     | Create | Webhooks package init         |
| `app/api/v1/webhooks/tracking.py`     | Create | Tracking webhook endpoints    |
| `app/schemas/tracking.py`             | Create | Tracking Pydantic models      |
| `app/tools/order_tools.py`            | Modify | Add tracking tools            |
| `app/services/chat.py`                | Modify | Integrate tracking features   |
| `app/core/config.py`                  | Modify | Add tracking service configs  |

---

## Dependencies

```toml
# Add to pyproject.toml
httpx = "^0.27"              # HTTP client for API calls
cryptography = "^41.0"       # Webhook signature validation
python-multipart = "^0.0.6"  # Webhook form data parsing
```

---

## Configuration

```python
# Add to app/core/config.py
class Settings(BaseSettings):
    # Existing settings...

    # AfterShip configuration
    aftership_api_key: str = Field(..., env="AFTERSHIP_API_KEY")
    aftership_webhook_secret: str = Field(..., env="AFTERSHIP_WEBHOOK_SECRET")

    # ShipStation configuration (optional)
    shipstation_api_key: str = Field("", env="SHIPSTATION_API_KEY")
    shipstation_api_secret: str = Field("", env="SHIPSTATION_API_SECRET")

    # Tracking settings
    tracking_cache_ttl: int = Field(1800, env="TRACKING_CACHE_TTL")  # 30 minutes
    tracking_webhook_timeout: int = Field(30, env="TRACKING_WEBHOOK_TIMEOUT")
```

---

## API Endpoints

| Endpoint                                 | Method | Purpose                      |
| ---------------------------------------- | ------ | ---------------------------- |
| `/api/v1/tracking/{tracking_number}`     | GET    | Get tracking information     |
| `/api/v1/orders/{order_number}/tracking` | GET    | Get all tracking for order   |
| `/api/v1/webhooks/aftership`             | POST   | AfterShip webhook receiver   |
| `/api/v1/webhooks/shipstation`           | POST   | ShipStation webhook receiver |

---

## Testing

- [ ] Unit test: AfterShip API client with mocked responses
- [ ] Unit test: Tracking event processing and database updates
- [ ] Unit test: LangChain tracking tools functionality
- [ ] Integration test: Full tracking lookup flow
- [ ] Test: Webhook signature validation
- [ ] Test: Tracking data caching and TTL
- [ ] Test: Multiple tracking numbers per order
- [ ] Test: Carrier auto-detection for tracking numbers
- [ ] Load test: Webhook processing under high volume

---

## Acceptance Criteria

1. Can retrieve real-time tracking information from AfterShip
2. Tracking data is cached appropriately to reduce API calls
3. Webhooks process tracking updates in real-time
4. LangChain tools provide accurate tracking information
5. Multiple tracking numbers per order are handled correctly
6. Tracking status is displayed in customer-friendly language
7. System gracefully handles tracking API failures
8. Webhook signatures are validated for security

---

## Notes

- AfterShip provides free tier with 100 trackings/month for testing
- Consider implementing carrier-specific optimizations for major carriers
- Tracking data should be cleaned up periodically (older than 90 days)
- Consider adding delivery notifications via email/SMS in future phases
- Ensure tracking data privacy and compliance with carrier terms of service

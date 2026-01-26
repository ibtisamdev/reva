# Phase 1: Webhook Handling & Detection

> **Parent:** [M4 Cart Recovery Agent](../m4-cart-recovery.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** M1-M3 complete, Shopify app installed

---

## Goal

Build the foundational webhook infrastructure to reliably capture and process Shopify cart events, enabling real-time abandonment detection.

---

## Tasks

### 1.1 Shopify Webhook Infrastructure

**Location:** `apps/api/app/api/v1/webhooks/shopify.py`

- [ ] Create webhook endpoint `POST /api/v1/webhooks/shopify`
- [ ] Implement HMAC SHA256 signature verification
- [ ] Parse webhook payload and extract event type
- [ ] Route events to appropriate handlers
- [ ] Add webhook registration during app installation
- [ ] Handle webhook verification challenge

**Webhook verification:**

```python
import hmac
import hashlib
from fastapi import HTTPException, Request

async def verify_shopify_webhook(request: Request, body: bytes) -> bool:
    signature = request.headers.get("X-Shopify-Hmac-Sha256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    expected = hmac.new(
        settings.SHOPIFY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)
```

### 1.2 Cart Event Handlers

**Location:** `apps/api/app/services/cart_events.py`

- [ ] Handle `carts/create` - Track new cart creation
- [ ] Handle `carts/update` - Update cart contents and value
- [ ] Handle `checkouts/create` - Mark as high-intent checkout
- [ ] Handle `orders/create` - Stop any active recovery sequences
- [ ] Extract customer information (email, phone, history)
- [ ] Calculate cart value and product details

**Event handler structure:**

```python
from typing import Dict, Any
from app.models.cart import Cart, CartItem
from app.models.customer import Customer

class CartEventHandler:
    async def handle_cart_create(self, payload: Dict[str, Any]) -> Cart:
        """Process new cart creation."""
        cart_data = payload.get("cart", {})

        cart = Cart(
            shopify_cart_id=cart_data["id"],
            store_id=self.store.id,
            customer_email=cart_data.get("email"),
            total_price=float(cart_data.get("total_price", 0)),
            currency=cart_data.get("currency"),
            created_at=cart_data["created_at"],
            updated_at=cart_data["updated_at"]
        )

        # Process line items
        for item_data in cart_data.get("line_items", []):
            cart_item = CartItem(
                cart=cart,
                shopify_variant_id=item_data["variant_id"],
                product_title=item_data["title"],
                quantity=item_data["quantity"],
                price=float(item_data["price"])
            )
            cart.items.append(cart_item)

        self.db.add(cart)
        await self.db.commit()
        return cart
```

### 1.3 Abandonment Detection Logic

**Location:** `apps/api/app/services/abandonment_detector.py`

- [ ] Define abandonment criteria (1 hour of inactivity)
- [ ] Track cart last_activity timestamp
- [ ] Implement abandonment scoring (cart value, customer type, items)
- [ ] Filter out carts that shouldn't trigger recovery (test orders, staff)
- [ ] Schedule abandonment check task

**Abandonment criteria:**

```python
from datetime import datetime, timedelta
from app.models.cart import Cart, CartStatus

class AbandonmentDetector:
    ABANDONMENT_THRESHOLD = timedelta(hours=1)
    MIN_CART_VALUE = 10.00  # Don't recover very low-value carts

    async def check_abandonment(self, cart: Cart) -> bool:
        """Determine if cart should trigger recovery sequence."""

        # Skip if already recovered or completed
        if cart.status in [CartStatus.RECOVERED, CartStatus.COMPLETED]:
            return False

        # Check time threshold
        time_since_update = datetime.utcnow() - cart.updated_at
        if time_since_update < self.ABANDONMENT_THRESHOLD:
            return False

        # Check minimum value
        if cart.total_price < self.MIN_CART_VALUE:
            return False

        # Skip test orders (common patterns)
        if self._is_test_cart(cart):
            return False

        return True

    def _is_test_cart(self, cart: Cart) -> bool:
        """Detect test/staff orders to avoid sending recovery emails."""
        test_indicators = [
            "test@", "example.com", "shopify.com",
            cart.customer_email and "test" in cart.customer_email.lower()
        ]
        return any(test_indicators)
```

### 1.4 Cart Data Models

**Location:** `apps/api/app/models/cart.py`

- [ ] Create Cart model with Shopify cart mapping
- [ ] Create CartItem model for line items
- [ ] Add cart status enum (ACTIVE, ABANDONED, RECOVERED, COMPLETED)
- [ ] Add recovery tracking fields
- [ ] Implement cart value calculations

**Database schema:**

```sql
-- Cart table
CREATE TABLE carts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    shopify_cart_id VARCHAR NOT NULL,
    customer_email VARCHAR,
    customer_phone VARCHAR,
    total_price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status cart_status DEFAULT 'ACTIVE',
    abandonment_detected_at TIMESTAMP,
    recovery_sequence_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(store_id, shopify_cart_id)
);

-- Cart items table
CREATE TABLE cart_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    shopify_variant_id VARCHAR NOT NULL,
    product_title VARCHAR NOT NULL,
    variant_title VARCHAR,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cart status enum
CREATE TYPE cart_status AS ENUM ('ACTIVE', 'ABANDONED', 'RECOVERED', 'COMPLETED');
```

### 1.5 Webhook Registration

**Location:** `apps/api/app/services/shopify_webhooks.py`

- [ ] Register webhooks during app installation
- [ ] Handle webhook endpoint updates
- [ ] Implement webhook cleanup on app uninstall
- [ ] Add webhook health monitoring

**Webhook registration:**

```python
import httpx
from app.core.config import settings

class ShopifyWebhookManager:
    def __init__(self, store_domain: str, access_token: str):
        self.store_domain = store_domain
        self.access_token = access_token
        self.base_url = f"https://{store_domain}/admin/api/2024-01/webhooks.json"

    async def register_cart_webhooks(self) -> list[dict]:
        """Register all required cart-related webhooks."""
        webhooks = [
            {
                "webhook": {
                    "topic": "carts/create",
                    "address": f"{settings.API_BASE_URL}/api/v1/webhooks/shopify",
                    "format": "json"
                }
            },
            {
                "webhook": {
                    "topic": "carts/update",
                    "address": f"{settings.API_BASE_URL}/api/v1/webhooks/shopify",
                    "format": "json"
                }
            },
            {
                "webhook": {
                    "topic": "checkouts/create",
                    "address": f"{settings.API_BASE_URL}/api/v1/webhooks/shopify",
                    "format": "json"
                }
            },
            {
                "webhook": {
                    "topic": "orders/create",
                    "address": f"{settings.API_BASE_URL}/api/v1/webhooks/shopify",
                    "format": "json"
                }
            }
        ]

        registered = []
        async with httpx.AsyncClient() as client:
            for webhook_data in webhooks:
                response = await client.post(
                    self.base_url,
                    json=webhook_data,
                    headers={"X-Shopify-Access-Token": self.access_token}
                )
                if response.status_code == 201:
                    registered.append(response.json()["webhook"])

        return registered
```

### 1.6 Event Processing Pipeline

**Location:** `apps/api/app/workers/webhook_tasks.py`

- [ ] Create async task for webhook processing
- [ ] Implement retry logic for failed processing
- [ ] Add webhook event logging and monitoring
- [ ] Handle duplicate webhook deliveries

**Celery task:**

```python
from celery import current_app as celery_app
from app.services.cart_events import CartEventHandler
from app.services.abandonment_detector import AbandonmentDetector

@celery_app.task(bind=True, max_retries=3)
async def process_cart_webhook(self, store_id: str, event_type: str, payload: dict):
    """Process Shopify cart webhook asynchronously."""
    try:
        handler = CartEventHandler(store_id)
        detector = AbandonmentDetector()

        if event_type == "carts/create":
            cart = await handler.handle_cart_create(payload)

        elif event_type == "carts/update":
            cart = await handler.handle_cart_update(payload)

            # Check if cart is now abandoned
            if await detector.check_abandonment(cart):
                from app.workers.recovery_tasks import start_recovery_sequence
                start_recovery_sequence.delay(cart.id)

        elif event_type == "orders/create":
            await handler.handle_order_create(payload)

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

---

## Files to Create/Modify

| File                                      | Action | Purpose                     |
| ----------------------------------------- | ------ | --------------------------- |
| `app/api/v1/webhooks/__init__.py`         | Create | Package init                |
| `app/api/v1/webhooks/shopify.py`          | Create | Webhook endpoint handlers   |
| `app/services/cart_events.py`             | Create | Cart event processing       |
| `app/services/abandonment_detector.py`    | Create | Abandonment detection logic |
| `app/services/shopify_webhooks.py`        | Create | Webhook registration        |
| `app/models/cart.py`                      | Create | Cart and CartItem models    |
| `app/schemas/cart.py`                     | Create | Pydantic schemas for carts  |
| `app/workers/webhook_tasks.py`            | Create | Async webhook processing    |
| `alembic/versions/xxx_add_cart_tables.py` | Create | Database migration          |

---

## Dependencies

```toml
# Add to pyproject.toml
httpx = "^0.27"        # Shopify API calls
celery = "^5.3"        # Async task processing
redis = "^5.0"         # Celery broker
```

---

## Testing

- [ ] Unit test: webhook signature verification
- [ ] Unit test: cart event parsing and storage
- [ ] Unit test: abandonment detection logic
- [ ] Integration test: full webhook → database flow
- [ ] Test: webhook registration during app install
- [ ] Test: duplicate webhook handling
- [ ] Test: malformed webhook payload handling

---

## Acceptance Criteria

1. Shopify webhooks are successfully registered during app installation
2. Cart creation/update events are captured and stored correctly
3. Abandonment detection triggers after 1 hour of inactivity
4. Order completion stops any active recovery sequences
5. Webhook processing is resilient to failures and retries
6. Test/staff carts are filtered out from recovery
7. All webhook events are logged for debugging

---

## Notes

- Start with basic webhook handling, add advanced filtering iteratively
- Monitor webhook delivery success rates in Shopify Partner Dashboard
- Consider webhook endpoint health checks for reliability
- Implement proper logging for debugging webhook issues

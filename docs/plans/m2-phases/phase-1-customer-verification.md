# Phase 1: Customer Verification & Order Lookup

> **Parent:** [M2 Order Status Agent](../m2-order-status.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** M1 complete, Shopify OAuth integration

---

## Goal

Build secure customer verification and Shopify order lookup functionality. Customers can verify their identity using order number + email, and the agent can retrieve order details from Shopify.

---

## Tasks

### 1.1 Customer Verification Service

**Location:** `apps/api/app/services/verification.py`

- [ ] Create customer verification endpoint `POST /api/v1/orders/verify`
- [ ] Implement order number + email matching
- [ ] Support multiple verification methods:
  - [ ] Order number + email (primary)
  - [ ] Order number + phone (fallback)
  - [ ] Order number + billing zip code (fallback)
- [ ] Rate limiting for verification attempts (5 per minute per IP)
- [ ] Audit logging for verification attempts
- [ ] Return verification token for subsequent order queries

**Verification Logic:**

```python
async def verify_customer(
    order_number: str,
    email: str,
    store_id: UUID
) -> VerificationResult:
    """
    Verify customer identity against order data.

    Returns:
        VerificationResult with success status and verification_token
    """
    # 1. Query Shopify for order by number
    # 2. Check if email matches order email
    # 3. Generate short-lived verification token (15 min)
    # 4. Log verification attempt
    # 5. Return result
```

### 1.2 Shopify Order Service

**Location:** `apps/api/app/services/orders.py`

- [ ] Create Shopify order client wrapper
- [ ] Implement order lookup by number
- [ ] Implement order lookup by email
- [ ] Handle Shopify API rate limits with exponential backoff
- [ ] Cache order data in Redis (15 minute TTL)
- [ ] Support order status mapping to customer-friendly messages

**Shopify API Integration:**

```python
class ShopifyOrderService:
    def __init__(self, store: Store):
        self.store = store
        self.client = ShopifyClient(store.shopify_access_token)

    async def get_order_by_number(self, order_number: str) -> Order | None:
        """Get order by order number from Shopify."""

    async def get_orders_by_email(self, email: str) -> list[Order]:
        """Get all orders for customer email."""

    async def get_order_fulfillments(self, order_id: str) -> list[Fulfillment]:
        """Get fulfillment/tracking info for order."""
```

### 1.3 Order Lookup Tools (LangChain)

**Location:** `apps/api/app/tools/order_tools.py`

- [ ] Create `OrderLookupTool` for LangChain integration
- [ ] Create `CustomerVerificationTool` for identity checks
- [ ] Implement structured output schemas for order data
- [ ] Handle tool calling errors gracefully
- [ ] Support multi-order scenarios (customer with multiple orders)

**LangChain Tool Definition:**

```python
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

class OrderLookupInput(BaseModel):
    order_number: str = Field(description="Order number to lookup")
    verification_token: str = Field(description="Customer verification token")

class OrderLookupTool(BaseTool):
    name = "order_lookup"
    description = "Look up order details after customer verification"
    args_schema = OrderLookupInput

    def _run(self, order_number: str, verification_token: str) -> str:
        # Validate verification token
        # Fetch order from Shopify
        # Return formatted order details
```

### 1.4 Order Status Templates

**Location:** `apps/api/app/templates/order_responses.py`

- [ ] Create response templates for each order status
- [ ] Include order timeline information
- [ ] Support dynamic content (order number, dates, amounts)
- [ ] Handle edge cases (cancelled orders, refunds, exchanges)

**Response Templates:**

```python
ORDER_STATUS_TEMPLATES = {
    "pending": "Great news! Your order #{order_number} is confirmed and being prepared. We'll send you tracking information once it ships.",

    "paid": "Your order #{order_number} has been received and we're packing it now! Expected to ship within {processing_time}.",

    "fulfilled": "Your order #{order_number} has shipped! 📦\n\nTracking: {tracking_number}\nCarrier: {carrier}\nExpected delivery: {estimated_delivery}",

    "refunded": "Your order #{order_number} has been refunded. The refund of ${refund_amount} should appear in your account within 3-5 business days."
}
```

### 1.5 Enhanced Chat Service Integration

**Location:** `apps/api/app/services/chat.py` (modify existing)

- [ ] Integrate order tools into existing chat pipeline
- [ ] Detect order-related queries using intent classification
- [ ] Route to order lookup flow when appropriate
- [ ] Maintain conversation context with order information
- [ ] Handle verification failures gracefully

**Intent Detection:**

```python
ORDER_INTENT_KEYWORDS = [
    "order", "tracking", "shipped", "delivery", "where is my",
    "order status", "order number", "tracking number"
]

async def detect_order_intent(message: str) -> bool:
    """Detect if message is asking about order status."""
    # Simple keyword matching or use classification model
```

### 1.6 Order API Endpoints

**Location:** `apps/api/app/api/v1/orders.py`

- [ ] `POST /api/v1/orders/verify` - Customer verification
- [ ] `GET /api/v1/orders/{order_number}` - Get order details (requires verification)
- [ ] `GET /api/v1/orders/customer/{email}` - Get customer's orders (requires verification)
- [ ] `POST /api/v1/orders/lookup` - Tool endpoint for LangChain

**API Endpoints:**

```python
@router.post("/verify")
async def verify_customer(
    request: CustomerVerificationRequest,
    db: AsyncSession = Depends(get_db)
) -> CustomerVerificationResponse:
    """Verify customer identity for order access."""

@router.get("/{order_number}")
async def get_order(
    order_number: str,
    verification_token: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> OrderResponse:
    """Get order details after verification."""
```

### 1.7 Magic Link Authentication (Optional)

**Location:** `apps/api/app/services/auth_links.py`

- [ ] Generate secure magic links for customer authentication
- [ ] Send magic links via email (using existing email service)
- [ ] Validate magic link tokens (JWT with 1 hour expiry)
- [ ] Create authenticated sessions for verified customers
- [ ] Support full order history access after magic link auth

**Magic Link Flow:**

```python
async def send_magic_link(email: str, store_id: UUID) -> bool:
    """Send magic link to customer email."""
    # 1. Generate JWT token with email + store_id
    # 2. Create magic link URL
    # 3. Send email with link
    # 4. Return success status

async def verify_magic_link(token: str) -> CustomerSession | None:
    """Verify magic link token and create session."""
    # 1. Decode JWT token
    # 2. Validate expiry and signature
    # 3. Create customer session
    # 4. Return session or None
```

---

## Files to Create/Modify

| File                               | Action | Purpose                         |
| ---------------------------------- | ------ | ------------------------------- |
| `app/services/verification.py`     | Create | Customer identity verification  |
| `app/services/orders.py`           | Create | Shopify order operations        |
| `app/services/auth_links.py`       | Create | Magic link authentication       |
| `app/tools/__init__.py`            | Create | Tools package init              |
| `app/tools/order_tools.py`         | Create | LangChain order tools           |
| `app/templates/order_responses.py` | Create | Order status response templates |
| `app/api/v1/orders.py`             | Create | Order API endpoints             |
| `app/schemas/orders.py`            | Create | Pydantic models for orders      |
| `app/schemas/verification.py`      | Create | Verification request/response   |
| `app/services/chat.py`             | Modify | Add order intent detection      |
| `app/core/shopify.py`              | Create | Shopify API client wrapper      |

---

## Dependencies

```toml
# Add to pyproject.toml
shopify-python-api = "^12.0"  # Shopify API client
redis = "^5.0"                # Order caching
pyjwt = "^2.8"               # Magic link tokens
langchain = "^0.1"           # Tool framework
langchain-openai = "^0.1"    # OpenAI tools integration
```

---

## Database Schema Updates

```sql
-- Add verification attempts tracking
CREATE TABLE verification_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    order_number VARCHAR(100),
    email VARCHAR(255),
    ip_address INET,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add customer sessions for magic links
CREATE TABLE customer_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    email VARCHAR(255) NOT NULL,
    session_token VARCHAR(500) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_verification_attempts_store_ip ON verification_attempts(store_id, ip_address);
CREATE INDEX idx_customer_sessions_token ON customer_sessions(session_token);
```

---

## Testing

- [ ] Unit test: Order number + email verification logic
- [ ] Unit test: Shopify API client with mocked responses
- [ ] Unit test: LangChain tool calling with order data
- [ ] Integration test: Full verification → order lookup flow
- [ ] Test: Rate limiting on verification attempts
- [ ] Test: Magic link generation and validation
- [ ] Test: Order status template rendering
- [ ] Test: Multi-tenant isolation (customers can't see other store orders)

---

## Acceptance Criteria

1. Customer can verify identity using order number + email
2. Verified customers can access their order details
3. Order status is displayed in customer-friendly language
4. System handles Shopify API rate limits gracefully
5. Verification attempts are rate limited and logged
6. Magic link authentication works end-to-end (optional)
7. Multi-tenant security: customers only see their store's orders
8. LangChain tools integrate seamlessly with chat service

---

## Notes

- Start with basic order number + email verification
- Add magic link authentication as enhancement
- Cache order data to reduce Shopify API calls
- Consider implementing order webhooks for real-time updates in future phases
- Ensure PCI compliance for any payment-related data handling

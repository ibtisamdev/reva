# Phase 2: Webhooks System

> **Parent:** [M8 Developer Platform](../m8-developer-platform.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Public API)

---

## Goal

Build a reliable webhook system that delivers real-time event notifications to external systems with retry logic, signature verification, and comprehensive event coverage.

---

## Tasks

### 2.1 Webhook Registration & Management

**Location:** `apps/api/app/models/webhooks.py`

- [ ] Create `webhooks` table with schema:

  ```sql
  CREATE TABLE webhooks (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    url VARCHAR(500) NOT NULL,
    events_json JSONB NOT NULL,
    secret_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    failure_count INTEGER DEFAULT 0,
    last_success_at TIMESTAMP,
    last_failure_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
  );

  CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY,
    webhook_id UUID REFERENCES webhooks(id),
    event_type VARCHAR(100) NOT NULL,
    payload_json JSONB NOT NULL,
    status VARCHAR(20) NOT NULL, -- pending, success, failed, abandoned
    attempts INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP,
    response_status INTEGER,
    response_body TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    delivered_at TIMESTAMP
  );
  ```

- [ ] Webhook CRUD API endpoints:

  ```python
  # apps/api/app/api/v1/public/webhooks.py

  @router.post("/webhooks")
  async def create_webhook(
      webhook: WebhookCreate,
      auth: OAuth2Token = Depends(require_scope("webhooks:write"))
  ):
      """Register a new webhook endpoint."""

  @router.get("/webhooks")
  async def list_webhooks(
      auth: OAuth2Token = Depends(require_scope("webhooks:read"))
  ):
      """List all webhook subscriptions."""

  @router.patch("/webhooks/{webhook_id}")
  async def update_webhook(
      webhook_id: UUID,
      updates: WebhookUpdate,
      auth: OAuth2Token = Depends(require_scope("webhooks:write"))
  ):
      """Update webhook configuration."""

  @router.delete("/webhooks/{webhook_id}")
  async def delete_webhook(
      webhook_id: UUID,
      auth: OAuth2Token = Depends(require_scope("webhooks:write"))
  ):
      """Delete webhook subscription."""
  ```

### 2.2 Event System Architecture

**Location:** `apps/api/app/services/events.py`

- [ ] Define comprehensive event types:

  ```python
  class EventType(str, Enum):
      # Conversation events
      CONVERSATION_CREATED = "conversation.created"
      CONVERSATION_RESOLVED = "conversation.resolved"
      CONVERSATION_ESCALATED = "conversation.escalated"

      # Message events
      MESSAGE_RECEIVED = "message.received"
      MESSAGE_SENT = "message.sent"

      # Action events
      ACTION_REQUESTED = "action.requested"
      ACTION_COMPLETED = "action.completed"

      # Cart events
      CART_ABANDONED = "cart.abandoned"
      CART_RECOVERED = "cart.recovered"

      # Customer events
      CUSTOMER_CREATED = "customer.created"
      CUSTOMER_UPDATED = "customer.updated"

      # Feedback events
      FEEDBACK_RECEIVED = "feedback.received"
  ```

- [ ] Event payload standardization:

  ```python
  class WebhookEvent(BaseModel):
      event: EventType
      timestamp: datetime
      store_id: UUID
      data: Dict[str, Any]
      version: str = "2024-01-01"
  ```

- [ ] Event emission service:
  ```python
  class EventEmitter:
      async def emit(self, event_type: EventType, store_id: UUID, data: dict):
          """Emit event to all subscribed webhooks."""

      async def emit_conversation_created(self, conversation: Conversation):
          """Convenience method for conversation events."""

      async def emit_message_received(self, message: Message, intent: str):
          """Convenience method for message events."""
  ```

### 2.3 Webhook Delivery Service

**Location:** `apps/api/app/services/webhook_delivery.py`

- [ ] Implement reliable delivery with retry logic:

  ```python
  class WebhookDeliveryService:
      RETRY_SCHEDULE = [60, 300, 900, 3600, 7200]  # 1m, 5m, 15m, 1h, 2h

      async def deliver_webhook(self, webhook: Webhook, event: WebhookEvent):
          """Deliver single webhook with retry logic."""

      async def process_delivery_queue(self):
          """Background task to process failed deliveries."""

      async def mark_webhook_failed(self, webhook_id: UUID):
          """Disable webhook after too many failures."""
  ```

- [ ] HTTP delivery implementation:

  ```python
  async def send_webhook_request(
      url: str,
      payload: dict,
      signature: str,
      timeout: int = 30
  ) -> WebhookResponse:
      """Send HTTP POST with proper headers and timeout."""
      headers = {
          "Content-Type": "application/json",
          "X-Reva-Signature": signature,
          "X-Reva-Event": payload["event"],
          "X-Reva-Delivery": str(uuid4()),
          "User-Agent": "Reva-Webhooks/1.0"
      }
  ```

- [ ] Celery task for async processing:
  ```python
  @celery_app.task(bind=True, max_retries=5)
  def deliver_webhook_task(self, webhook_id: str, event_data: dict):
      """Async webhook delivery task."""
  ```

### 2.4 Signature Verification

**Location:** `apps/api/app/services/webhook_security.py`

- [ ] HMAC-SHA256 signature generation:

  ```python
  def generate_signature(payload: bytes, secret: str) -> str:
      """Generate HMAC-SHA256 signature for webhook payload."""
      signature = hmac.new(
          secret.encode('utf-8'),
          payload,
          hashlib.sha256
      ).hexdigest()
      return f"sha256={signature}"

  def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
      """Verify webhook signature."""
      expected = generate_signature(payload, secret)
      return hmac.compare_digest(signature, expected)
  ```

- [ ] Webhook secret management:
  ```python
  def generate_webhook_secret() -> str:
      """Generate cryptographically secure webhook secret."""
      return secrets.token_urlsafe(32)
  ```

### 2.5 Event Integration Points

**Location:** Various service files

- [ ] Integrate event emission into existing services:

  ```python
  # In conversation service
  async def create_conversation(self, data: ConversationCreate) -> Conversation:
      conversation = await self.repository.create(data)

      # Emit event
      await self.event_emitter.emit_conversation_created(conversation)

      return conversation

  # In chat service
  async def send_message(self, conversation_id: UUID, content: str) -> Message:
      message = await self.repository.create_message(conversation_id, content)

      # Emit event with detected intent
      intent = await self.intent_detector.detect(content)
      await self.event_emitter.emit_message_received(message, intent)

      return message
  ```

- [ ] Action tracking integration:
  ```python
  # In action service
  async def execute_action(self, action: ActionRequest) -> ActionResult:
      # Emit action requested
      await self.event_emitter.emit(
          EventType.ACTION_REQUESTED,
          action.store_id,
          {"action_type": action.type, "parameters": action.parameters}
      )

      result = await self._execute(action)

      # Emit action completed
      await self.event_emitter.emit(
          EventType.ACTION_COMPLETED,
          action.store_id,
          {"action_type": action.type, "result": result.dict()}
      )

      return result
  ```

### 2.6 Webhook Testing & Debugging

**Location:** `apps/api/app/api/v1/public/webhook_testing.py`

- [ ] Webhook testing endpoint:

  ```python
  @router.post("/webhooks/{webhook_id}/test")
  async def test_webhook(
      webhook_id: UUID,
      event_type: EventType,
      auth: OAuth2Token = Depends(require_scope("webhooks:write"))
  ):
      """Send test event to webhook for debugging."""
  ```

- [ ] Delivery logs API:

  ```python
  @router.get("/webhooks/{webhook_id}/deliveries")
  async def get_webhook_deliveries(
      webhook_id: UUID,
      limit: int = 50,
      status: Optional[str] = None,
      auth: OAuth2Token = Depends(require_scope("webhooks:read"))
  ):
      """Get webhook delivery history for debugging."""
  ```

- [ ] Webhook health monitoring:
  ```python
  @router.get("/webhooks/{webhook_id}/health")
  async def get_webhook_health(
      webhook_id: UUID,
      auth: OAuth2Token = Depends(require_scope("webhooks:read"))
  ):
      """Get webhook success rate and performance metrics."""
  ```

---

## Event Payload Examples

### Conversation Created

```json
{
  "event": "conversation.created",
  "timestamp": "2026-01-24T10:30:00Z",
  "store_id": "shop_123",
  "data": {
    "conversation_id": "conv_abc123",
    "customer_email": "john@example.com",
    "channel": "widget",
    "initial_message": "I need help with my order",
    "page_url": "/products/winter-jacket",
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1"
  },
  "version": "2024-01-01"
}
```

### Conversation Escalated

```json
{
  "event": "conversation.escalated",
  "timestamp": "2026-01-24T10:35:00Z",
  "store_id": "shop_123",
  "data": {
    "conversation_id": "conv_abc123",
    "customer_email": "john@example.com",
    "escalation_reason": "refund_over_limit",
    "ai_summary": "Customer wants $500 refund, exceeds $100 auto-approval",
    "sentiment": "frustrated",
    "priority": "high",
    "messages_count": 5,
    "duration_seconds": 300
  },
  "version": "2024-01-01"
}
```

### Action Completed

```json
{
  "event": "action.completed",
  "timestamp": "2026-01-24T10:32:00Z",
  "store_id": "shop_123",
  "data": {
    "conversation_id": "conv_abc123",
    "action_type": "cancel_order",
    "parameters": {
      "order_id": "order_456",
      "reason": "customer_request"
    },
    "result": {
      "success": true,
      "refund_amount": 89.99,
      "refund_id": "refund_789"
    },
    "execution_time_ms": 1250
  },
  "version": "2024-01-01"
}
```

---

## Files to Create/Modify

| File                                   | Action | Purpose                   |
| -------------------------------------- | ------ | ------------------------- |
| `app/models/webhooks.py`               | Create | Webhook data models       |
| `app/services/events.py`               | Create | Event system core         |
| `app/services/webhook_delivery.py`     | Create | Webhook delivery logic    |
| `app/services/webhook_security.py`     | Create | Signature verification    |
| `app/api/v1/public/webhooks.py`        | Create | Webhook management API    |
| `app/api/v1/public/webhook_testing.py` | Create | Webhook testing endpoints |
| `app/schemas/public/webhooks.py`       | Create | Webhook Pydantic schemas  |
| `app/workers/webhook_tasks.py`         | Create | Celery tasks for delivery |
| `app/services/conversation.py`         | Modify | Add event emission        |
| `app/services/chat.py`                 | Modify | Add message events        |
| `app/services/actions.py`              | Modify | Add action events         |
| `alembic/versions/xxx_add_webhooks.py` | Create | Database migration        |

---

## Dependencies

```toml
# Add to pyproject.toml
celery = "^5.3"           # Async task processing
redis = "^5.0"            # Celery broker
httpx = "^0.27"           # HTTP client for webhook delivery
```

---

## Testing

- [ ] Unit tests for signature generation and verification
- [ ] Unit tests for event emission and payload formatting
- [ ] Integration tests for webhook delivery with mock endpoints
- [ ] Load testing for high-volume event processing
- [ ] Failure scenario testing (network errors, timeouts, invalid URLs)
- [ ] Retry logic testing with different failure patterns

**Example Tests:**

```python
@pytest.mark.asyncio
async def test_webhook_signature_verification():
    secret = "webhook_secret_123"
    payload = b'{"event": "test", "data": {}}'

    signature = generate_signature(payload, secret)
    assert verify_signature(payload, signature, secret) is True

    # Test invalid signature
    assert verify_signature(payload, "invalid", secret) is False

@pytest.mark.asyncio
async def test_webhook_delivery_retry():
    # Mock failing webhook endpoint
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.Response(500),
            httpx.Response(200)
        ]

        delivery_service = WebhookDeliveryService()
        result = await delivery_service.deliver_webhook(webhook, event)

        assert result.success is True
        assert mock_post.call_count == 3  # 2 failures + 1 success

@pytest.mark.asyncio
async def test_event_emission():
    conversation = await create_test_conversation()

    with patch('app.services.webhook_delivery.deliver_webhook') as mock_deliver:
        await event_emitter.emit_conversation_created(conversation)

        # Verify webhook was called with correct payload
        mock_deliver.assert_called_once()
        event_data = mock_deliver.call_args[0][1]
        assert event_data.event == "conversation.created"
        assert event_data.data["conversation_id"] == str(conversation.id)
```

---

## Acceptance Criteria

1. **Webhook Registration:** Can create, update, delete webhook subscriptions via API
2. **Event Delivery:** All defined events are delivered to subscribed webhooks
3. **Signature Security:** All webhook payloads include valid HMAC signatures
4. **Retry Logic:** Failed deliveries are retried with exponential backoff
5. **Failure Handling:** Webhooks are disabled after repeated failures
6. **Testing Tools:** Can test webhooks and view delivery logs
7. **Performance:** Can handle 1000+ events per minute without delays
8. **Reliability:** 99%+ delivery success rate for healthy endpoints

---

## Notes

- Start with core events (conversation, message), add others iteratively
- Consider webhook payload size limits (keep under 1MB)
- Implement webhook URL validation (must be HTTPS in production)
- Add webhook delivery metrics to analytics dashboard
- Consider implementing webhook subscriptions by event pattern matching

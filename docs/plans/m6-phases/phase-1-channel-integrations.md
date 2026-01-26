# Phase 1: Channel Integrations

> **Parent:** [M6 Omnichannel Deployment](../m6-omnichannel.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** M1-M5 complete

---

## Goal

Establish core channel integrations for email inbound, WhatsApp Business, and SMS via Twilio. Build the foundational message handling infrastructure that normalizes all channels into a unified format.

---

## Tasks

### 1.1 Message Normalization Infrastructure

**Location:** `apps/api/app/omnichannel/normalizer.py`

- [ ] Create unified message format schema
- [ ] Implement channel detection and routing
- [ ] Build customer identification logic (email, phone matching)
- [ ] Create message validation and sanitization
- [ ] Add support for attachments/media across channels

**Unified Message Schema:**

```python
@dataclass
class UnifiedMessage:
    id: UUID
    channel: ChannelType  # EMAIL, WHATSAPP, SMS, CHAT
    customer_identifier: str  # email or phone
    content: str
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    timestamp: datetime
    store_id: UUID
```

### 1.2 Email Inbound Integration

**Location:** `apps/api/app/omnichannel/channels/email.py`

- [ ] Set up SendGrid/Resend inbound parse webhook
- [ ] Create email parsing endpoint `POST /api/v1/omnichannel/email/inbound`
- [ ] Extract customer email, subject, body content
- [ ] Handle email threading (Reply-To, In-Reply-To headers)
- [ ] Support HTML and plain text email formats
- [ ] Parse and store email attachments
- [ ] Implement email response sending

**Email Webhook Handler:**

```python
@router.post("/email/inbound")
async def handle_inbound_email(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # Parse SendGrid inbound email format
    form_data = await request.form()

    message = UnifiedMessage(
        channel=ChannelType.EMAIL,
        customer_identifier=form_data.get("from"),
        content=form_data.get("text", form_data.get("html")),
        metadata={
            "subject": form_data.get("subject"),
            "to": form_data.get("to"),
            "message_id": form_data.get("headers", {}).get("Message-ID")
        }
    )

    await process_unified_message(message, db)
```

### 1.3 WhatsApp Business Integration

**Location:** `apps/api/app/omnichannel/channels/whatsapp.py`

- [ ] Set up Twilio WhatsApp Business API credentials
- [ ] Create WhatsApp webhook endpoint `POST /api/v1/omnichannel/whatsapp/webhook`
- [ ] Handle incoming WhatsApp messages
- [ ] Support WhatsApp media messages (images, documents)
- [ ] Implement WhatsApp message status tracking (delivered, read)
- [ ] Add WhatsApp-specific formatting (emojis, quick replies)
- [ ] Handle WhatsApp business profile integration

**WhatsApp Message Handler:**

```python
@router.post("/whatsapp/webhook")
async def handle_whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    webhook_data = await request.json()

    for entry in webhook_data.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "messages":
                for message in change.get("value", {}).get("messages", []):
                    unified_msg = UnifiedMessage(
                        channel=ChannelType.WHATSAPP,
                        customer_identifier=message["from"],
                        content=message.get("text", {}).get("body", ""),
                        metadata={
                            "whatsapp_id": message["id"],
                            "type": message.get("type")
                        }
                    )
                    await process_unified_message(unified_msg, db)
```

### 1.4 SMS Integration

**Location:** `apps/api/app/omnichannel/channels/sms.py`

- [ ] Set up Twilio SMS API integration
- [ ] Create SMS webhook endpoint `POST /api/v1/omnichannel/sms/webhook`
- [ ] Handle incoming SMS messages
- [ ] Implement SMS response sending
- [ ] Add SMS-specific formatting (160 char limit handling)
- [ ] Support SMS delivery status tracking
- [ ] Handle SMS opt-out/opt-in management

**SMS Message Handler:**

```python
@router.post("/sms/webhook")
async def handle_sms_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    form_data = await request.form()

    message = UnifiedMessage(
        channel=ChannelType.SMS,
        customer_identifier=form_data.get("From"),
        content=form_data.get("Body", ""),
        metadata={
            "sms_sid": form_data.get("MessageSid"),
            "to": form_data.get("To")
        }
    )

    await process_unified_message(message, db)
```

### 1.5 Channel Response Formatters

**Location:** `apps/api/app/omnichannel/formatters.py`

- [ ] Create channel-specific response formatting
- [ ] Email formatter (HTML templates, proper headers)
- [ ] WhatsApp formatter (emoji support, quick replies)
- [ ] SMS formatter (length constraints, link shortening)
- [ ] Implement response delivery tracking

**Response Formatting:**

```python
class ResponseFormatter:
    @staticmethod
    def format_for_channel(
        response: str,
        channel: ChannelType,
        metadata: dict = None
    ) -> FormattedResponse:
        if channel == ChannelType.EMAIL:
            return EmailFormatter.format(response, metadata)
        elif channel == ChannelType.WHATSAPP:
            return WhatsAppFormatter.format(response, metadata)
        elif channel == ChannelType.SMS:
            return SMSFormatter.format(response, metadata)
        else:
            return response
```

### 1.6 Database Schema Updates

**Location:** `apps/api/alembic/versions/`

- [ ] Create `channels` table for channel configurations
- [ ] Add `channel_type` to conversations table
- [ ] Create `customer_identifiers` table for cross-channel matching
- [ ] Add `message_metadata` JSONB column for channel-specific data
- [ ] Create indexes for efficient channel-based queries

**Database Schema:**

```sql
-- Channel configurations per store
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    channel_type VARCHAR(20) NOT NULL, -- EMAIL, WHATSAPP, SMS
    configuration JSONB NOT NULL, -- API keys, webhooks, etc.
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Customer identity mapping across channels
CREATE TABLE customer_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    customer_profile_id UUID, -- Will be created in Phase 2
    identifier_type VARCHAR(20) NOT NULL, -- EMAIL, PHONE
    identifier_value VARCHAR(255) NOT NULL,
    verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(store_id, identifier_type, identifier_value)
);

-- Add channel info to existing conversations
ALTER TABLE conversations ADD COLUMN channel_type VARCHAR(20) DEFAULT 'CHAT';
ALTER TABLE conversations ADD COLUMN customer_identifier VARCHAR(255);
ALTER TABLE messages ADD COLUMN channel_metadata JSONB;
```

---

## Files to Create/Modify

| File                                   | Action | Purpose                     |
| -------------------------------------- | ------ | --------------------------- |
| `app/omnichannel/__init__.py`          | Create | Package init                |
| `app/omnichannel/normalizer.py`        | Create | Message normalization       |
| `app/omnichannel/channels/__init__.py` | Create | Channel package init        |
| `app/omnichannel/channels/email.py`    | Create | Email inbound handling      |
| `app/omnichannel/channels/whatsapp.py` | Create | WhatsApp integration        |
| `app/omnichannel/channels/sms.py`      | Create | SMS integration             |
| `app/omnichannel/formatters.py`        | Create | Channel-specific formatting |
| `app/schemas/omnichannel.py`           | Create | Pydantic models             |
| `app/api/v1/omnichannel.py`            | Create | Omnichannel endpoints       |
| `app/services/channel_service.py`      | Create | Channel management service  |
| `app/core/config.py`                   | Modify | Add Twilio/SendGrid config  |

---

## Dependencies

```toml
# Add to pyproject.toml
twilio = "^8.0"                    # WhatsApp and SMS
sendgrid = "^6.0"                  # Email sending
python-multipart = "^0.0.6"       # Form data parsing
phonenumbers = "^8.13"             # Phone number validation
email-validator = "^2.1"          # Email validation
```

**Environment Variables:**

```bash
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# SendGrid
SENDGRID_API_KEY=your_sendgrid_key
SENDGRID_FROM_EMAIL=support@yourstore.com

# Webhooks
OMNICHANNEL_WEBHOOK_BASE_URL=https://api.reva.ai/api/v1/omnichannel
```

---

## Testing

- [ ] Unit test: Message normalization from each channel
- [ ] Unit test: Customer identifier extraction and validation
- [ ] Unit test: Response formatting for each channel
- [ ] Integration test: Email inbound webhook processing
- [ ] Integration test: WhatsApp message flow (send/receive)
- [ ] Integration test: SMS message flow (send/receive)
- [ ] Load test: Concurrent messages from multiple channels

**Test Examples:**

```python
@pytest.mark.asyncio
async def test_email_message_normalization():
    email_data = {
        "from": "customer@example.com",
        "subject": "Order question",
        "text": "When will my order ship?"
    }

    normalized = await normalize_email_message(email_data)

    assert normalized.channel == ChannelType.EMAIL
    assert normalized.customer_identifier == "customer@example.com"
    assert "Order question" in normalized.metadata["subject"]

@pytest.mark.asyncio
async def test_whatsapp_response_formatting():
    response = "Your order #1234 will ship tomorrow! 📦"

    formatted = ResponseFormatter.format_for_channel(
        response,
        ChannelType.WHATSAPP
    )

    assert "📦" in formatted.content  # Emoji preserved
    assert formatted.channel_specific_data is not None
```

---

## Acceptance Criteria

1. Can receive and process inbound emails with proper customer identification
2. WhatsApp messages are received, processed, and responses sent successfully
3. SMS messages work bidirectionally with proper formatting
4. All channels produce normalized messages in unified format
5. Response formatting respects channel-specific constraints and features
6. Webhook endpoints are secure and handle failures gracefully
7. Database properly stores channel-specific metadata

---

## Notes

- Start with email integration as it's most straightforward
- WhatsApp Business API requires approval - begin application process early
- SMS should handle opt-out compliance (STOP/START keywords)
- Consider rate limiting for each channel to avoid API limits
- Implement proper webhook signature validation for security

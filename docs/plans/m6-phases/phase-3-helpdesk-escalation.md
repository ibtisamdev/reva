# Phase 3: Helpdesk Escalation

> **Parent:** [M6 Omnichannel Deployment](../m6-omnichannel.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1-2 complete

---

## Goal

Build seamless escalation to human agents through popular helpdesk integrations. When AI cannot resolve complex issues, automatically create tickets with full conversation context in Slack, Zendesk, Freshdesk, and other platforms.

---

## Tasks

### 3.1 Escalation Detection System

**Location:** `apps/api/app/omnichannel/escalation.py`

- [ ] Implement escalation trigger detection
- [ ] Build confidence scoring for AI responses
- [ ] Create escalation rules engine (keywords, sentiment, complexity)
- [ ] Add manual escalation request handling
- [ ] Implement escalation priority classification
- [ ] Build escalation analytics and reporting

**Escalation Triggers:**

```python
@dataclass
class EscalationTrigger:
    trigger_type: EscalationType  # AUTO, MANUAL, SENTIMENT, KEYWORD
    confidence_threshold: float = 0.7
    keywords: list[str] = field(default_factory=list)
    sentiment_threshold: float = -0.5
    max_conversation_turns: int = 10

class EscalationDetector:
    async def should_escalate(
        self,
        conversation: Conversation,
        ai_response_confidence: float,
        customer_sentiment: float
    ) -> EscalationDecision:
        """Determine if conversation should be escalated"""

        triggers = []

        # Low AI confidence
        if ai_response_confidence < self.config.confidence_threshold:
            triggers.append(EscalationType.LOW_CONFIDENCE)

        # Negative sentiment
        if customer_sentiment < self.config.sentiment_threshold:
            triggers.append(EscalationType.NEGATIVE_SENTIMENT)

        # Keyword detection
        if self._contains_escalation_keywords(conversation.last_message):
            triggers.append(EscalationType.KEYWORD_MATCH)

        # Too many turns without resolution
        if len(conversation.messages) > self.config.max_conversation_turns:
            triggers.append(EscalationType.MAX_TURNS_EXCEEDED)

        return EscalationDecision(
            should_escalate=len(triggers) > 0,
            triggers=triggers,
            priority=self._calculate_priority(triggers)
        )
```

### 3.2 Slack Integration

**Location:** `apps/api/app/omnichannel/integrations/slack.py`

- [ ] Set up Slack app and bot token authentication
- [ ] Create Slack notification service
- [ ] Build escalation message formatting for Slack
- [ ] Implement Slack thread management for ongoing cases
- [ ] Add Slack slash commands for agent responses
- [ ] Create Slack workflow for case assignment

**Slack Escalation:**

````python
class SlackEscalationService:
    def __init__(self, slack_client: WebClient):
        self.client = slack_client

    async def create_escalation(
        self,
        escalation: EscalationCase,
        context: ConversationContext
    ) -> SlackEscalationResult:
        """Create Slack notification for escalation"""

        # Format escalation message
        message_blocks = self._build_escalation_blocks(escalation, context)

        # Post to designated channel
        response = await self.client.chat_postMessage(
            channel=escalation.slack_channel,
            blocks=message_blocks,
            text=f"🚨 Escalation: {escalation.summary}"
        )

        # Create thread for updates
        thread_ts = response["ts"]

        return SlackEscalationResult(
            message_ts=thread_ts,
            channel=escalation.slack_channel,
            permalink=response.get("permalink")
        )

    def _build_escalation_blocks(
        self,
        escalation: EscalationCase,
        context: ConversationContext
    ) -> list[dict]:
        """Build Slack message blocks for escalation"""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {escalation.priority.value} Priority Escalation"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Customer:* {context.customer_name}"},
                    {"type": "mrkdwn", "text": f"*Channel:* {escalation.channel.value}"},
                    {"type": "mrkdwn", "text": f"*Store:* {context.store_name}"},
                    {"type": "mrkdwn", "text": f"*Order:* {context.order_number or 'N/A'}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Issue Summary:*\n{escalation.summary}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Conversation History:*\n```{context.conversation_summary}```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Take Case"},
                        "action_id": f"take_case_{escalation.id}",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Full Context"},
                        "action_id": f"view_context_{escalation.id}",
                        "url": f"{settings.DASHBOARD_URL}/escalations/{escalation.id}"
                    }
                ]
            }
        ]
````

### 3.3 Zendesk Integration

**Location:** `apps/api/app/omnichannel/integrations/zendesk.py`

- [ ] Set up Zendesk API authentication
- [ ] Create ticket creation service
- [ ] Build ticket formatting with conversation context
- [ ] Implement ticket status synchronization
- [ ] Add custom fields for Reva-specific data
- [ ] Create ticket update webhooks

**Zendesk Ticket Creation:**

```python
class ZendeskEscalationService:
    def __init__(self, zendesk_client: ZendeskClient):
        self.client = zendesk_client

    async def create_ticket(
        self,
        escalation: EscalationCase,
        context: ConversationContext
    ) -> ZendeskTicketResult:
        """Create Zendesk ticket from escalation"""

        ticket_data = {
            "ticket": {
                "subject": f"[Reva AI] {escalation.summary}",
                "description": self._build_ticket_description(escalation, context),
                "priority": self._map_priority(escalation.priority),
                "type": "question",
                "requester": {
                    "name": context.customer_name or "Customer",
                    "email": context.customer_email
                },
                "tags": [
                    "reva-ai",
                    f"channel-{escalation.channel.value.lower()}",
                    f"store-{context.store_id}"
                ],
                "custom_fields": [
                    {"id": settings.ZENDESK_REVA_CASE_ID_FIELD, "value": str(escalation.id)},
                    {"id": settings.ZENDESK_ORIGINAL_CHANNEL_FIELD, "value": escalation.channel.value},
                    {"id": settings.ZENDESK_CUSTOMER_PROFILE_FIELD, "value": str(context.customer_profile_id)}
                ]
            }
        }

        response = await self.client.tickets.create(ticket_data)

        return ZendeskTicketResult(
            ticket_id=response["ticket"]["id"],
            ticket_url=response["ticket"]["url"],
            status=response["ticket"]["status"]
        )

    def _build_ticket_description(
        self,
        escalation: EscalationCase,
        context: ConversationContext
    ) -> str:
        """Build comprehensive ticket description"""
        return f"""
ESCALATION DETAILS:
- Escalation ID: {escalation.id}
- Priority: {escalation.priority.value}
- Channel: {escalation.channel.value}
- Triggers: {', '.join([t.value for t in escalation.triggers])}

CUSTOMER INFORMATION:
- Name: {context.customer_name or 'Unknown'}
- Email: {context.customer_email or 'Unknown'}
- Phone: {context.customer_phone or 'Unknown'}
- Order History: {len(context.order_history)} orders

CONVERSATION SUMMARY:
{context.conversation_summary}

FULL CONVERSATION HISTORY:
{self._format_conversation_history(context.recent_conversations)}

AI ANALYSIS:
- Confidence Score: {escalation.ai_confidence:.2f}
- Sentiment Score: {escalation.customer_sentiment:.2f}
- Detected Intent: {escalation.detected_intent}

This ticket was automatically created by Reva AI when the conversation required human intervention.
View full context: {settings.DASHBOARD_URL}/escalations/{escalation.id}
        """
```

### 3.4 Freshdesk Integration

**Location:** `apps/api/app/omnichannel/integrations/freshdesk.py`

- [ ] Set up Freshdesk API authentication
- [ ] Create ticket creation service similar to Zendesk
- [ ] Implement Freshdesk-specific field mapping
- [ ] Add contact creation and management
- [ ] Build ticket update synchronization
- [ ] Create Freshdesk webhook handlers

**Freshdesk Implementation:**

```python
class FreshdeskEscalationService:
    def __init__(self, freshdesk_client: FreshdeskClient):
        self.client = freshdesk_client

    async def create_ticket(
        self,
        escalation: EscalationCase,
        context: ConversationContext
    ) -> FreshdeskTicketResult:
        """Create Freshdesk ticket from escalation"""

        # Similar structure to Zendesk but with Freshdesk-specific fields
        ticket_data = {
            "subject": f"[Reva AI] {escalation.summary}",
            "description": self._build_ticket_description(escalation, context),
            "priority": self._map_priority(escalation.priority),
            "status": 2,  # Open
            "source": 7,  # API
            "email": context.customer_email,
            "name": context.customer_name or "Customer",
            "tags": [
                "reva-ai",
                f"channel-{escalation.channel.value.lower()}",
                f"store-{context.store_id}"
            ],
            "custom_fields": {
                "reva_case_id": str(escalation.id),
                "original_channel": escalation.channel.value,
                "customer_profile_id": str(context.customer_profile_id)
            }
        }

        response = await self.client.tickets.create(ticket_data)

        return FreshdeskTicketResult(
            ticket_id=response["id"],
            ticket_url=f"{settings.FRESHDESK_DOMAIN}/a/tickets/{response['id']}",
            status=response["status"]
        )
```

### 3.5 Escalation Management Service

**Location:** `apps/api/app/services/escalation_service.py`

- [ ] Create unified escalation orchestration
- [ ] Implement escalation routing based on store configuration
- [ ] Build escalation status tracking
- [ ] Add escalation analytics and reporting
- [ ] Create escalation resolution workflows
- [ ] Implement escalation feedback collection

**Escalation Orchestration:**

```python
class EscalationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.slack_service = SlackEscalationService()
        self.zendesk_service = ZendeskEscalationService()
        self.freshdesk_service = FreshdeskEscalationService()

    async def escalate_conversation(
        self,
        conversation_id: UUID,
        escalation_reason: str,
        manual: bool = False
    ) -> EscalationResult:
        """Escalate conversation to configured helpdesk"""

        # Load conversation and context
        conversation = await self._load_conversation(conversation_id)
        context = await self._build_escalation_context(conversation)

        # Create escalation case
        escalation = EscalationCase(
            id=uuid4(),
            conversation_id=conversation_id,
            store_id=conversation.store_id,
            channel=conversation.channel_type,
            summary=escalation_reason,
            priority=self._determine_priority(context),
            triggers=[EscalationType.MANUAL if manual else EscalationType.AUTO],
            created_at=datetime.utcnow()
        )

        # Route to configured helpdesk(s)
        store_config = await self._get_store_escalation_config(conversation.store_id)

        results = []

        if store_config.slack_enabled:
            slack_result = await self.slack_service.create_escalation(escalation, context)
            results.append(slack_result)

        if store_config.zendesk_enabled:
            zendesk_result = await self.zendesk_service.create_ticket(escalation, context)
            results.append(zendesk_result)

        if store_config.freshdesk_enabled:
            freshdesk_result = await self.freshdesk_service.create_ticket(escalation, context)
            results.append(freshdesk_result)

        # Save escalation record
        await self._save_escalation(escalation, results)

        return EscalationResult(
            escalation_id=escalation.id,
            integrations=results,
            status="created"
        )
```

### 3.6 Escalation Dashboard

**Location:** `apps/api/app/api/v1/escalations.py`

- [ ] Create escalation management endpoints
- [ ] Build escalation analytics API
- [ ] Implement escalation status updates
- [ ] Add escalation search and filtering
- [ ] Create escalation resolution tracking
- [ ] Build escalation performance metrics

**Escalation API:**

```python
@router.get("/escalations")
async def list_escalations(
    store_id: UUID,
    status: EscalationStatus = None,
    channel: ChannelType = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> list[EscalationResponse]:
    """List escalations with filtering"""

@router.get("/escalations/{escalation_id}")
async def get_escalation(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> EscalationDetailResponse:
    """Get detailed escalation information"""

@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: UUID,
    resolution: EscalationResolution,
    db: AsyncSession = Depends(get_db)
) -> EscalationResponse:
    """Mark escalation as resolved"""
```

### 3.7 Database Schema Updates

**Location:** `apps/api/alembic/versions/`

- [ ] Create `escalations` table
- [ ] Create `escalation_integrations` table for tracking external tickets
- [ ] Add escalation configuration to stores
- [ ] Create escalation analytics tables

**Database Schema:**

```sql
-- Escalation cases
CREATE TABLE escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    store_id UUID NOT NULL REFERENCES stores(id),
    customer_profile_id UUID REFERENCES customer_profiles(id),
    channel_type VARCHAR(20) NOT NULL,
    summary TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, URGENT
    triggers JSONB NOT NULL, -- Array of trigger types
    ai_confidence FLOAT,
    customer_sentiment FLOAT,
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, IN_PROGRESS, RESOLVED, CLOSED
    assigned_to VARCHAR(255),
    resolution_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    INDEX(store_id, status),
    INDEX(conversation_id)
);

-- External integration tracking
CREATE TABLE escalation_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escalation_id UUID NOT NULL REFERENCES escalations(id),
    integration_type VARCHAR(50) NOT NULL, -- SLACK, ZENDESK, FRESHDESK
    external_id VARCHAR(255) NOT NULL, -- Ticket ID, message TS, etc.
    external_url VARCHAR(500),
    status VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Store escalation configuration
ALTER TABLE stores ADD COLUMN escalation_config JSONB DEFAULT '{}';

-- Example escalation_config structure:
-- {
--   "slack": {"enabled": true, "channel": "#support", "webhook_url": "..."},
--   "zendesk": {"enabled": true, "domain": "company.zendesk.com", "api_token": "..."},
--   "freshdesk": {"enabled": false, "domain": "company.freshdesk.com", "api_key": "..."}
-- }
```

---

## Files to Create/Modify

| File                                        | Action | Purpose                          |
| ------------------------------------------- | ------ | -------------------------------- |
| `app/omnichannel/escalation.py`             | Create | Escalation detection and routing |
| `app/omnichannel/integrations/__init__.py`  | Create | Integrations package             |
| `app/omnichannel/integrations/slack.py`     | Create | Slack integration                |
| `app/omnichannel/integrations/zendesk.py`   | Create | Zendesk integration              |
| `app/omnichannel/integrations/freshdesk.py` | Create | Freshdesk integration            |
| `app/services/escalation_service.py`        | Create | Escalation business logic        |
| `app/schemas/escalation.py`                 | Create | Escalation Pydantic models       |
| `app/api/v1/escalations.py`                 | Create | Escalation management endpoints  |
| `app/workers/escalation_tasks.py`           | Create | Async escalation processing      |
| `app/core/config.py`                        | Modify | Add integration configurations   |

---

## Dependencies

```toml
# Add to pyproject.toml
slack-sdk = "^3.0"                # Slack API client
zenpy = "^2.0"                    # Zendesk API client
freshdesk-api = "^1.0"            # Freshdesk API client
textblob = "^0.17"                # Sentiment analysis
```

**Environment Variables:**

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret

# Zendesk
ZENDESK_DOMAIN=company.zendesk.com
ZENDESK_EMAIL=api@company.com
ZENDESK_API_TOKEN=your-api-token

# Freshdesk
FRESHDESK_DOMAIN=company.freshdesk.com
FRESHDESK_API_KEY=your-api-key
```

---

## Testing

- [ ] Unit test: Escalation trigger detection
- [ ] Unit test: Slack message formatting
- [ ] Unit test: Zendesk ticket creation
- [ ] Unit test: Freshdesk ticket creation
- [ ] Integration test: End-to-end escalation flow
- [ ] Integration test: Webhook handling for status updates
- [ ] Load test: Concurrent escalation processing

**Test Examples:**

```python
@pytest.mark.asyncio
async def test_escalation_trigger_detection():
    conversation = create_test_conversation([
        "I'm really frustrated with this order",
        "This is the third time I'm asking",
        "I want to speak to a manager"
    ])

    detector = EscalationDetector()
    decision = await detector.should_escalate(
        conversation,
        ai_confidence=0.3,
        customer_sentiment=-0.8
    )

    assert decision.should_escalate is True
    assert EscalationType.LOW_CONFIDENCE in decision.triggers
    assert EscalationType.NEGATIVE_SENTIMENT in decision.triggers
    assert EscalationType.KEYWORD_MATCH in decision.triggers

@pytest.mark.asyncio
async def test_slack_escalation_creation():
    escalation = create_test_escalation()
    context = create_test_context()

    slack_service = SlackEscalationService(mock_slack_client)
    result = await slack_service.create_escalation(escalation, context)

    assert result.message_ts is not None
    assert result.channel == "#support"
    assert "🚨" in mock_slack_client.last_message["text"]
```

---

## Acceptance Criteria

1. AI automatically detects when conversations need human intervention
2. Escalations are created in configured helpdesk systems with full context
3. Slack notifications provide immediate team awareness of urgent issues
4. Zendesk/Freshdesk tickets contain comprehensive conversation history
5. Escalation status is tracked and synchronized across systems
6. Merchants can configure which integrations to use
7. Escalation analytics provide insights into common escalation patterns
8. Human agents can easily understand the full context when taking over

---

## Notes

- Implement webhook signature validation for security
- Consider rate limiting for external API calls
- Build retry mechanisms for failed integrations
- Add escalation priority rules based on customer tier/order value
- Implement escalation SLA tracking and alerts
- Consider building custom integration framework for other helpdesks

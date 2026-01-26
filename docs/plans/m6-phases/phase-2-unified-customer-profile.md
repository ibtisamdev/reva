# Phase 2: Unified Customer Profile

> **Parent:** [M6 Omnichannel Deployment](../m6-omnichannel.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 complete

---

## Goal

Build a unified customer profile system that maintains identity and conversation history across all channels. Enable seamless context switching where customers can start on chat, continue via email, and check status on WhatsApp while the AI remembers everything.

---

## Tasks

### 2.1 Customer Profile System

**Location:** `apps/api/app/omnichannel/profiles.py`

- [ ] Create customer profile data model
- [ ] Implement cross-channel identity matching
- [ ] Build profile merging logic for duplicate detection
- [ ] Add customer preference tracking (preferred channel, timezone)
- [ ] Implement profile enrichment from order history
- [ ] Create profile analytics and insights

**Customer Profile Schema:**

```python
@dataclass
class CustomerProfile:
    id: UUID
    store_id: UUID
    primary_email: str | None
    primary_phone: str | None
    name: str | None
    identifiers: list[CustomerIdentifier]
    preferences: CustomerPreferences
    order_history: list[OrderSummary]
    conversation_summary: str | None
    created_at: datetime
    updated_at: datetime

@dataclass
class CustomerPreferences:
    preferred_channel: ChannelType | None
    timezone: str | None
    language: str = "en"
    marketing_opt_in: bool = False
    notification_preferences: dict = field(default_factory=dict)
```

### 2.2 Cross-Channel Memory System

**Location:** `apps/api/app/omnichannel/memory.py`

- [ ] Implement conversation context aggregation across channels
- [ ] Build conversation summarization for long histories
- [ ] Create context injection system for new conversations
- [ ] Add conversation threading and topic tracking
- [ ] Implement memory compression and archival
- [ ] Build context relevance scoring

**Memory Context Structure:**

```python
@dataclass
class ConversationContext:
    customer_profile_id: UUID
    recent_conversations: list[ConversationSummary]
    active_topics: list[str]
    order_context: list[OrderContext]
    previous_resolutions: list[ResolutionSummary]
    sentiment_history: list[SentimentPoint]
    last_channel: ChannelType
    context_summary: str

class MemoryService:
    async def load_context(
        self,
        customer_profile_id: UUID,
        current_channel: ChannelType
    ) -> ConversationContext:
        """Load relevant context for new conversation"""

    async def update_context(
        self,
        customer_profile_id: UUID,
        new_message: UnifiedMessage,
        ai_response: str
    ) -> None:
        """Update context with new interaction"""
```

### 2.3 Identity Resolution Engine

**Location:** `apps/api/app/omnichannel/identity.py`

- [ ] Implement fuzzy matching for email/phone variations
- [ ] Build confidence scoring for identity matches
- [ ] Create manual merge interface for ambiguous cases
- [ ] Add identity verification workflows
- [ ] Implement duplicate profile detection and cleanup
- [ ] Build identity conflict resolution

**Identity Matching Logic:**

```python
class IdentityResolver:
    async def resolve_customer(
        self,
        identifier: str,
        identifier_type: IdentifierType,
        store_id: UUID
    ) -> CustomerProfile | None:
        """Find or create customer profile"""

        # Exact match first
        profile = await self._exact_match(identifier, identifier_type, store_id)
        if profile:
            return profile

        # Fuzzy matching for variations
        candidates = await self._fuzzy_match(identifier, identifier_type, store_id)
        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            # Multiple matches - needs manual resolution
            await self._flag_for_manual_review(identifier, candidates)
            return None

        # No match - create new profile
        return await self._create_new_profile(identifier, identifier_type, store_id)
```

### 2.4 Conversation Continuity

**Location:** `apps/api/app/omnichannel/continuity.py`

- [ ] Build conversation handoff between channels
- [ ] Implement context preservation during channel switches
- [ ] Create conversation state management
- [ ] Add conversation topic persistence
- [ ] Build conversation analytics and insights
- [ ] Implement conversation archival and retrieval

**Conversation Handoff:**

```python
class ConversationContinuity:
    async def handle_channel_switch(
        self,
        customer_profile_id: UUID,
        from_channel: ChannelType,
        to_channel: ChannelType,
        new_message: UnifiedMessage
    ) -> ConversationContext:
        """Handle customer switching channels mid-conversation"""

        # Load active conversation from previous channel
        active_conv = await self._get_active_conversation(
            customer_profile_id, from_channel
        )

        # Create continuation context
        context = ConversationContext(
            customer_profile_id=customer_profile_id,
            previous_channel=from_channel,
            continuation_from=active_conv.id if active_conv else None,
            context_summary=await self._summarize_recent_context(customer_profile_id)
        )

        return context
```

### 2.5 Enhanced Chat Service Integration

**Location:** `apps/api/app/services/chat.py` (modify existing)

- [ ] Integrate customer profile loading into chat flow
- [ ] Add cross-channel context to AI prompts
- [ ] Implement conversation continuity in responses
- [ ] Add customer preference awareness
- [ ] Build personalized response generation
- [ ] Integrate order history context

**Enhanced Chat Prompt:**

```python
def build_enhanced_prompt(
    message: str,
    context: ConversationContext,
    store_context: StoreContext
) -> str:
    return f"""
You are a helpful customer support agent for {store_context.name}.

CUSTOMER CONTEXT:
- Previous conversations: {context.context_summary}
- Recent orders: {context.order_context}
- Preferred communication style: {context.customer_preferences}
- Current topic: {context.active_topics}

CONVERSATION HISTORY (across all channels):
{context.recent_conversations}

Current customer message: {message}

Respond naturally, acknowledging relevant context when appropriate.
If this continues a previous conversation, reference it naturally.
"""
```

### 2.6 Profile Analytics Dashboard

**Location:** `apps/api/app/api/v1/analytics.py`

- [ ] Create customer profile analytics endpoints
- [ ] Build channel usage analytics
- [ ] Implement conversation flow analysis
- [ ] Add customer satisfaction tracking
- [ ] Create profile completeness metrics
- [ ] Build customer journey visualization data

**Analytics Endpoints:**

```python
@router.get("/analytics/customer-profiles")
async def get_profile_analytics(
    store_id: UUID,
    timeframe: str = "30d",
    db: AsyncSession = Depends(get_db)
) -> ProfileAnalytics:
    """Get customer profile analytics"""

@router.get("/analytics/channel-usage")
async def get_channel_usage(
    store_id: UUID,
    timeframe: str = "30d",
    db: AsyncSession = Depends(get_db)
) -> ChannelUsageAnalytics:
    """Get channel usage patterns"""
```

### 2.7 Database Schema Completion

**Location:** `apps/api/alembic/versions/`

- [ ] Create `customer_profiles` table
- [ ] Create `conversation_context` table for memory storage
- [ ] Add profile relationship to conversations
- [ ] Create indexes for efficient profile queries
- [ ] Add conversation threading support

**Database Schema:**

```sql
-- Customer profiles
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id),
    primary_email VARCHAR(255),
    primary_phone VARCHAR(50),
    name VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    conversation_summary TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(store_id, primary_email) WHERE primary_email IS NOT NULL,
    UNIQUE(store_id, primary_phone) WHERE primary_phone IS NOT NULL
);

-- Link customer identifiers to profiles
ALTER TABLE customer_identifiers
ADD COLUMN customer_profile_id UUID REFERENCES customer_profiles(id);

-- Add profile reference to conversations
ALTER TABLE conversations
ADD COLUMN customer_profile_id UUID REFERENCES customer_profiles(id);

-- Conversation context storage
CREATE TABLE conversation_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_profile_id UUID NOT NULL REFERENCES customer_profiles(id),
    context_data JSONB NOT NULL,
    context_type VARCHAR(50) NOT NULL, -- SUMMARY, ACTIVE_TOPICS, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Conversation threading
ALTER TABLE conversations ADD COLUMN parent_conversation_id UUID REFERENCES conversations(id);
ALTER TABLE conversations ADD COLUMN thread_topic VARCHAR(255);

-- Indexes for performance
CREATE INDEX idx_customer_profiles_store_email ON customer_profiles(store_id, primary_email);
CREATE INDEX idx_customer_profiles_store_phone ON customer_profiles(store_id, primary_phone);
CREATE INDEX idx_conversation_contexts_profile ON conversation_contexts(customer_profile_id);
CREATE INDEX idx_conversations_profile ON conversations(customer_profile_id);
```

---

## Files to Create/Modify

| File                              | Action | Purpose                         |
| --------------------------------- | ------ | ------------------------------- |
| `app/omnichannel/profiles.py`     | Create | Customer profile management     |
| `app/omnichannel/memory.py`       | Create | Cross-channel memory system     |
| `app/omnichannel/identity.py`     | Create | Identity resolution engine      |
| `app/omnichannel/continuity.py`   | Create | Conversation continuity         |
| `app/services/profile_service.py` | Create | Profile business logic          |
| `app/services/chat.py`            | Modify | Add profile context integration |
| `app/schemas/profiles.py`         | Create | Profile Pydantic models         |
| `app/api/v1/profiles.py`          | Create | Profile management endpoints    |
| `app/api/v1/analytics.py`         | Modify | Add profile analytics           |
| `app/workers/profile_tasks.py`    | Create | Async profile processing        |

---

## Dependencies

```toml
# Add to pyproject.toml
fuzzywuzzy = "^0.18"              # Fuzzy string matching
python-levenshtein = "^0.20"      # Fast string distance
phonenumbers = "^8.13"            # Phone number normalization
email-validator = "^2.1"          # Email validation and normalization
```

---

## Testing

- [ ] Unit test: Customer profile creation and updates
- [ ] Unit test: Identity resolution with various edge cases
- [ ] Unit test: Cross-channel context loading
- [ ] Unit test: Conversation continuity across channels
- [ ] Integration test: Full customer journey across multiple channels
- [ ] Performance test: Profile lookup and context loading speed
- [ ] Load test: Concurrent profile operations

**Test Examples:**

```python
@pytest.mark.asyncio
async def test_cross_channel_continuity():
    # Customer starts on chat
    chat_msg = UnifiedMessage(
        channel=ChannelType.CHAT,
        customer_identifier="customer@example.com",
        content="I need help with my order #1234"
    )

    chat_response = await process_message(chat_msg)
    profile = await get_customer_profile("customer@example.com")

    # Customer continues on WhatsApp
    whatsapp_msg = UnifiedMessage(
        channel=ChannelType.WHATSAPP,
        customer_identifier="+1234567890",  # Same customer, different identifier
        content="Is my order ready?"
    )

    # Should recognize same customer and maintain context
    whatsapp_response = await process_message(whatsapp_msg)

    assert "order #1234" in whatsapp_response.lower()
    assert profile.id == (await get_customer_profile("+1234567890")).id

@pytest.mark.asyncio
async def test_identity_resolution_fuzzy_matching():
    # Create profile with email
    await create_customer_profile("john.doe@example.com")

    # Try to resolve with slight variation
    profile = await resolve_customer("johndoe@example.com", IdentifierType.EMAIL)

    assert profile is not None
    assert profile.primary_email == "john.doe@example.com"
```

---

## Acceptance Criteria

1. Customer profiles are automatically created and linked across channels
2. Conversation context is preserved when customers switch channels
3. AI responses acknowledge relevant previous conversations naturally
4. Identity resolution handles email/phone variations accurately
5. Profile analytics provide insights into customer behavior
6. System handles profile merging for duplicate detection
7. Performance remains fast even with large conversation histories
8. Customer preferences are respected across all channels

---

## Notes

- Implement privacy controls for data retention and deletion
- Consider GDPR compliance for customer profile data
- Build manual review interface for ambiguous identity matches
- Implement profile data export functionality
- Add customer preference management interface
- Consider implementing customer self-service profile management

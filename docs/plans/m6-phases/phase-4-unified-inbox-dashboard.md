# Phase 4: Unified Inbox Dashboard

> **Parent:** [M6 Omnichannel Deployment](../m6-omnichannel.md)  
> **Duration:** 0.5-1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1-3 complete

---

## Goal

Create a unified inbox dashboard where merchants can view, manage, and respond to conversations across all channels (chat, email, WhatsApp, SMS) from a single interface. Provide real-time updates, conversation management, and omnichannel analytics.

---

## Tasks

### 4.1 Real-time Message Streaming

**Location:** `apps/api/app/api/v1/realtime.py`

- [ ] Set up WebSocket connections for real-time updates
- [ ] Implement message broadcasting across channels
- [ ] Build connection management and authentication
- [ ] Add real-time conversation status updates
- [ ] Implement typing indicators across channels
- [ ] Create real-time escalation notifications

**WebSocket Implementation:**

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[UUID, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, store_id: UUID):
        await websocket.accept()
        if store_id not in self.active_connections:
            self.active_connections[store_id] = []
        self.active_connections[store_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, store_id: UUID):
        if store_id in self.active_connections:
            self.active_connections[store_id].remove(websocket)

    async def broadcast_to_store(self, store_id: UUID, message: dict):
        if store_id in self.active_connections:
            for connection in self.active_connections[store_id]:
                try:
                    await connection.send_json(message)
                except:
                    # Remove dead connections
                    self.active_connections[store_id].remove(connection)

@router.websocket("/ws/{store_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    store_id: UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    # Authenticate token
    store = await authenticate_websocket_token(token, store_id, db)
    if not store:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, store_id)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_json()
            await handle_websocket_message(data, store_id, db)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, store_id)
```

### 4.2 Unified Inbox API

**Location:** `apps/api/app/api/v1/inbox.py`

- [ ] Create unified conversation listing endpoint
- [ ] Implement conversation filtering and search
- [ ] Build conversation detail endpoint with full history
- [ ] Add conversation assignment and status management
- [ ] Create bulk conversation operations
- [ ] Implement conversation archiving and deletion

**Inbox API Endpoints:**

```python
@router.get("/inbox/conversations")
async def list_conversations(
    store_id: UUID,
    channel: ChannelType = None,
    status: ConversationStatus = None,
    assigned_to: str = None,
    search: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> ConversationListResponse:
    """List conversations across all channels with filtering"""

    query = select(Conversation).where(Conversation.store_id == store_id)

    if channel:
        query = query.where(Conversation.channel_type == channel)
    if status:
        query = query.where(Conversation.status == status)
    if assigned_to:
        query = query.where(Conversation.assigned_to == assigned_to)
    if search:
        query = query.where(
            or_(
                Conversation.customer_name.ilike(f"%{search}%"),
                Conversation.last_message.ilike(f"%{search}%")
            )
        )

    query = query.order_by(Conversation.updated_at.desc())
    query = query.offset(offset).limit(limit)

    conversations = await db.execute(query)
    return ConversationListResponse(
        conversations=[ConversationSummary.from_orm(c) for c in conversations.scalars()],
        total=await get_conversation_count(store_id, db),
        has_more=offset + limit < total
    )

@router.get("/inbox/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ConversationDetailResponse:
    """Get full conversation with messages and context"""

    conversation = await get_conversation_with_messages(conversation_id, db)
    customer_profile = await get_customer_profile(conversation.customer_profile_id, db)

    return ConversationDetailResponse(
        conversation=conversation,
        customer_profile=customer_profile,
        messages=conversation.messages,
        escalations=await get_conversation_escalations(conversation_id, db)
    )

@router.post("/inbox/conversations/{conversation_id}/reply")
async def send_reply(
    conversation_id: UUID,
    reply: ConversationReply,
    db: AsyncSession = Depends(get_db)
) -> MessageResponse:
    """Send reply through appropriate channel"""

    conversation = await get_conversation(conversation_id, db)

    # Format response for the conversation's channel
    formatted_response = ResponseFormatter.format_for_channel(
        reply.content,
        conversation.channel_type,
        reply.metadata
    )

    # Send through appropriate channel
    await send_channel_response(conversation, formatted_response)

    # Store message in database
    message = await create_message(
        conversation_id=conversation_id,
        content=reply.content,
        sender_type=SenderType.AGENT,
        sender_id=reply.agent_id,
        db=db
    )

    # Broadcast to real-time subscribers
    await manager.broadcast_to_store(conversation.store_id, {
        "type": "message_sent",
        "conversation_id": str(conversation_id),
        "message": MessageResponse.from_orm(message)
    })

    return MessageResponse.from_orm(message)
```

### 4.3 Conversation Management

**Location:** `apps/api/app/services/conversation_management.py`

- [ ] Implement conversation assignment system
- [ ] Build conversation status workflow
- [ ] Create conversation tagging and categorization
- [ ] Add conversation notes and internal comments
- [ ] Implement conversation merging for duplicates
- [ ] Build conversation analytics and insights

**Conversation Management:**

```python
class ConversationManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_conversation(
        self,
        conversation_id: UUID,
        agent_id: str,
        assigned_by: str
    ) -> ConversationAssignment:
        """Assign conversation to agent"""

        conversation = await self.get_conversation(conversation_id)

        assignment = ConversationAssignment(
            conversation_id=conversation_id,
            agent_id=agent_id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow()
        )

        conversation.assigned_to = agent_id
        conversation.status = ConversationStatus.ASSIGNED

        await self.db.commit()

        # Notify agent of assignment
        await self._notify_assignment(assignment)

        return assignment

    async def update_conversation_status(
        self,
        conversation_id: UUID,
        status: ConversationStatus,
        updated_by: str,
        notes: str = None
    ) -> Conversation:
        """Update conversation status with audit trail"""

        conversation = await self.get_conversation(conversation_id)
        old_status = conversation.status

        conversation.status = status
        conversation.updated_at = datetime.utcnow()

        # Create status change record
        status_change = ConversationStatusChange(
            conversation_id=conversation_id,
            old_status=old_status,
            new_status=status,
            changed_by=updated_by,
            notes=notes,
            changed_at=datetime.utcnow()
        )

        self.db.add(status_change)
        await self.db.commit()

        return conversation
```

### 4.4 Dashboard Frontend Components

**Location:** `apps/web/src/components/inbox/`

- [ ] Create unified inbox layout component
- [ ] Build conversation list with real-time updates
- [ ] Implement conversation detail view
- [ ] Create message composition interface
- [ ] Add channel-specific UI elements (emoji picker for WhatsApp, etc.)
- [ ] Build conversation search and filtering
- [ ] Implement conversation assignment interface

**Inbox Layout Component:**

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ConversationList } from './ConversationList';
import { ConversationDetail } from './ConversationDetail';
import { InboxFilters } from './InboxFilters';

interface InboxProps {
  storeId: string;
}

export function UnifiedInbox({ storeId }: InboxProps) {
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filters, setFilters] = useState<InboxFilters>({});

  const { socket, isConnected } = useWebSocket(`/ws/${storeId}`);

  useEffect(() => {
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleRealtimeUpdate(data);
      };
    }
  }, [socket]);

  const handleRealtimeUpdate = (data: RealtimeUpdate) => {
    switch (data.type) {
      case 'new_message':
        updateConversationWithMessage(data.conversation_id, data.message);
        break;
      case 'conversation_status_changed':
        updateConversationStatus(data.conversation_id, data.status);
        break;
      case 'new_conversation':
        addNewConversation(data.conversation);
        break;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar with conversation list */}
      <div className="w-1/3 bg-white border-r border-gray-200">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-semibold">Unified Inbox</h1>
          <div className="flex items-center mt-2">
            <div className={`w-2 h-2 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <InboxFilters filters={filters} onFiltersChange={setFilters} />

        <ConversationList
          conversations={conversations}
          selectedId={selectedConversation}
          onSelect={setSelectedConversation}
          filters={filters}
        />
      </div>

      {/* Main conversation view */}
      <div className="flex-1">
        {selectedConversation ? (
          <ConversationDetail
            conversationId={selectedConversation}
            onClose={() => setSelectedConversation(null)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            Select a conversation to view details
          </div>
        )}
      </div>
    </div>
  );
}
```

### 4.5 Channel-Specific UI Components

**Location:** `apps/web/src/components/inbox/channels/`

- [ ] Create email-specific composer (rich text, attachments)
- [ ] Build WhatsApp-style interface (emojis, media)
- [ ] Implement SMS character counter and formatting
- [ ] Add chat widget preview and testing
- [ ] Create channel status indicators
- [ ] Build channel-specific settings panels

**WhatsApp Message Component:**

```typescript
interface WhatsAppMessageProps {
  message: Message;
  isOwn: boolean;
}

export function WhatsAppMessage({ message, isOwn }: WhatsAppMessageProps) {
  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-2`}>
      <div
        className={`
          max-w-xs lg:max-w-md px-4 py-2 rounded-lg
          ${isOwn
            ? 'bg-green-500 text-white rounded-br-none'
            : 'bg-white border border-gray-200 rounded-bl-none'
          }
        `}
      >
        <p className="text-sm">{message.content}</p>
        <div className="flex items-center justify-end mt-1">
          <span className="text-xs opacity-70">
            {formatTime(message.created_at)}
          </span>
          {isOwn && (
            <div className="ml-1">
              {message.status === 'delivered' && <CheckIcon className="w-3 h-3" />}
              {message.status === 'read' && <DoubleCheckIcon className="w-3 h-3" />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

### 4.6 Analytics Dashboard

**Location:** `apps/web/src/components/analytics/OmnichannelAnalytics.tsx`

- [ ] Create omnichannel conversation analytics
- [ ] Build channel performance metrics
- [ ] Implement response time analytics across channels
- [ ] Add customer satisfaction tracking
- [ ] Create escalation analytics dashboard
- [ ] Build agent performance metrics

**Analytics Component:**

```typescript
export function OmnichannelAnalytics({ storeId }: { storeId: string }) {
  const { data: analytics } = useQuery({
    queryKey: ['omnichannel-analytics', storeId],
    queryFn: () => fetchOmnichannelAnalytics(storeId)
  });

  return (
    <div className="space-y-6">
      {/* Channel Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Conversations by Channel</CardTitle>
        </CardHeader>
        <CardContent>
          <ChannelDistributionChart data={analytics?.channelDistribution} />
        </CardContent>
      </Card>

      {/* Response Times */}
      <Card>
        <CardHeader>
          <CardTitle>Average Response Time by Channel</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponseTimeChart data={analytics?.responseTimes} />
        </CardContent>
      </Card>

      {/* Customer Journey */}
      <Card>
        <CardHeader>
          <CardTitle>Cross-Channel Customer Journeys</CardTitle>
        </CardHeader>
        <CardContent>
          <CustomerJourneyFlow data={analytics?.customerJourneys} />
        </CardContent>
      </Card>
    </div>
  );
}
```

### 4.7 Database Schema Completion

**Location:** `apps/api/alembic/versions/`

- [ ] Add conversation assignment tracking
- [ ] Create conversation status change audit log
- [ ] Add conversation tags and categories
- [ ] Create agent performance tracking tables
- [ ] Add conversation analytics materialized views

**Database Schema:**

```sql
-- Conversation assignments
CREATE TABLE conversation_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    agent_id VARCHAR(255) NOT NULL,
    assigned_by VARCHAR(255) NOT NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),
    unassigned_at TIMESTAMP,
    INDEX(conversation_id),
    INDEX(agent_id)
);

-- Conversation status changes audit
CREATE TABLE conversation_status_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    changed_by VARCHAR(255) NOT NULL,
    notes TEXT,
    changed_at TIMESTAMP DEFAULT NOW(),
    INDEX(conversation_id)
);

-- Conversation tags
CREATE TABLE conversation_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    tag VARCHAR(100) NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(conversation_id, tag)
);

-- Add fields to conversations table
ALTER TABLE conversations ADD COLUMN assigned_to VARCHAR(255);
ALTER TABLE conversations ADD COLUMN status VARCHAR(50) DEFAULT 'OPEN';
ALTER TABLE conversations ADD COLUMN priority VARCHAR(20) DEFAULT 'NORMAL';
ALTER TABLE conversations ADD COLUMN category VARCHAR(100);
ALTER TABLE conversations ADD COLUMN internal_notes TEXT;

-- Analytics materialized view
CREATE MATERIALIZED VIEW conversation_analytics AS
SELECT
    store_id,
    channel_type,
    DATE(created_at) as date,
    COUNT(*) as conversation_count,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))/60) as avg_resolution_time_minutes,
    COUNT(CASE WHEN status = 'ESCALATED' THEN 1 END) as escalation_count
FROM conversations
WHERE created_at >= NOW() - INTERVAL '90 days'
GROUP BY store_id, channel_type, DATE(created_at);

-- Refresh analytics daily
CREATE INDEX idx_conversation_analytics_store_date ON conversation_analytics(store_id, date);
```

---

## Files to Create/Modify

| File                                                   | Action | Purpose                       |
| ------------------------------------------------------ | ------ | ----------------------------- |
| `app/api/v1/realtime.py`                               | Create | WebSocket real-time updates   |
| `app/api/v1/inbox.py`                                  | Create | Unified inbox API endpoints   |
| `app/services/conversation_management.py`              | Create | Conversation management logic |
| `apps/web/src/components/inbox/UnifiedInbox.tsx`       | Create | Main inbox layout             |
| `apps/web/src/components/inbox/ConversationList.tsx`   | Create | Conversation list component   |
| `apps/web/src/components/inbox/ConversationDetail.tsx` | Create | Conversation detail view      |
| `apps/web/src/components/inbox/MessageComposer.tsx`    | Create | Message composition interface |
| `apps/web/src/hooks/useWebSocket.ts`                   | Create | WebSocket connection hook     |
| `apps/web/src/hooks/useInbox.ts`                       | Create | Inbox data management hook    |
| `apps/web/src/pages/inbox.tsx`                         | Create | Inbox page                    |

---

## Dependencies

```toml
# Backend - Add to pyproject.toml
websockets = "^12.0"              # WebSocket support
redis = "^5.0"                    # Real-time message queuing
```

```json
// Frontend - Add to package.json
{
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",
    "socket.io-client": "^4.7.0",
    "react-hook-form": "^7.48.0",
    "date-fns": "^3.0.0"
  }
}
```

---

## Testing

- [ ] Unit test: WebSocket connection management
- [ ] Unit test: Conversation filtering and search
- [ ] Unit test: Real-time message broadcasting
- [ ] Integration test: Full inbox workflow (view, reply, assign)
- [ ] E2E test: Cross-channel conversation management
- [ ] Performance test: Real-time updates with many concurrent users
- [ ] Accessibility test: Inbox interface compliance

**Test Examples:**

```python
@pytest.mark.asyncio
async def test_websocket_message_broadcasting():
    # Connect multiple clients
    client1 = TestWebSocketClient()
    client2 = TestWebSocketClient()

    await client1.connect("/ws/store-123")
    await client2.connect("/ws/store-123")

    # Send message through API
    response = await api_client.post("/inbox/conversations/conv-123/reply", {
        "content": "Test message",
        "agent_id": "agent-1"
    })

    # Both clients should receive real-time update
    message1 = await client1.receive_json()
    message2 = await client2.receive_json()

    assert message1["type"] == "message_sent"
    assert message2["type"] == "message_sent"
    assert message1["message"]["content"] == "Test message"

@pytest.mark.asyncio
async def test_conversation_assignment():
    conversation_id = create_test_conversation()

    # Assign conversation
    response = await api_client.post(f"/inbox/conversations/{conversation_id}/assign", {
        "agent_id": "agent-1",
        "assigned_by": "manager-1"
    })

    assert response.status_code == 200

    # Verify assignment in database
    conversation = await get_conversation(conversation_id)
    assert conversation.assigned_to == "agent-1"
    assert conversation.status == "ASSIGNED"
```

---

## Acceptance Criteria

1. Merchants can view conversations from all channels in a single interface
2. Real-time updates work seamlessly across all connected clients
3. Conversation assignment and status management works correctly
4. Channel-specific UI elements enhance the user experience
5. Search and filtering help merchants find conversations quickly
6. Analytics provide insights into omnichannel performance
7. Interface is responsive and works well on different screen sizes
8. WebSocket connections are stable and handle reconnection gracefully

---

## Notes

- Implement proper WebSocket authentication and authorization
- Consider implementing conversation threading for complex issues
- Add keyboard shortcuts for power users
- Implement conversation templates for common responses
- Consider adding voice message support for WhatsApp
- Build mobile-responsive design for on-the-go management
- Add conversation export functionality for compliance

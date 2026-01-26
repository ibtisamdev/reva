# Phase 3: Confirmation Flow & Checkpointing

> **Parent:** [M5 Full Action Agent](../m5-action-agent.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 & 2 complete, LangGraph setup

---

## Goal

Implement the human-in-the-loop confirmation flow using LangGraph's checkpointing system. This allows the agent to pause execution, request customer confirmation, and resume from the exact same state.

---

## Tasks

### 3.1 LangGraph Agent Setup

**Location:** `apps/api/app/agents/action_agent.py`

- [ ] Create LangGraph state schema for action flow
- [ ] Implement action classification node
- [ ] Implement permission checking node
- [ ] Implement confirmation request node
- [ ] Implement action execution node
- [ ] Configure checkpointing with PostgreSQL

```python
from typing import Dict, Any, List, Optional, Annotated
from uuid import UUID
import json
from datetime import datetime

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel

from app.agents.tools.registry import ActionToolRegistry
from app.services.permissions import PermissionService
from app.services.audit import AuditService
from app.core.database import get_db_url

class ActionAgentState(BaseModel):
    """State for the action agent."""
    messages: Annotated[List[BaseMessage], add_messages]
    store_id: UUID
    conversation_id: UUID

    # Action flow state
    intent: Optional[str] = None
    action_type: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None
    permission_check: Optional[Dict[str, Any]] = None
    confirmation_required: bool = False
    customer_confirmed: Optional[bool] = None
    action_result: Optional[Dict[str, Any]] = None

    # Metadata
    current_step: str = "classify"
    error: Optional[str] = None

class ActionAgent:
    """LangGraph-based action agent with checkpointing."""

    def __init__(
        self,
        tool_registry: ActionToolRegistry,
        permission_service: PermissionService,
        audit_service: AuditService
    ):
        self.tool_registry = tool_registry
        self.permission_service = permission_service
        self.audit_service = audit_service

        # Setup checkpointing
        self.checkpointer = PostgresSaver.from_conn_string(get_db_url())

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the action agent graph."""
        workflow = StateGraph(ActionAgentState)

        # Add nodes
        workflow.add_node("classify", self._classify_intent)
        workflow.add_node("check_permission", self._check_permission)
        workflow.add_node("request_confirmation", self._request_confirmation)
        workflow.add_node("wait_confirmation", self._wait_confirmation)
        workflow.add_node("execute_action", self._execute_action)
        workflow.add_node("explain_denial", self._explain_denial)

        # Add edges
        workflow.add_edge(START, "classify")
        workflow.add_conditional_edges(
            "classify",
            self._route_after_classification,
            {
                "check_permission": "check_permission",
                "no_action": END
            }
        )
        workflow.add_conditional_edges(
            "check_permission",
            self._route_after_permission,
            {
                "execute": "execute_action",
                "confirm": "request_confirmation",
                "deny": "explain_denial"
            }
        )
        workflow.add_edge("request_confirmation", "wait_confirmation")
        workflow.add_conditional_edges(
            "wait_confirmation",
            self._route_after_confirmation,
            {
                "execute": "execute_action",
                "cancelled": END
            }
        )
        workflow.add_edge("execute_action", END)
        workflow.add_edge("explain_denial", END)

        return workflow.compile(checkpointer=self.checkpointer)

    async def _classify_intent(self, state: ActionAgentState) -> ActionAgentState:
        """Classify the customer's intent and extract action data."""
        last_message = state.messages[-1].content

        # Use LLM to classify intent and extract structured data
        classification_result = await self._llm_classify_intent(last_message)

        state.intent = classification_result.get("intent")
        state.action_type = classification_result.get("action_type")
        state.action_data = classification_result.get("action_data", {})
        state.current_step = "classify"

        return state

    async def _check_permission(self, state: ActionAgentState) -> ActionAgentState:
        """Check if the action is permitted."""
        if not state.action_type:
            state.error = "No action type identified"
            return state

        is_allowed, requires_confirmation, denial_reason = await self.permission_service.check_action_permission(
            store_id=state.store_id,
            action_type=state.action_type,
            action_data=state.action_data
        )

        state.permission_check = {
            "allowed": is_allowed,
            "requires_confirmation": requires_confirmation,
            "denial_reason": denial_reason
        }
        state.confirmation_required = requires_confirmation
        state.current_step = "check_permission"

        return state

    async def _request_confirmation(self, state: ActionAgentState) -> ActionAgentState:
        """Request confirmation from the customer."""
        tool = self.tool_registry.get_tool(state.action_type)
        confirmation_message = await tool._generate_confirmation_message(state.action_data)

        # Add confirmation request to messages
        confirmation_msg = AIMessage(content=confirmation_message)
        state.messages.append(confirmation_msg)
        state.current_step = "wait_confirmation"

        return state

    async def _wait_confirmation(self, state: ActionAgentState) -> ActionAgentState:
        """Wait for customer confirmation (checkpoint here)."""
        # This node represents the checkpoint where we wait for user input
        # The actual confirmation will come from a separate API call
        state.current_step = "wait_confirmation"
        return state

    async def _execute_action(self, state: ActionAgentState) -> ActionAgentState:
        """Execute the confirmed action."""
        try:
            tool = self.tool_registry.get_tool(state.action_type)
            result = await tool._execute_action(state.store_id, state.action_data)

            state.action_result = result
            state.current_step = "completed"

            # Add success message
            success_msg = self._generate_success_message(state.action_type, result)
            state.messages.append(AIMessage(content=success_msg))

        except Exception as e:
            state.error = str(e)
            error_msg = f"I encountered an error while processing your request: {str(e)}"
            state.messages.append(AIMessage(content=error_msg))

        return state

    async def _explain_denial(self, state: ActionAgentState) -> ActionAgentState:
        """Explain why the action was denied."""
        denial_reason = state.permission_check.get("denial_reason", "Action not permitted")

        explanation = f"I'm sorry, but I can't perform this action. {denial_reason}"
        state.messages.append(AIMessage(content=explanation))
        state.current_step = "denied"

        return state

    def _route_after_classification(self, state: ActionAgentState) -> str:
        """Route after intent classification."""
        if state.action_type:
            return "check_permission"
        return "no_action"

    def _route_after_permission(self, state: ActionAgentState) -> str:
        """Route after permission check."""
        if not state.permission_check["allowed"]:
            return "deny"
        elif state.permission_check["requires_confirmation"]:
            return "confirm"
        else:
            return "execute"

    def _route_after_confirmation(self, state: ActionAgentState) -> str:
        """Route after confirmation check."""
        if state.customer_confirmed:
            return "execute"
        return "cancelled"
```

### 3.2 Intent Classification Service

**Location:** `apps/api/app/services/intent_classification.py`

- [ ] Use LLM to classify customer intents
- [ ] Extract structured action data from natural language
- [ ] Support multiple action types in single message
- [ ] Handle ambiguous requests

```python
from typing import Dict, Any, Optional, List
import json
from openai import AsyncOpenAI

from app.core.config import settings

class IntentClassificationService:
    """Service for classifying customer intents and extracting action data."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def classify_intent(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify customer intent and extract structured action data.

        Returns:
            {
                "intent": "action_request" | "question" | "complaint",
                "action_type": "cancel_order" | "process_refund" | etc.,
                "action_data": {...},
                "confidence": 0.0-1.0
            }
        """
        system_prompt = """
        You are an expert at understanding customer service requests. Analyze the customer's message and determine:
        1. Their intent (action_request, question, complaint, other)
        2. If it's an action request, what specific action they want
        3. Extract any relevant data (order numbers, amounts, reasons, etc.)

        Available actions:
        - cancel_order: Customer wants to cancel an order
        - process_refund: Customer wants a refund
        - initiate_return: Customer wants to return items
        - apply_discount: Customer requests a discount
        - update_address: Customer wants to change shipping address
        - lookup_order: Customer wants order status
        - send_tracking: Customer wants tracking information

        Respond with JSON only:
        {
            "intent": "action_request|question|complaint|other",
            "action_type": "action_name|null",
            "action_data": {
                "order_id": "extracted_order_number",
                "amount": "extracted_amount",
                "reason": "extracted_reason",
                "items": ["extracted_items"]
            },
            "confidence": 0.95
        }
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]

        if context:
            # Add context about current conversation or order
            context_msg = f"Context: {json.dumps(context)}"
            messages.insert(-1, {"role": "system", "content": context_msg})

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        try:
            result = json.loads(response.choices[0].message.content)
            return result
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "intent": "other",
                "action_type": None,
                "action_data": {},
                "confidence": 0.0
            }

    async def extract_order_info(self, message: str) -> Optional[str]:
        """Extract order number from message."""
        # Simple regex patterns for common order number formats
        import re

        patterns = [
            r'#(\d+)',  # #1234
            r'order\s+(\d+)',  # order 1234
            r'order\s+#(\d+)',  # order #1234
            r'(\d{4,})',  # 4+ digit number
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        return None
```

### 3.3 Confirmation API Endpoints

**Location:** `apps/api/app/api/v1/confirmations.py`

- [ ] `POST /api/v1/confirmations/{conversation_id}/confirm` - Confirm action
- [ ] `POST /api/v1/confirmations/{conversation_id}/cancel` - Cancel action
- [ ] `GET /api/v1/confirmations/{conversation_id}/status` - Check status

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Dict, Any

from app.core.deps import get_db
from app.agents.action_agent import ActionAgent
from app.services.conversation import ConversationService

router = APIRouter(prefix="/confirmations", tags=["confirmations"])

@router.post("/{conversation_id}/confirm")
async def confirm_action(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Confirm a pending action."""
    try:
        # Get the conversation and its current state
        conversation_service = ConversationService(db)
        conversation = await conversation_service.get_conversation(conversation_id)

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Resume the agent from checkpoint with confirmation
        agent = ActionAgent(...)  # Initialize with dependencies

        # Update state with confirmation
        config = {"configurable": {"thread_id": str(conversation_id)}}
        current_state = await agent.graph.aget_state(config)

        if current_state.values.get("current_step") != "wait_confirmation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending confirmation for this conversation"
            )

        # Update state with confirmation and resume
        await agent.graph.aupdate_state(
            config,
            {"customer_confirmed": True}
        )

        # Continue execution
        result = await agent.graph.ainvoke(None, config)

        return {
            "status": "confirmed",
            "action_executed": True,
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/{conversation_id}/cancel")
async def cancel_action(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Cancel a pending action."""
    try:
        agent = ActionAgent(...)  # Initialize with dependencies

        config = {"configurable": {"thread_id": str(conversation_id)}}
        current_state = await agent.graph.aget_state(config)

        if current_state.values.get("current_step") != "wait_confirmation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending confirmation for this conversation"
            )

        # Update state with cancellation
        await agent.graph.aupdate_state(
            config,
            {"customer_confirmed": False}
        )

        # Continue execution (will route to cancelled)
        result = await agent.graph.ainvoke(None, config)

        return {
            "status": "cancelled",
            "action_executed": False
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{conversation_id}/status")
async def get_confirmation_status(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get the current confirmation status."""
    try:
        agent = ActionAgent(...)  # Initialize with dependencies

        config = {"configurable": {"thread_id": str(conversation_id)}}
        current_state = await agent.graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active conversation state"
            )

        state_values = current_state.values

        return {
            "conversation_id": conversation_id,
            "current_step": state_values.get("current_step"),
            "confirmation_required": state_values.get("confirmation_required", False),
            "action_type": state_values.get("action_type"),
            "action_data": state_values.get("action_data"),
            "pending_confirmation": state_values.get("current_step") == "wait_confirmation"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

### 3.4 Widget Confirmation UI

**Location:** `apps/widget/src/components/ConfirmationDialog.tsx`

- [ ] Create confirmation dialog component
- [ ] Show action details clearly
- [ ] Provide confirm/cancel buttons
- [ ] Handle confirmation API calls

```typescript
import { useState } from 'preact/hooks';
import { Button } from './ui/Button';
import { Card } from './ui/Card';

interface ConfirmationDialogProps {
  conversationId: string;
  actionType: string;
  actionData: any;
  confirmationMessage: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function ConfirmationDialog({
  conversationId,
  actionType,
  actionData,
  confirmationMessage,
  onConfirm,
  onCancel,
  loading = false
}: ConfirmationDialogProps) {
  const [confirming, setConfirming] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      const response = await fetch(`/api/v1/confirmations/${conversationId}/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        onConfirm();
      } else {
        console.error('Failed to confirm action');
      }
    } catch (error) {
      console.error('Error confirming action:', error);
    } finally {
      setConfirming(false);
    }
  };

  const handleCancel = async () => {
    setCancelling(true);
    try {
      const response = await fetch(`/api/v1/confirmations/${conversationId}/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        onCancel();
      } else {
        console.error('Failed to cancel action');
      }
    } catch (error) {
      console.error('Error cancelling action:', error);
    } finally {
      setCancelling(false);
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case 'cancel_order':
        return '❌';
      case 'process_refund':
        return '💰';
      case 'initiate_return':
        return '📦';
      case 'apply_discount':
        return '🏷️';
      default:
        return '⚡';
    }
  };

  const getActionTitle = (actionType: string) => {
    switch (actionType) {
      case 'cancel_order':
        return 'Cancel Order';
      case 'process_refund':
        return 'Process Refund';
      case 'initiate_return':
        return 'Initiate Return';
      case 'apply_discount':
        return 'Apply Discount';
      default:
        return 'Confirm Action';
    }
  };

  return (
    <Card className="p-4 border-orange-200 bg-orange-50">
      <div className="flex items-start space-x-3">
        <div className="text-2xl">{getActionIcon(actionType)}</div>
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 mb-2">
            {getActionTitle(actionType)}
          </h3>
          <p className="text-gray-700 mb-4">
            {confirmationMessage}
          </p>

          {/* Action Details */}
          <div className="bg-white p-3 rounded border mb-4">
            <h4 className="font-medium text-sm text-gray-600 mb-2">Action Details:</h4>
            <div className="space-y-1 text-sm">
              {actionData.order_id && (
                <div>Order: #{actionData.order_id}</div>
              )}
              {actionData.amount && (
                <div>Amount: ${actionData.amount}</div>
              )}
              {actionData.reason && (
                <div>Reason: {actionData.reason}</div>
              )}
            </div>
          </div>

          <div className="flex space-x-3">
            <Button
              onClick={handleConfirm}
              disabled={confirming || cancelling || loading}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {confirming ? 'Confirming...' : 'Yes, Proceed'}
            </Button>
            <Button
              onClick={handleCancel}
              disabled={confirming || cancelling || loading}
              variant="outline"
            >
              {cancelling ? 'Cancelling...' : 'No, Cancel'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
```

### 3.5 Chat Integration

**Location:** `apps/api/app/api/v1/chat.py`

- [ ] Modify chat endpoint to handle action agent
- [ ] Integrate with LangGraph checkpointing
- [ ] Return confirmation dialogs when needed
- [ ] Handle state persistence

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Dict, Any

from app.core.deps import get_db, get_current_store
from app.agents.action_agent import ActionAgent
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/messages", response_model=ChatMessageResponse)
async def send_message(
    message_request: ChatMessageRequest,
    store = Depends(get_current_store),
    db: AsyncSession = Depends(get_db)
):
    """Send a message and get AI response, potentially with action confirmation."""
    try:
        # Initialize action agent
        agent = ActionAgent(...)  # Initialize with dependencies

        # Prepare conversation config
        conversation_id = message_request.conversation_id or UUID()
        config = {"configurable": {"thread_id": str(conversation_id)}}

        # Create initial state
        initial_state = {
            "messages": [HumanMessage(content=message_request.message)],
            "store_id": store.id,
            "conversation_id": conversation_id
        }

        # Run the agent
        result = await agent.graph.ainvoke(initial_state, config)

        # Check if confirmation is needed
        if result.get("current_step") == "wait_confirmation":
            return ChatMessageResponse(
                conversation_id=conversation_id,
                message_id=UUID(),
                response=result["messages"][-1].content,
                requires_confirmation=True,
                confirmation_data={
                    "action_type": result["action_type"],
                    "action_data": result["action_data"],
                    "confirmation_message": result["messages"][-1].content
                },
                created_at=datetime.utcnow()
            )
        else:
            # Regular response
            return ChatMessageResponse(
                conversation_id=conversation_id,
                message_id=UUID(),
                response=result["messages"][-1].content,
                requires_confirmation=False,
                created_at=datetime.utcnow()
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )
```

---

## Files to Create/Modify

| File                                                | Action | Purpose                       |
| --------------------------------------------------- | ------ | ----------------------------- |
| `app/agents/action_agent.py`                        | Create | Main LangGraph action agent   |
| `app/services/intent_classification.py`             | Create | Intent classification service |
| `app/api/v1/confirmations.py`                       | Create | Confirmation API endpoints    |
| `app/schemas/chat.py`                               | Modify | Add confirmation fields       |
| `apps/widget/src/components/ConfirmationDialog.tsx` | Create | Confirmation UI component     |
| `app/api/v1/chat.py`                                | Modify | Integrate action agent        |

---

## Dependencies

```toml
# Add to pyproject.toml
langgraph = "^0.0.60"
langgraph-checkpoint-postgres = "^1.0.0"
```

---

## Testing

- [ ] Unit test: intent classification accuracy
- [ ] Unit test: LangGraph state transitions
- [ ] Unit test: checkpointing and resume functionality
- [ ] Integration test: full confirmation flow
- [ ] E2E test: widget confirmation dialog
- [ ] Test: concurrent conversations with checkpointing

---

## Acceptance Criteria

1. Agent can pause execution and wait for customer confirmation
2. Conversation state is preserved across requests
3. Customer can confirm or cancel pending actions
4. Widget displays clear confirmation dialogs
5. Intent classification accurately identifies action requests
6. Multiple conversations can run concurrently
7. Checkpointing works reliably with PostgreSQL

---

## Notes

- Test checkpointing thoroughly with database failures
- Consider timeout handling for pending confirmations
- Implement conversation cleanup for old checkpoints
- Plan for conversation handoff to human agents

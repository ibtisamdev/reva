# Phase 3: LangGraph Router & State Machine

> **Parent:** [M3 Sales & Recommendation Agent](../m3-sales-agent.md)  
> **Duration:** 1 week  
> **Status:** Not Started  
> **Dependencies:** Phase 1 (Product Search), Phase 2 (Recommendations)

---

## Goal

Implement a sophisticated conversation routing system using LangGraph that can classify customer intent, maintain conversation state, and route to appropriate specialized handlers for sales, support, and product discovery.

---

## Tasks

### 3.1 LangGraph State Schema

**Location:** `apps/api/app/services/langgraph_state.py`

- [ ] Define conversation state schema for LangGraph
- [ ] Include customer context, conversation history, and intent
- [ ] Track product search context and recommendations
- [ ] Maintain shopping cart state and preferences
- [ ] Handle multi-turn conversation flows

**State Schema:**

```python
from typing import TypedDict, Annotated, Sequence
from langgraph.graph.message import add_messages

class ConversationState(TypedDict):
    # Core conversation data
    messages: Annotated[Sequence[BaseMessage], add_messages]
    conversation_id: str
    store_id: str

    # Customer context
    customer_id: str | None
    customer_preferences: dict | None
    session_data: dict

    # Intent and routing
    current_intent: str | None
    confidence_score: float | None
    routing_history: list[str]

    # Product context
    current_products: list[dict] | None
    search_query: str | None
    search_results: list[dict] | None
    recommendations: list[dict] | None

    # Shopping context
    cart_items: list[dict] | None
    price_range: dict | None
    size_preferences: dict | None

    # Conversation flow
    needs_clarification: bool
    clarification_question: str | None
    next_action: str | None

    # Analytics
    interaction_count: int
    start_time: str
    last_activity: str
```

### 3.2 Intent Classification Node

**Location:** `apps/api/app/services/intent_classifier.py`

- [ ] Implement LLM-based intent classification
- [ ] Define intent categories and confidence thresholds
- [ ] Handle multi-intent messages
- [ ] Extract entities from customer messages
- [ ] Update conversation state with classified intent

**Intent Categories:**

```python
class CustomerIntent(str, Enum):
    # Product discovery
    PRODUCT_SEARCH = "product_search"
    BROWSE_CATEGORY = "browse_category"
    GIFT_SEARCH = "gift_search"
    PRICE_INQUIRY = "price_inquiry"

    # Product information
    PRODUCT_DETAILS = "product_details"
    SIZE_GUIDANCE = "size_guidance"
    AVAILABILITY_CHECK = "availability_check"
    COMPARISON_REQUEST = "comparison_request"

    # Purchase assistance
    ADD_TO_CART = "add_to_cart"
    CHECKOUT_HELP = "checkout_help"
    PAYMENT_QUESTION = "payment_question"

    # Support requests
    ORDER_STATUS = "order_status"
    RETURN_POLICY = "return_policy"
    SHIPPING_INFO = "shipping_info"
    GENERAL_SUPPORT = "general_support"

    # Conversation management
    GREETING = "greeting"
    SMALL_TALK = "small_talk"
    GOODBYE = "goodbye"
    UNCLEAR = "unclear"

async def classify_intent(state: ConversationState) -> ConversationState:
    """
    Classify customer intent from the latest message.

    Updates state with:
    - current_intent
    - confidence_score
    - extracted entities
    """
```

### 3.3 Conversation Router Node

**Location:** `apps/api/app/services/conversation_router.py`

- [ ] Route conversations based on classified intent
- [ ] Handle conditional routing with confidence thresholds
- [ ] Implement fallback routing for unclear intents
- [ ] Support multi-step conversation flows
- [ ] Track routing decisions for analytics

**Router Implementation:**

```python
def route_conversation(state: ConversationState) -> str:
    """
    Route conversation to appropriate handler based on intent.

    Returns:
        Next node name to execute
    """
    intent = state.get("current_intent")
    confidence = state.get("confidence_score", 0.0)

    # High confidence routing
    if confidence > 0.8:
        return INTENT_ROUTING_MAP[intent]

    # Medium confidence - ask for clarification
    elif confidence > 0.5:
        return "clarification_node"

    # Low confidence - fallback to general support
    else:
        return "general_support_node"

INTENT_ROUTING_MAP = {
    CustomerIntent.PRODUCT_SEARCH: "product_search_node",
    CustomerIntent.PRODUCT_DETAILS: "product_details_node",
    CustomerIntent.SIZE_GUIDANCE: "size_guidance_node",
    CustomerIntent.ORDER_STATUS: "order_status_node",
    CustomerIntent.GENERAL_SUPPORT: "general_support_node",
    # ... more mappings
}
```

### 3.4 Product Search Node

**Location:** `apps/api/app/services/nodes/product_search_node.py`

- [ ] Execute product search using Phase 1 search engine
- [ ] Update state with search results
- [ ] Generate conversational response with product recommendations
- [ ] Handle zero-result searches with suggestions
- [ ] Prepare for follow-up questions

**Search Node:**

```python
async def product_search_node(state: ConversationState) -> ConversationState:
    """
    Execute product search and update conversation state.

    Process:
    1. Extract search query from message
    2. Call product search service
    3. Generate conversational response
    4. Update state with results
    5. Suggest next actions
    """

    # Extract search parameters
    query = extract_search_query(state["messages"][-1])
    filters = extract_search_filters(state)

    # Execute search
    search_results = await search_products(
        query=query,
        store_id=state["store_id"],
        filters=filters
    )

    # Generate response
    response = await generate_search_response(search_results, query)

    # Update state
    state["search_query"] = query
    state["search_results"] = [r.model_dump() for r in search_results]
    state["current_products"] = search_results[:3]  # Top 3 for context
    state["next_action"] = "await_product_selection"

    return state
```

### 3.5 Recommendation Node

**Location:** `apps/api/app/services/nodes/recommendation_node.py`

- [ ] Generate product recommendations using Phase 2 engine
- [ ] Handle different recommendation types (similar, upsell, cross-sell)
- [ ] Update conversation state with recommendations
- [ ] Format recommendations in conversational style
- [ ] Track recommendation context for follow-ups

**Recommendation Node:**

```python
async def recommendation_node(state: ConversationState) -> ConversationState:
    """
    Generate and present product recommendations.

    Handles:
    - Similar product recommendations
    - Upsell suggestions
    - Cross-sell opportunities
    - Bundle recommendations
    """

    # Determine recommendation type
    rec_type = determine_recommendation_type(state)

    # Generate recommendations
    recommendations = await generate_recommendations(
        recommendation_type=rec_type,
        context_products=state.get("current_products", []),
        customer_preferences=state.get("customer_preferences"),
        store_id=state["store_id"]
    )

    # Generate conversational response
    response = await format_recommendations_response(
        recommendations, rec_type
    )

    # Update state
    state["recommendations"] = [r.model_dump() for r in recommendations]
    state["next_action"] = "await_recommendation_feedback"

    return state
```

### 3.6 Support Nodes

**Location:** `apps/api/app/services/nodes/support_nodes.py`

- [ ] Order status lookup node
- [ ] General FAQ answering node
- [ ] Policy information node (shipping, returns)
- [ ] Escalation to human agent node
- [ ] Small talk and greeting nodes

**Support Node Example:**

```python
async def order_status_node(state: ConversationState) -> ConversationState:
    """Handle order status inquiries."""

    # Extract order identifier
    order_id = extract_order_id(state["messages"][-1])

    if order_id:
        # Look up order status
        order_info = await get_order_status(order_id, state["store_id"])
        response = format_order_status_response(order_info)
    else:
        # Ask for order number
        response = "I'd be happy to help you check your order status. Could you please provide your order number?"
        state["needs_clarification"] = True
        state["clarification_question"] = "order_number"

    return state
```

### 3.7 LangGraph Workflow Definition

**Location:** `apps/api/app/services/langgraph_workflow.py`

- [ ] Define the complete conversation graph
- [ ] Set up nodes and conditional edges
- [ ] Implement conversation flow logic
- [ ] Add error handling and fallback paths
- [ ] Configure graph compilation and execution

**Graph Definition:**

```python
from langgraph.graph import StateGraph, END

def create_sales_agent_graph() -> StateGraph:
    """Create the sales agent conversation graph."""

    # Initialize graph
    workflow = StateGraph(ConversationState)

    # Add nodes
    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("product_search_node", product_search_node)
    workflow.add_node("recommendation_node", recommendation_node)
    workflow.add_node("order_status_node", order_status_node)
    workflow.add_node("general_support_node", general_support_node)
    workflow.add_node("clarification_node", clarification_node)

    # Set entry point
    workflow.set_entry_point("classify_intent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "classify_intent",
        route_conversation,
        {
            "product_search_node": "product_search_node",
            "recommendation_node": "recommendation_node",
            "order_status_node": "order_status_node",
            "general_support_node": "general_support_node",
            "clarification_node": "clarification_node"
        }
    )

    # Add edges to END
    workflow.add_edge("product_search_node", END)
    workflow.add_edge("recommendation_node", END)
    workflow.add_edge("order_status_node", END)
    workflow.add_edge("general_support_node", END)
    workflow.add_edge("clarification_node", END)

    return workflow.compile()
```

### 3.8 Chat Service Integration

**Location:** `apps/api/app/services/chat.py` (modify existing)

- [ ] Replace existing chat logic with LangGraph workflow
- [ ] Maintain conversation state across messages
- [ ] Handle streaming responses from LangGraph
- [ ] Implement conversation persistence
- [ ] Add error handling and fallbacks

**Updated Chat Service:**

```python
class ChatService:
    def __init__(self):
        self.graph = create_sales_agent_graph()

    async def process_message(
        self,
        message: str,
        conversation_id: str | None,
        store_id: str,
        context: dict | None = None
    ) -> ChatResponse:
        """Process message through LangGraph workflow."""

        # Load or create conversation state
        state = await self.load_conversation_state(conversation_id, store_id)

        # Add new message to state
        state["messages"].append(HumanMessage(content=message))

        # Execute graph
        result = await self.graph.ainvoke(state)

        # Extract response and update state
        response_message = result["messages"][-1].content

        # Save conversation state
        await self.save_conversation_state(result)

        return ChatResponse(
            conversation_id=result["conversation_id"],
            response=response_message,
            intent=result.get("current_intent"),
            next_action=result.get("next_action"),
            products=result.get("current_products"),
            recommendations=result.get("recommendations")
        )
```

### 3.9 Analytics & Monitoring

**Location:** `apps/api/app/services/langgraph_analytics.py`

- [ ] Track conversation flow through graph nodes
- [ ] Monitor intent classification accuracy
- [ ] Measure conversation completion rates
- [ ] Identify common routing patterns
- [ ] Generate insights for graph optimization

**Analytics Schema:**

```sql
CREATE TABLE conversation_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    store_id UUID NOT NULL,
    node_name VARCHAR(100) NOT NULL,
    intent VARCHAR(100),
    confidence_score FLOAT,
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Files to Create/Modify

| File                                        | Action | Purpose                      |
| ------------------------------------------- | ------ | ---------------------------- |
| `app/services/langgraph_state.py`           | Create | LangGraph state schema       |
| `app/services/intent_classifier.py`         | Create | Intent classification logic  |
| `app/services/conversation_router.py`       | Create | Conversation routing logic   |
| `app/services/nodes/product_search_node.py` | Create | Product search graph node    |
| `app/services/nodes/recommendation_node.py` | Create | Recommendation graph node    |
| `app/services/nodes/support_nodes.py`       | Create | Support-related graph nodes  |
| `app/services/langgraph_workflow.py`        | Create | Complete graph definition    |
| `app/services/langgraph_analytics.py`       | Create | Graph execution analytics    |
| `app/services/chat.py`                      | Modify | Integrate LangGraph workflow |
| `app/schemas/langgraph.py`                  | Create | LangGraph-related schemas    |
| `app/models/conversation_analytics.py`      | Create | Analytics database model     |
| `migrations/add_conversation_analytics.py`  | Create | Database migration           |

---

## Dependencies

```toml
# Add to pyproject.toml
langgraph = "^0.0.40"     # LangGraph state machine framework
langchain = "^0.1.0"      # LangChain core (required by LangGraph)
langchain-openai = "^0.1.0"  # OpenAI integration
```

---

## Testing

- [ ] Unit test: intent classification accuracy across different message types
- [ ] Unit test: conversation routing logic with various confidence scores
- [ ] Unit test: state updates in each graph node
- [ ] Integration test: complete conversation flows through graph
- [ ] Integration test: conversation state persistence
- [ ] Performance test: graph execution time under load
- [ ] A/B test: different intent classification prompts
- [ ] User test: conversation flow feels natural and helpful

---

## Acceptance Criteria

1. **Intent Classification**: Accurately classifies customer intents with >85% accuracy
2. **Conversation Routing**: Routes conversations to appropriate handlers based on intent
3. **State Management**: Maintains conversation context across multiple turns
4. **Flow Control**: Handles multi-step conversations smoothly
5. **Error Handling**: Gracefully handles unclear intents and errors
6. **Performance**: Graph execution completes within 3 seconds
7. **Analytics**: Tracks conversation flows and performance metrics
8. **Scalability**: Handles multiple concurrent conversations

---

## Example Conversation Flows

**Product Discovery Flow:**

```
Customer: "I'm looking for a gift for my mom"
→ classify_intent → GIFT_SEARCH
→ product_search_node → "What does your mom enjoy? Here are some popular gift categories..."

Customer: "She likes gardening"
→ classify_intent → PRODUCT_SEARCH
→ product_search_node → Shows gardening products
→ recommendation_node → Suggests complementary items
```

**Size Guidance Flow:**

```
Customer: "Will this jacket fit me? I'm 6'2""
→ classify_intent → SIZE_GUIDANCE
→ size_guidance_node → Analyzes size chart and reviews
→ "Based on your height, I'd recommend XL..."
```

**Order Status Flow:**

```
Customer: "Where is my order?"
→ classify_intent → ORDER_STATUS
→ order_status_node → "I can help you track your order. What's your order number?"

Customer: "ORDER123"
→ order_status_node → Looks up order → "Your order shipped yesterday..."
```

---

## LangGraph Visualization

The implemented graph will match the architecture diagram from the milestone overview:

```
┌────────────────────────────────────────────────────────────┐
│                   SALES AGENT GRAPH                        │
│                                                            │
│  ┌─────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │  START  │────▶│   CLASSIFY   │────▶│    ROUTE     │    │
│  └─────────┘     │    INTENT    │     └──────┬───────┘    │
│                  └──────────────┘            │             │
│            ┌─────────────┬─────────────┬─────┴────┐       │
│            ▼             ▼             ▼          ▼       │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌────────┐  │
│     │ PRODUCT  │  │  ORDER   │  │   FAQ    │ │ SMALL  │  │
│     │  SEARCH  │  │  STATUS  │  │  ANSWER  │ │  TALK  │  │
│     └────┬─────┘  └──────────┘  └──────────┘ └────────┘  │
│          ▼                                                │
│     ┌──────────┐                                          │
│     │  FILTER  │                                          │
│     │  & RANK  │                                          │
│     └────┬─────┘                                          │
│          ▼                                                │
│     ┌──────────┐                                          │
│     │ RECOMMEND│                                          │
│     └────┬─────┘                                          │
│          └──────────────────────────────────────────┐     │
│                                                     ▼     │
│                                              ┌──────────┐ │
│                                              │ RESPOND  │ │
│                                              └──────────┘ │
└────────────────────────────────────────────────────────────┘
```

---

## Notes

- Start with simple linear flows, add complexity incrementally
- Use LangGraph's visualization tools for debugging conversation flows
- Implement comprehensive logging for conversation state changes
- Consider implementing conversation branching for complex scenarios
- Monitor conversation analytics to optimize routing decisions

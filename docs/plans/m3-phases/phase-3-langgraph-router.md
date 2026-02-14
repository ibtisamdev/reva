# Phase 3: LangGraph Router & State Machine

> **Parent:** [M3 Sales & Recommendation Agent](../m3-sales-agent.md)
> **Duration:** 1 week
> **Status:** Complete
> **Dependencies:** Phase 1 (Product Search), Phase 2 (Recommendations)

---

## Goal

Implement a conversation routing system using LangGraph that classifies customer intent, maintains conversation state, and routes to specialized handlers for sales, support, and product discovery.

---

## Tasks

### 3.1 LangGraph State Schema

**Location:** `apps/api/app/services/graph/state.py`
**Status:** COMPLETED

- [x] Define conversation state schema for LangGraph
- [x] Include intent, confidence, and message history
- [x] Track tool usage for persistence and analytics
- [x] Track tool availability flags (order tools, product tools)

**Implementation:**

```python
class ConversationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    intent: str
    confidence: float
    store_id: str
    store_name: str
    tools_used: list[str]
    has_order_tools: bool
    has_product_tools: bool
    tool_calls_record: list[dict[str, Any]]
    tool_results_record: list[dict[str, Any]]
```

> **Note:** The state is intentionally lean (10 fields) compared to the original plan (~30 fields). Product context and search results flow through tool calls and messages, not state fields. This keeps the state focused on routing and observability.

### 3.2 Intent Classification Node

**Location:** `apps/api/app/services/graph/nodes.py` (`classify_intent` function)
**Status:** COMPLETED

- [x] Implement LLM-based intent classification using GPT-4o (temp=0)
- [x] Define 6 intent categories with confidence scores
- [x] Handle JSON response parsing (including markdown-wrapped responses)
- [x] Fallback to small_talk/0.3 on parse failure
- [x] Update conversation state with classified intent

**Intent Categories (6, not 18 as originally planned):**

```python
# Defined in app/services/graph/prompts.py (INTENT_CLASSIFIER_PROMPT)
- product_search       # Finding, browsing, discovering products
- product_recommendation  # Recommendations, comparisons, alternatives
- order_status         # Order tracking, shipping, delivery
- faq_support          # Policies, returns, general store questions
- small_talk           # Greetings, thanks, off-topic
- complaint            # Unhappy customer, problems, refund requests
```

> **Note:** The simpler 6-intent system provides higher classification accuracy than the originally planned 18 intents. The LLM returns JSON `{"intent": "...", "confidence": 0.0-1.0}` with max_tokens=100.

### 3.3 Conversation Router Node

**Location:** `apps/api/app/services/graph/router.py`
**Status:** COMPLETED

- [x] Route conversations based on classified intent
- [x] Handle confidence threshold (CLARIFY_THRESHOLD = 0.6)
- [x] Map intents to node names
- [x] Default unknown intents to general node

**Implementation:**

```python
CLARIFY_THRESHOLD = 0.6

def route_conversation(state: ConversationState) -> str:
    intent = state.get("intent", "small_talk")
    confidence = state.get("confidence", 0.0)

    if confidence < CLARIFY_THRESHOLD:
        return "clarify"

    intent_to_node = {
        "product_search": "search",
        "product_recommendation": "recommend",
        "order_status": "support",
        "faq_support": "support",
        "complaint": "support",
        "small_talk": "general",
    }
    return intent_to_node.get(intent, "general")
```

> **Note:** Single threshold at 0.6, not the three-tier system (0.8/0.5) in the original plan. Simpler and works well in practice.

### 3.4 Product Search Node

**Location:** `apps/api/app/services/graph/nodes.py` (`search_node` function)
**Status:** COMPLETED

- [x] Execute product search via LangChain tools
- [x] Force-first-tool-call behavior (always searches before asking questions)
- [x] Agentic tool loop with max 3 iterations (`_run_tool_loop`)
- [x] Track tool calls and results for persistence
- [x] System prompt enforces search-first behavior

> **Note:** All nodes are in a single `nodes.py` file (not a separate `nodes/` directory). The `_run_tool_loop()` function handles the iterative tool calling pattern shared by search and recommend nodes.

### 3.5 Recommendation Node

**Location:** `apps/api/app/services/graph/nodes.py` (`recommend_node` function)
**Status:** COMPLETED

- [x] Generate product recommendations via LangChain tools
- [x] Handle similar, upsell, cross-sell, and compare flows
- [x] Force-first-tool-call behavior
- [x] Same agentic tool loop pattern as search node

### 3.6 Support Nodes

**Location:** `apps/api/app/services/graph/nodes.py`
**Status:** COMPLETED

- [x] `support_node` — Handles order status, FAQ, and complaints. Receives order tools when available and includes dynamic ORDER STATUS INSTRUCTIONS in the system prompt.
- [x] `general_node` — Handles small talk with store name personalization and RAG context.
- [x] `clarify_node` — Asks one clarifying question when intent confidence is below threshold.

> **Note:** A single `support_node` handles order/FAQ/complaint intents (all routed to "support" by the router). Separate `general_node` and `clarify_node` handle their respective cases.

### 3.7 LangGraph Workflow Definition

**Location:** `apps/api/app/services/graph/workflow.py`
**Status:** COMPLETED

- [x] Define complete conversation graph with `create_sales_graph()`
- [x] Set up 6 nodes and conditional edges
- [x] Per-request graph creation with closure-bound tools and context
- [x] Error handling via tool loop iteration limits

**Implementation:**

```python
def create_sales_graph(
    product_tools, order_tools, context_text, product_text, context_section
) -> CompiledGraph:
    # Creates closure-based node wrappers that capture tools/context
    # 6 nodes: classify, search, recommend, support, general, clarify
    # Entry: classify → conditional edge (route_conversation) → action node → END
```

> **Note:** The graph is created per-request (not once at startup) because tools are bound to the specific store's SearchService and RecommendationService instances for multi-tenant isolation.

### 3.8 Chat Service Integration

**Location:** `apps/api/app/services/chat_service.py`
**Status:** COMPLETED

- [x] LangGraph workflow fully integrated into ChatService.process_message()
- [x] Builds graph per-request with store-scoped tools
- [x] Reconstructs LangChain message history for multi-turn context
- [x] Persists tool calls and results on Message model
- [x] Product tools created via factory pattern (`create_product_tools`)

> **Note:** Streaming is not yet implemented — responses are returned as complete messages. The `_generate_response` method handles the full LangGraph lifecycle.

### 3.9 Analytics & Monitoring

**Location:** Not built
**Status:** DEFERRED → [deferred-features.md](../deferred-features.md)

- [ ] ~~Track conversation flow through graph nodes~~
- [ ] ~~Monitor intent classification accuracy~~
- [ ] ~~Measure conversation completion rates~~
- [ ] ~~Identify common routing patterns~~
- [ ] ~~Generate insights for graph optimization~~

> **Note:** Basic observability exists via logging in nodes.py. Tool calls and results are persisted on the Message model (`tool_calls`, `tool_results` JSONB columns) for debugging. A dedicated analytics table was not created.

---

## Files Created/Modified

| File                                    | Action   | Purpose                                        |
| --------------------------------------- | -------- | ---------------------------------------------- |
| `app/services/graph/__init__.py`        | Created  | Package init, exports create_sales_graph       |
| `app/services/graph/state.py`           | Created  | ConversationState TypedDict (10 fields)        |
| `app/services/graph/nodes.py`           | Created  | classify_intent + 5 node functions + tool loop |
| `app/services/graph/router.py`          | Created  | route_conversation conditional edge function   |
| `app/services/graph/workflow.py`        | Created  | create_sales_graph graph builder               |
| `app/services/graph/prompts.py`         | Created  | 6 system prompts                               |
| `app/services/tools/__init__.py`        | Created  | Package init                                   |
| `app/services/tools/product_tools.py`   | Created  | 6 LangChain tools with per-request factory     |
| `app/services/chat_service.py`          | Modified | Full LangGraph integration                     |

---

## Dependencies

Already in `pyproject.toml`:

```toml
langgraph >= 0.2.0
langchain-core >= 0.3.0
langchain-openai >= 0.3.0
```

---

## Testing

- [x] Unit test: routing logic with various confidence scores and intents (`tests/test_graph.py::TestRouteConversation` — 12 test cases)
- [x] Unit test: intent classification returns valid JSON (`tests/test_graph.py::TestClassifyIntent` — 3 test cases)
- [x] Unit test: workflow compilation with and without tools (`tests/test_graph.py::TestWorkflowCreation` — 2 test cases)
- [x] Unit test: product tool invocation and results (`tests/test_product_tools.py` — 4 test classes)
- [ ] Integration test: complete conversation flows through graph
- [ ] Performance test: graph execution time under load

---

## Acceptance Criteria

1. **Intent Classification**: Classifies 6 intent types with JSON confidence scores — DONE
2. **Conversation Routing**: Routes to appropriate node based on intent + 0.6 confidence threshold — DONE
3. **State Management**: 10-field ConversationState with message history — DONE
4. **Flow Control**: classify → route → node → END for all paths — DONE
5. **Error Handling**: JSON parse fallback, tool error catching, max 3 iterations — DONE
6. **Analytics**: ~~Tracks conversation flows~~ — DEFERRED
7. **Scalability**: Per-request graph creation, no shared mutable state — DONE

---

## LangGraph Visualization

```
┌──────────────────────────────────────────────────────────────┐
│                     SALES AGENT GRAPH                        │
│                                                              │
│  ┌─────────┐     ┌──────────────┐     ┌──────────────┐      │
│  │  START  │────▶│   CLASSIFY   │────▶│    ROUTE     │      │
│  └─────────┘     │   INTENT     │     └──────┬───────┘      │
│                  └──────────────┘            │               │
│       ┌──────────┬──────────┬───────────┬────┴──────┐       │
│       ▼          ▼          ▼           ▼           ▼       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌────────┐   │
│  │ SEARCH │ │RECOMMEND│ │SUPPORT│ │ GENERAL │ │CLARIFY │   │
│  └───┬────┘ └───┬────┘ └───┬───┘ └────┬────┘ └───┬────┘   │
│      │          │          │           │          │         │
│      └──────────┴──────────┴───────────┴──────────┘         │
│                            │                                 │
│                       ┌────▼────┐                            │
│                       │   END   │                            │
│                       └─────────┘                            │
└──────────────────────────────────────────────────────────────┘
```

**Routing rules:**
- confidence < 0.6 → CLARIFY
- product_search → SEARCH
- product_recommendation → RECOMMEND
- order_status / faq_support / complaint → SUPPORT
- small_talk → GENERAL

---

## Notes

- Started simple with 6 intents and single confidence threshold — can add granularity later
- Per-request graph creation ensures multi-tenant isolation via closure-bound tools
- Force-first-tool-call prompts prevent unnecessary clarification questions
- Tool loop capped at 3 iterations to prevent runaway tool calling
- Streaming responses not yet implemented — full response returned

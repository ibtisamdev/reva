"""LangGraph conditional routing logic."""

from app.services.graph.state import ConversationState

# Confidence threshold below which we ask for clarification
CLARIFY_THRESHOLD = 0.6


def route_conversation(state: ConversationState) -> str:
    """Route to the appropriate node based on classified intent.

    This is used as the conditional edge function in the LangGraph workflow.

    Returns:
        The name of the next node to execute.
    """
    intent = state.get("intent", "small_talk")
    confidence = state.get("confidence", 0.0)

    # Low confidence → ask for clarification
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

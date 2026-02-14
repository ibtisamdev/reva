"""LangGraph workflow definition for the sales agent."""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from app.services.graph.nodes import (
    clarify_node,
    classify_intent,
    general_node,
    recommend_node,
    search_node,
    support_node,
)
from app.services.graph.router import route_conversation
from app.services.graph.state import ConversationState

logger = logging.getLogger(__name__)


def create_sales_graph(
    product_tools: list[Any] | None = None,
    order_tools: list[Any] | None = None,
    context_text: str = "",
    product_text: str = "",
    context_section: str = "",
) -> Any:
    """Build and compile the LangGraph sales agent workflow.

    Args:
        product_tools: Product search and recommendation tools
        order_tools: Order status tools
        context_text: RAG context from knowledge base
        product_text: Product context for the prompt
        context_section: General context section for prompts

    Returns:
        Compiled LangGraph workflow
    """
    # Combine tools for each node type
    search_tools = list(product_tools or [])
    recommend_tools = list(product_tools or [])
    support_tools = list(order_tools or [])

    # Create node functions with bound arguments
    async def _search_node(state: ConversationState) -> dict[str, Any]:
        return await search_node(state, tools=search_tools or None, context_section=context_section)

    async def _recommend_node(state: ConversationState) -> dict[str, Any]:
        return await recommend_node(
            state, tools=recommend_tools or None, context_section=context_section
        )

    async def _support_node(state: ConversationState) -> dict[str, Any]:
        return await support_node(
            state,
            tools=support_tools or None,
            context_text=context_text,
            product_text=product_text,
        )

    async def _general_node(state: ConversationState) -> dict[str, Any]:
        return await general_node(state, context_section=context_section)

    async def _clarify_node(state: ConversationState) -> dict[str, Any]:
        return await clarify_node(state, context_section=context_section)

    # Build the graph
    graph = StateGraph(ConversationState)

    # Add nodes
    graph.add_node("classify", classify_intent)
    graph.add_node("search", _search_node)
    graph.add_node("recommend", _recommend_node)
    graph.add_node("support", _support_node)
    graph.add_node("general", _general_node)
    graph.add_node("clarify", _clarify_node)

    # Set entry point
    graph.set_entry_point("classify")

    # Add conditional routing from classifier
    graph.add_conditional_edges(
        "classify",
        route_conversation,
        {
            "search": "search",
            "recommend": "recommend",
            "support": "support",
            "general": "general",
            "clarify": "clarify",
        },
    )

    # All action nodes go to END
    graph.add_edge("search", END)
    graph.add_edge("recommend", END)
    graph.add_edge("support", END)
    graph.add_edge("general", END)
    graph.add_edge("clarify", END)

    return graph.compile()

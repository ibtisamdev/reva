"""LangGraph conversation state definition."""

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ConversationState(TypedDict):
    """State that flows through the LangGraph conversation workflow.

    Attributes:
        messages: Chat message history (uses LangGraph's add_messages reducer)
        intent: Classified intent for the current message
        confidence: Confidence score of the intent classification (0-1)
        store_id: Store ID for multi-tenant scoping
        store_name: Store display name for prompts
        tools_used: List of tool names used during this turn
        has_order_tools: Whether order tools are available
        has_product_tools: Whether product tools are available
        tool_calls_record: Detailed tool call records for persistence
        tool_results_record: Detailed tool result records for persistence
    """

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

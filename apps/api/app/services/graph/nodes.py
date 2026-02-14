"""LangGraph node functions for the sales agent workflow."""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.services.graph.prompts import (
    CLARIFY_NODE_PROMPT,
    GENERAL_NODE_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    RECOMMEND_NODE_PROMPT,
    SEARCH_NODE_PROMPT,
    SUPPORT_NODE_PROMPT,
)
from app.services.graph.state import ConversationState

logger = logging.getLogger(__name__)

CHAT_MODEL = "gpt-4o"
MAX_RESPONSE_TOKENS = 800
MAX_TOOL_ITERATIONS = 3


@dataclass
class ToolLoopResult:
    """Result from the agentic tool loop."""

    content: str
    tools_used: list[str] = field(default_factory=list)
    tool_calls_record: list[dict[str, Any]] = field(default_factory=list)
    tool_results_record: list[dict[str, Any]] = field(default_factory=list)


def _get_llm() -> ChatOpenAI:
    """Create a ChatOpenAI instance."""
    return ChatOpenAI(
        model=CHAT_MODEL,
        api_key=settings.openai_api_key,
        temperature=0.7,
        max_tokens=MAX_RESPONSE_TOKENS,
    )


def _get_last_human_message(state: ConversationState) -> str:
    """Extract the last human message from state."""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else ""
    return ""


async def _run_tool_loop(
    llm: Any,
    messages: list[Any],
    tools: list[Any],
    max_iterations: int = MAX_TOOL_ITERATIONS,
    force_first_tool_call: bool = False,
) -> ToolLoopResult:
    """Run the agentic tool loop with full tracking.

    Args:
        force_first_tool_call: When True, forces the LLM to call a tool on the
            first iteration using tool_choice="required". This prevents the model
            from asking clarifying questions instead of using its tools.

    Returns:
        ToolLoopResult with content, tools used, and detailed records
    """
    result = ToolLoopResult(content="")
    tool_names = [t.name for t in tools]
    logger.info(
        "Tool loop started: force_first=%s, tools=%s", force_first_tool_call, tool_names
    )

    for i in range(max_iterations):
        if force_first_tool_call and i == 0:
            bound_llm = llm.bind_tools(tools, tool_choice="required")
        else:
            bound_llm = llm.bind_tools(tools)

        response: AIMessage = await bound_llm.ainvoke(messages)

        if not response.tool_calls:
            logger.info("Tool loop iteration %d: no tool calls, returning text response", i)
            result.content = response.content if isinstance(response.content, str) else ""
            return result

        logger.info(
            "Tool loop iteration %d: tool calls=%s",
            i,
            [tc["name"] for tc in response.tool_calls],
        )
        messages.append(response)
        for tc in response.tool_calls:
            result.tools_used.append(tc["name"])
            result.tool_calls_record.append(
                {
                    "id": tc["id"],
                    "name": tc["name"],
                    "args": tc["args"],
                }
            )

            tool_fn = next((t for t in tools if t.name == tc["name"]), None)
            try:
                if tool_fn:
                    tool_result = await tool_fn.ainvoke(tc["args"])
                else:
                    tool_result = f"Unknown tool: {tc['name']}"
            except Exception as e:
                logger.exception("Tool execution error: %s", tc["name"])
                tool_result = f"Error: {e}"

            result.tool_results_record.append(
                {
                    "tool_call_id": tc["id"],
                    "result": str(tool_result),
                }
            )
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

    result.content = "I'm having trouble processing your request. Please try again."
    return result


async def classify_intent(state: ConversationState) -> dict[str, Any]:
    """Classify the intent of the latest user message."""
    user_message = _get_last_human_message(state)

    llm = ChatOpenAI(
        model=CHAT_MODEL,
        api_key=settings.openai_api_key,
        temperature=0.0,
        max_tokens=100,
    )

    prompt = INTENT_CLASSIFIER_PROMPT.format(message=user_message)
    response = await llm.ainvoke([HumanMessage(content=prompt)])

    content = response.content if isinstance(response.content, str) else ""

    # Strip markdown code fences if present (GPT-4o sometimes wraps JSON in ```json ... ```)
    content = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    content = re.sub(r"\n?```\s*$", "", content.strip())

    # Parse the JSON response
    try:
        parsed = json.loads(content)
        intent = parsed.get("intent", "small_talk")
        confidence = float(parsed.get("confidence", 0.5))
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Failed to parse intent classifier response: %s", content)
        intent = "small_talk"
        confidence = 0.3

    logger.info("Intent classified: intent=%s, confidence=%.2f, message=%r", intent, confidence, user_message)
    return {"intent": intent, "confidence": confidence}


async def search_node(
    state: ConversationState,
    tools: list[Any] | None = None,
    context_section: str = "",
) -> dict[str, Any]:
    """Handle product search queries."""
    llm = _get_llm()
    store_name = state.get("store_name", "the store")

    system = SEARCH_NODE_PROMPT.format(
        store_name=store_name,
        context_section=context_section,
    )
    messages: list[Any] = [SystemMessage(content=system)] + list(state["messages"])

    if tools:
        result = await _run_tool_loop(llm, messages, tools, force_first_tool_call=True)
    else:
        response = await llm.ainvoke(messages)
        result = ToolLoopResult(
            content=response.content if isinstance(response.content, str) else ""
        )

    return {
        "messages": [AIMessage(content=result.content)],
        "tools_used": result.tools_used,
        "tool_calls_record": result.tool_calls_record,
        "tool_results_record": result.tool_results_record,
    }


async def recommend_node(
    state: ConversationState,
    tools: list[Any] | None = None,
    context_section: str = "",
) -> dict[str, Any]:
    """Handle product recommendation queries."""
    llm = _get_llm()
    store_name = state.get("store_name", "the store")

    system = RECOMMEND_NODE_PROMPT.format(
        store_name=store_name,
        context_section=context_section,
    )
    messages: list[Any] = [SystemMessage(content=system)] + list(state["messages"])

    if tools:
        result = await _run_tool_loop(llm, messages, tools, force_first_tool_call=True)
    else:
        response = await llm.ainvoke(messages)
        result = ToolLoopResult(
            content=response.content if isinstance(response.content, str) else ""
        )

    return {
        "messages": [AIMessage(content=result.content)],
        "tools_used": result.tools_used,
        "tool_calls_record": result.tool_calls_record,
        "tool_results_record": result.tool_results_record,
    }


async def support_node(
    state: ConversationState,
    tools: list[Any] | None = None,
    context_text: str = "",
    product_text: str = "",
) -> dict[str, Any]:
    """Handle order status and FAQ support queries."""
    llm = _get_llm()
    store_name = state.get("store_name", "the store")
    has_order_tools = state.get("has_order_tools", False)

    order_instructions = ""
    if has_order_tools:
        order_instructions = """
ORDER STATUS INSTRUCTIONS:
1. When a customer asks about their order status, you MUST ask for BOTH their order number AND email address before using the verification tool
2. NEVER reveal order details without successful verification
3. After verification, use the lookup_order_status tool for follow-up questions about the same order
4. When sharing tracking info, always include the tracking number and carrier name
5. Use get_tracking_details when the customer asks specifically about tracking, shipping, or delivery
6. If verification fails, suggest the customer double-check their order number and email"""

    system = SUPPORT_NODE_PROMPT.format(
        store_name=store_name,
        order_instructions=order_instructions,
        context_text=context_text or "No knowledge base context available.",
        product_text=product_text or "No matching products found.",
    )
    messages: list[Any] = [SystemMessage(content=system)] + list(state["messages"])

    if tools:
        result = await _run_tool_loop(llm, messages, tools)
    else:
        response = await llm.ainvoke(messages)
        result = ToolLoopResult(
            content=response.content if isinstance(response.content, str) else ""
        )

    return {
        "messages": [AIMessage(content=result.content)],
        "tools_used": result.tools_used,
        "tool_calls_record": result.tool_calls_record,
        "tool_results_record": result.tool_results_record,
    }


async def general_node(
    state: ConversationState,
    context_section: str = "",
) -> dict[str, Any]:
    """Handle small talk and general conversation."""
    llm = _get_llm()
    store_name = state.get("store_name", "the store")

    system = GENERAL_NODE_PROMPT.format(
        store_name=store_name,
        context_section=context_section,
    )
    messages: list[Any] = [SystemMessage(content=system)] + list(state["messages"])

    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else ""

    return {
        "messages": [AIMessage(content=content)],
        "tools_used": [],
        "tool_calls_record": [],
        "tool_results_record": [],
    }


async def clarify_node(
    state: ConversationState,
    context_section: str = "",
) -> dict[str, Any]:
    """Ask clarifying questions when intent is unclear."""
    llm = _get_llm()
    store_name = state.get("store_name", "the store")

    system = CLARIFY_NODE_PROMPT.format(
        store_name=store_name,
        context_section=context_section,
    )
    messages: list[Any] = [SystemMessage(content=system)] + list(state["messages"])

    response = await llm.ainvoke(messages)
    content = response.content if isinstance(response.content, str) else ""

    return {
        "messages": [AIMessage(content=content)],
        "tools_used": [],
        "tool_calls_record": [],
        "tool_results_record": [],
    }

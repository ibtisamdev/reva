"""Unit tests for LangGraph router and workflow."""

import pytest

from app.services.graph.router import CLARIFY_THRESHOLD, route_conversation


class TestRouteConversation:
    """Tests for the route_conversation conditional edge function."""

    def test_routes_product_search(self) -> None:
        state = {"intent": "product_search", "confidence": 0.9}
        assert route_conversation(state) == "search"

    def test_routes_product_recommendation(self) -> None:
        state = {"intent": "product_recommendation", "confidence": 0.8}
        assert route_conversation(state) == "recommend"

    def test_routes_order_status_to_support(self) -> None:
        state = {"intent": "order_status", "confidence": 0.85}
        assert route_conversation(state) == "support"

    def test_routes_faq_support_to_support(self) -> None:
        state = {"intent": "faq_support", "confidence": 0.7}
        assert route_conversation(state) == "support"

    def test_routes_complaint_to_support(self) -> None:
        state = {"intent": "complaint", "confidence": 0.75}
        assert route_conversation(state) == "support"

    def test_routes_small_talk_to_general(self) -> None:
        state = {"intent": "small_talk", "confidence": 0.9}
        assert route_conversation(state) == "general"

    def test_routes_unknown_intent_to_general(self) -> None:
        state = {"intent": "unknown_intent", "confidence": 0.8}
        assert route_conversation(state) == "general"

    def test_low_confidence_routes_to_clarify(self) -> None:
        state = {"intent": "product_search", "confidence": 0.3}
        assert route_conversation(state) == "clarify"

    def test_confidence_at_threshold_routes_to_intent(self) -> None:
        state = {"intent": "product_search", "confidence": CLARIFY_THRESHOLD}
        assert route_conversation(state) == "search"

    def test_confidence_just_below_threshold_routes_to_clarify(self) -> None:
        state = {"intent": "product_search", "confidence": CLARIFY_THRESHOLD - 0.01}
        assert route_conversation(state) == "clarify"

    def test_missing_intent_defaults_to_general(self) -> None:
        state = {"confidence": 0.9}
        assert route_conversation(state) == "general"

    def test_missing_confidence_defaults_to_clarify(self) -> None:
        state = {"intent": "product_search"}
        assert route_conversation(state) == "clarify"


class TestClassifyIntent:
    """Tests for the classify_intent node function."""

    @pytest.mark.asyncio
    async def test_returns_intent_and_confidence(
        self,
        mock_openai_chat: None,
    ) -> None:
        """classify_intent returns intent and confidence from LLM JSON response."""
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage, HumanMessage

        # Mock the LLM to return a JSON response
        mock_llm = MagicMock()
        mock_response = AIMessage(content='{"intent": "product_search", "confidence": 0.92}')
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Patch _get_llm equivalent — classify_intent creates ChatOpenAI internally
        # Since mock_openai_chat patches ChatOpenAI at the module level,
        # we directly test the parsing logic
        from app.services.graph.nodes import classify_intent

        state = {"messages": [HumanMessage(content="show me red shoes")]}

        result = await classify_intent(state)

        # The mock_openai_chat fixture returns a mock that returns content
        # We just verify it returns a dict with intent and confidence keys
        assert "intent" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_handles_invalid_json(
        self,
        mock_openai_chat: None,
    ) -> None:
        """classify_intent defaults gracefully when LLM returns non-JSON."""
        from langchain_core.messages import HumanMessage

        from app.services.graph.nodes import classify_intent

        state = {"messages": [HumanMessage(content="hello")]}
        result = await classify_intent(state)

        # Should still return valid intent/confidence (defaults on parse failure)
        assert isinstance(result["intent"], str)
        assert isinstance(result["confidence"], float)

    @pytest.mark.asyncio
    async def test_handles_markdown_wrapped_json(self) -> None:
        """classify_intent correctly parses JSON wrapped in markdown code fences."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from langchain_core.messages import AIMessage, HumanMessage

        from app.services.graph.nodes import classify_intent

        md_content = '```json\n{"intent": "product_recommendation", "confidence": 0.95}\n```'
        mock_response = AIMessage(content=md_content)

        with patch("app.services.graph.nodes.ChatOpenAI") as mock_class:
            mock_llm = MagicMock()
            mock_class.return_value = mock_llm
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)

            state = {"messages": [HumanMessage(content="recommend me a snowboard under $1000")]}
            result = await classify_intent(state)

        assert result["intent"] == "product_recommendation"
        assert result["confidence"] == 0.95


class TestWorkflowCreation:
    """Tests for create_sales_graph workflow builder."""

    def test_creates_compilable_graph(self) -> None:
        """create_sales_graph returns a compiled graph."""
        from app.services.graph.workflow import create_sales_graph

        graph = create_sales_graph()
        assert graph is not None

    def test_creates_graph_with_tools(self) -> None:
        """create_sales_graph accepts tool lists without error."""
        from unittest.mock import MagicMock

        from app.services.graph.workflow import create_sales_graph

        mock_tool = MagicMock()
        mock_tool.name = "mock_tool"

        graph = create_sales_graph(
            product_tools=[mock_tool],
            order_tools=[mock_tool],
            context_text="Some context",
            context_section="Context section",
        )
        assert graph is not None

"""Unit tests for LangChain order tool wrappers.

Tests verify_customer_and_lookup_order, lookup_order_status,
and get_tracking_details tools created by create_order_tools().
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.order import FulfillmentInfo, OrderStatusResponse, OrderVerificationResponse
from app.services.order_tools import create_order_tools


@pytest.fixture
def mock_order_service() -> MagicMock:
    """A mock OrderService for tool tests."""
    return MagicMock()


@pytest.fixture
def store_id() -> uuid.UUID:
    return uuid.uuid4()


class TestCreateOrderTools:
    """Tests for create_order_tools()."""

    def test_returns_three_tools(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """create_order_tools returns exactly 3 tools."""
        tools = create_order_tools(mock_order_service, store_id)
        assert len(tools) == 3

    def test_tool_names(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Tools have correct names."""
        tools = create_order_tools(mock_order_service, store_id)
        names = {t.name for t in tools}
        assert names == {
            "verify_customer_and_lookup_order",
            "lookup_order_status",
            "get_tracking_details",
        }


class TestVerifyCustomerTool:
    """Tests for the verify_customer_and_lookup_order tool."""

    @pytest.mark.asyncio
    async def test_calls_service_verify_and_lookup(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Tool calls order_service.verify_and_lookup with correct args."""
        mock_response = OrderVerificationResponse(
            verified=True,
            order=None,
            message="Order verified successfully.",
        )
        mock_order_service.verify_and_lookup = AsyncMock(return_value=mock_response)

        tools = create_order_tools(mock_order_service, store_id)
        verify_tool = next(t for t in tools if t.name == "verify_customer_and_lookup_order")

        await verify_tool.ainvoke({"order_number": "#1001", "email": "test@example.com"})

        mock_order_service.verify_and_lookup.assert_awaited_once_with(
            store_id, "#1001", "test@example.com"
        )

    @pytest.mark.asyncio
    async def test_returns_json_string(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Tool returns a valid JSON string."""
        mock_response = OrderVerificationResponse(
            verified=True,
            order=None,
            message="Order verified successfully.",
        )
        mock_order_service.verify_and_lookup = AsyncMock(return_value=mock_response)

        tools = create_order_tools(mock_order_service, store_id)
        verify_tool = next(t for t in tools if t.name == "verify_customer_and_lookup_order")

        result = await verify_tool.ainvoke({"order_number": "#1001", "email": "test@example.com"})
        parsed = json.loads(result)

        assert parsed["verified"] is True
        assert parsed["message"] == "Order verified successfully."


class TestLookupOrderStatusTool:
    """Tests for the lookup_order_status tool."""

    @pytest.mark.asyncio
    async def test_returns_order_json_when_found(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Returns order status JSON when found."""
        mock_status = OrderStatusResponse(
            order_number="#1001",
            order_id=123,
            email="test@example.com",
            financial_status="paid",
            fulfillment_status=None,
            created_at="2024-01-01T00:00:00Z",
            total_price="10.00",
            currency="USD",
            line_items=[],
            fulfillments=[],
            status_message="Your order is being processed.",
        )
        mock_order_service.get_order_status = AsyncMock(return_value=mock_status)

        tools = create_order_tools(mock_order_service, store_id)
        lookup_tool = next(t for t in tools if t.name == "lookup_order_status")

        result = await lookup_tool.ainvoke({"order_number": "#1001"})
        parsed = json.loads(result)

        assert parsed["order_number"] == "#1001"
        assert parsed["financial_status"] == "paid"

    @pytest.mark.asyncio
    async def test_returns_error_when_not_found(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Returns error JSON when order not found."""
        mock_order_service.get_order_status = AsyncMock(return_value=None)

        tools = create_order_tools(mock_order_service, store_id)
        lookup_tool = next(t for t in tools if t.name == "lookup_order_status")

        result = await lookup_tool.ainvoke({"order_number": "#9999"})
        parsed = json.loads(result)

        assert "error" in parsed
        assert "not found" in parsed["error"].lower()

    @pytest.mark.asyncio
    async def test_calls_service_get_order_status(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Tool calls order_service.get_order_status with correct args."""
        mock_order_service.get_order_status = AsyncMock(return_value=None)

        tools = create_order_tools(mock_order_service, store_id)
        lookup_tool = next(t for t in tools if t.name == "lookup_order_status")

        await lookup_tool.ainvoke({"order_number": "#1001"})

        mock_order_service.get_order_status.assert_awaited_once_with(
            store_id, "#1001"
        )


class TestGetTrackingDetailsTool:
    """Tests for the get_tracking_details tool."""

    @pytest.mark.asyncio
    async def test_returns_tracking_data(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Returns structured tracking data with shipment info."""
        mock_status = OrderStatusResponse(
            order_number="#1001",
            order_id=123,
            email="test@example.com",
            financial_status="paid",
            fulfillment_status="fulfilled",
            created_at="2024-01-01T00:00:00Z",
            total_price="10.00",
            currency="USD",
            line_items=[],
            fulfillments=[
                FulfillmentInfo(
                    status="success",
                    tracking_number="1Z999",
                    tracking_url="https://ups.com/track/1Z999",
                    tracking_company="UPS",
                    shipment_status="delivered",
                ),
            ],
            status_message="Your order has been shipped.",
        )
        mock_order_service.get_order_status = AsyncMock(return_value=mock_status)

        tools = create_order_tools(mock_order_service, store_id)
        tracking_tool = next(t for t in tools if t.name == "get_tracking_details")

        result = await tracking_tool.ainvoke({"order_number": "#1001"})
        parsed = json.loads(result)

        assert parsed["order_number"] == "#1001"
        assert parsed["total_shipments"] == 1
        assert parsed["shipments"][0]["tracking_number"] == "1Z999"
        assert parsed["shipments"][0]["carrier"] == "UPS"

    @pytest.mark.asyncio
    async def test_returns_unfulfilled_message(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Returns unfulfilled message when no fulfillments exist."""
        mock_status = OrderStatusResponse(
            order_number="#1001",
            order_id=123,
            email="test@example.com",
            financial_status="paid",
            fulfillment_status=None,
            created_at="2024-01-01T00:00:00Z",
            total_price="10.00",
            currency="USD",
            line_items=[],
            fulfillments=[],
            status_message="Order being prepared.",
        )
        mock_order_service.get_order_status = AsyncMock(return_value=mock_status)

        tools = create_order_tools(mock_order_service, store_id)
        tracking_tool = next(t for t in tools if t.name == "get_tracking_details")

        result = await tracking_tool.ainvoke({"order_number": "#1001"})
        parsed = json.loads(result)

        assert parsed["status"] == "unfulfilled"
        assert "not been shipped" in parsed["message"]

    @pytest.mark.asyncio
    async def test_returns_error_when_not_found(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Returns error JSON when order not found."""
        mock_order_service.get_order_status = AsyncMock(return_value=None)

        tools = create_order_tools(mock_order_service, store_id)
        tracking_tool = next(t for t in tools if t.name == "get_tracking_details")

        result = await tracking_tool.ainvoke({"order_number": "#9999"})
        parsed = json.loads(result)

        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_multiple_fulfillments(
        self, mock_order_service: MagicMock, store_id: uuid.UUID
    ) -> None:
        """Handles multiple fulfillments correctly."""
        mock_status = OrderStatusResponse(
            order_number="#1001",
            order_id=123,
            email="test@example.com",
            financial_status="paid",
            fulfillment_status="partial",
            created_at="2024-01-01T00:00:00Z",
            total_price="100.00",
            currency="USD",
            line_items=[],
            fulfillments=[
                FulfillmentInfo(
                    status="success",
                    tracking_number="TRACK1",
                    tracking_company="FedEx",
                ),
                FulfillmentInfo(
                    status="success",
                    tracking_number="TRACK2",
                    tracking_company="DHL",
                ),
            ],
            status_message="Order partially shipped.",
        )
        mock_order_service.get_order_status = AsyncMock(return_value=mock_status)

        tools = create_order_tools(mock_order_service, store_id)
        tracking_tool = next(t for t in tools if t.name == "get_tracking_details")

        result = await tracking_tool.ainvoke({"order_number": "#1001"})
        parsed = json.loads(result)

        assert parsed["total_shipments"] == 2
        assert parsed["shipments"][0]["shipment"] == 1
        assert parsed["shipments"][1]["shipment"] == 2
        assert parsed["shipments"][0]["carrier"] == "FedEx"
        assert parsed["shipments"][1]["carrier"] == "DHL"

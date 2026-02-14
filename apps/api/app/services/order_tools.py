"""LangChain @tool definitions for order status operations.

Tools are created per-request via create_order_tools() to ensure
multi-tenant isolation — each tool closes over order_service and store_id.

These tools work unchanged in LangGraph tool_node (M3 forward compatibility).
"""

from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services.order_service import OrderService


class VerifyCustomerInput(BaseModel):
    """Input for customer verification."""

    order_number: str = Field(description="Order number (e.g., '#1001' or '1001')")
    email: str = Field(description="Customer's email address for verification")


class OrderLookupInput(BaseModel):
    """Input for order status lookup."""

    order_number: str = Field(description="Order number to look up")


class TrackingLookupInput(BaseModel):
    """Input for tracking details lookup."""

    order_number: str = Field(description="Order number to get tracking for")


def create_order_tools(order_service: OrderService, store_id: UUID) -> list[Any]:
    """Create LangChain tools bound to a specific store context.

    Returns list of @tool-decorated functions for bind_tools().
    Each tool closes over order_service and store_id for multi-tenant safety.
    """

    @tool(args_schema=VerifyCustomerInput)
    async def verify_customer_and_lookup_order(order_number: str, email: str) -> str:
        """Verify a customer's identity and look up their order status.
        Use when a customer asks about their order and provides both
        order number and email address."""
        result = await order_service.verify_and_lookup(store_id, order_number, email)
        return result.model_dump_json()

    @tool(args_schema=OrderLookupInput)
    async def lookup_order_status(order_number: str) -> str:
        """Look up the current status of an order.
        Use after the customer has already been verified in this conversation."""
        result = await order_service.get_order_status(store_id, order_number)
        if result:
            return result.model_dump_json()
        return '{"error": "Order not found"}'

    @tool(args_schema=TrackingLookupInput)
    async def get_tracking_details(order_number: str) -> str:
        """Get detailed tracking/shipping info for an order.
        Use when customer asks specifically about tracking, shipping, or delivery."""
        result = await order_service.get_order_status(store_id, order_number)
        if not result:
            return '{"error": "Order not found"}'

        if not result.fulfillments:
            return (
                '{"status": "unfulfilled", '
                '"message": "This order has not been shipped yet. '
                'It is being prepared for shipment."}'
            )

        # Format tracking details
        tracking_parts = []
        for i, f in enumerate(result.fulfillments, 1):
            info = {
                "shipment": i,
                "status": f.status,
                "tracking_number": f.tracking_number,
                "tracking_url": f.tracking_url,
                "carrier": f.tracking_company,
                "shipment_status": f.shipment_status,
            }
            tracking_parts.append(info)

        import json

        return json.dumps(
            {
                "order_number": result.order_number,
                "fulfillment_status": result.fulfillment_status,
                "shipments": tracking_parts,
                "total_shipments": len(tracking_parts),
            }
        )

    return [verify_customer_and_lookup_order, lookup_order_status, get_tracking_details]

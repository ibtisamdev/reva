"""Order-related Pydantic schemas for M2 Order Status Agent."""

from datetime import datetime

from app.schemas.common import BaseSchema


class OrderLineItem(BaseSchema):
    """A single line item from an order."""

    title: str
    quantity: int
    price: str
    variant_title: str | None = None


class FulfillmentInfo(BaseSchema):
    """Fulfillment/tracking information for an order."""

    status: str
    tracking_number: str | None = None
    tracking_url: str | None = None
    tracking_company: str | None = None
    shipment_status: str | None = None
    created_at: datetime | None = None


class OrderStatusResponse(BaseSchema):
    """Complete order status returned after verification."""

    order_number: str
    order_id: int
    email: str
    financial_status: str
    fulfillment_status: str | None
    created_at: datetime
    total_price: str
    currency: str
    line_items: list[OrderLineItem]
    fulfillments: list[FulfillmentInfo]
    customer_name: str | None = None
    status_message: str
    shipping_city: str | None = None
    shipping_province: str | None = None


class OrderVerificationRequest(BaseSchema):
    """Request to verify customer identity and look up an order."""

    order_number: str
    email: str


class OrderVerificationResponse(BaseSchema):
    """Response from order verification."""

    verified: bool
    order: OrderStatusResponse | None = None
    message: str

"""Order service for verification, lookup, and caching."""

import json
import logging
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_token
from app.integrations.shopify.client import ShopifyClient
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.schemas.order import (
    FulfillmentInfo,
    OrderLineItem,
    OrderStatusResponse,
    OrderVerificationResponse,
)

logger = logging.getLogger(__name__)

# Redis cache TTL for order data
ORDER_CACHE_TTL = 900  # 15 minutes


class OrderService:
    """Business logic for order verification and status lookups."""

    def __init__(self, db: AsyncSession, redis: aioredis.Redis) -> None:
        self.db = db
        self.redis = redis

    async def verify_and_lookup(
        self,
        store_id: UUID,
        order_number: str,
        email: str,
    ) -> OrderVerificationResponse:
        """Verify customer identity by matching email to order, then return status.

        Args:
            store_id: The store to look up the order in.
            order_number: The order display number (e.g., '#1001' or '1001').
            email: Customer email to verify against the order.

        Returns:
            OrderVerificationResponse with verified status and optional order data.
        """
        client = await self._get_shopify_client(store_id)
        if not client:
            return OrderVerificationResponse(
                verified=False,
                message="Order lookup is not available for this store.",
            )

        # Check Redis cache first
        cache_key = f"order:{store_id}:{order_number.lstrip('#')}"
        cached = await self.redis.get(cache_key)

        if cached:
            order_data = json.loads(cached)
        else:
            # Fetch from Shopify
            order_data = await client.get_order_by_number(order_number)
            if not order_data:
                return OrderVerificationResponse(
                    verified=False,
                    message="Order not found. Please check the order number and try again.",
                )
            # Cache the raw order data
            await self.redis.set(cache_key, json.dumps(order_data), ex=ORDER_CACHE_TTL)

        # Verify email matches (case-insensitive)
        order_email = order_data.get("email", "")
        if order_email.lower() != email.lower():
            return OrderVerificationResponse(
                verified=False,
                message="The email address does not match our records for this order.",
            )

        # Fetch fulfillments
        order_id = order_data.get("id")
        fulfillments = await client.get_order_fulfillments(order_id)

        # Build structured response
        order_status = self._build_order_status(order_data, fulfillments)

        return OrderVerificationResponse(
            verified=True,
            order=order_status,
            message="Order verified successfully.",
        )

    async def get_order_status(
        self,
        store_id: UUID,
        order_number: str,
    ) -> OrderStatusResponse | None:
        """Look up order status without verification (for follow-up queries).

        Should only be called after the customer has already been verified
        in the current conversation.
        """
        client = await self._get_shopify_client(store_id)
        if not client:
            return None

        # Check cache
        cache_key = f"order:{store_id}:{order_number.lstrip('#')}"
        cached = await self.redis.get(cache_key)

        if cached:
            order_data = json.loads(cached)
        else:
            order_data = await client.get_order_by_number(order_number)
            if not order_data:
                return None
            await self.redis.set(cache_key, json.dumps(order_data), ex=ORDER_CACHE_TTL)

        order_id = order_data.get("id")
        fulfillments = await client.get_order_fulfillments(order_id)
        return self._build_order_status(order_data, fulfillments)

    async def _get_shopify_client(self, store_id: UUID) -> ShopifyClient | None:
        """Get a ShopifyClient for the given store, or None if not available."""
        stmt = select(StoreIntegration).where(
            StoreIntegration.store_id == store_id,
            StoreIntegration.platform == PlatformType.SHOPIFY,
            StoreIntegration.status == IntegrationStatus.ACTIVE,
        )
        result = await self.db.execute(stmt)
        integration = result.scalar_one_or_none()
        if not integration:
            return None

        try:
            access_token = decrypt_token(integration.credentials.get("access_token", ""))
        except Exception:
            logger.exception("Failed to decrypt Shopify token for store %s", store_id)
            return None

        return ShopifyClient(integration.platform_domain, access_token)

    def _build_order_status(
        self,
        order_data: dict[str, Any],
        fulfillments: list[dict[str, Any]],
    ) -> OrderStatusResponse:
        """Parse Shopify order JSON + fulfillments into a structured response."""
        # Parse line items
        line_items = [
            OrderLineItem(
                title=item.get("title", ""),
                quantity=item.get("quantity", 0),
                price=item.get("price", "0.00"),
                variant_title=item.get("variant_title"),
            )
            for item in order_data.get("line_items", [])
        ]

        # Parse fulfillments
        fulfillment_infos = [
            FulfillmentInfo(
                status=f.get("status", "unknown"),
                tracking_number=f.get("tracking_number"),
                tracking_url=f.get("tracking_url"),
                tracking_company=f.get("tracking_company"),
                shipment_status=f.get("shipment_status"),
                created_at=f.get("created_at"),
            )
            for f in fulfillments
        ]

        # Extract shipping address info
        shipping_address = order_data.get("shipping_address") or {}

        # Build customer name
        customer = order_data.get("customer") or {}
        customer_name = None
        first = customer.get("first_name", "")
        last = customer.get("last_name", "")
        if first or last:
            customer_name = f"{first} {last}".strip()

        # Generate human-readable status message
        status_message = self._get_status_message(order_data, fulfillments)

        return OrderStatusResponse(
            order_number=order_data.get("name", ""),
            order_id=order_data.get("id", 0),
            email=order_data.get("email", ""),
            financial_status=order_data.get("financial_status", "unknown"),
            fulfillment_status=order_data.get("fulfillment_status"),
            created_at=order_data.get("created_at", ""),
            total_price=order_data.get("total_price", "0.00"),
            currency=order_data.get("currency", "USD"),
            line_items=line_items,
            fulfillments=fulfillment_infos,
            customer_name=customer_name,
            status_message=status_message,
            shipping_city=shipping_address.get("city"),
            shipping_province=shipping_address.get("province"),
        )

    def _get_status_message(
        self, order_data: dict[str, Any], fulfillments: list[dict[str, Any]]
    ) -> str:
        """Map financial_status + fulfillment_status to a human-readable message."""
        financial = order_data.get("financial_status", "")
        fulfillment = order_data.get("fulfillment_status")
        cancelled_at = order_data.get("cancelled_at")

        if cancelled_at:
            return "This order has been cancelled."

        if financial == "refunded":
            return "This order has been fully refunded."

        if financial == "partially_refunded":
            return "This order has been partially refunded."

        if fulfillment is None:
            # Unfulfilled
            if financial == "paid":
                return "Your order has been confirmed and is being prepared for shipment."
            if financial == "pending":
                return "Your order is awaiting payment confirmation."
            if financial == "authorized":
                return "Your order payment has been authorized and is being processed."
            return "Your order is being processed."

        if fulfillment == "partial":
            shipped_count = len(fulfillments)
            return (
                f"Your order has been partially shipped ({shipped_count} "
                f"shipment{'s' if shipped_count != 1 else ''} so far)."
            )

        if fulfillment == "fulfilled":
            if fulfillments:
                latest = fulfillments[-1]
                tracking = latest.get("tracking_number")
                carrier = latest.get("tracking_company", "")
                if tracking:
                    return (
                        f"Your order has been shipped"
                        f"{f' via {carrier}' if carrier else ''}. "
                        f"Tracking number: {tracking}"
                    )
            return "Your order has been shipped."

        return "Your order is being processed."

"""Pydantic schemas for Shopify integration and products."""

from datetime import datetime
from typing import Any
from uuid import UUID

from app.schemas.common import BaseSchema


class ShopifyConnectionResponse(BaseSchema):
    """Response for Shopify connection status."""

    platform: str
    platform_domain: str
    status: str
    last_synced_at: datetime | None = None
    product_count: int = 0


class SyncStatusResponse(BaseSchema):
    """Response for sync trigger."""

    status: str
    message: str


class ProductVariantResponse(BaseSchema):
    """A product variant."""

    id: int | str | None = None
    title: str = "Default"
    price: str = "0.00"
    sku: str | None = None
    inventory_quantity: int | None = None


class ProductImageResponse(BaseSchema):
    """A product image."""

    id: int | str | None = None
    src: str
    alt: str | None = None
    position: int = 1


class ProductResponse(BaseSchema):
    """Response for a synced product."""

    id: UUID
    platform_product_id: str
    title: str
    description: str | None = None
    handle: str
    vendor: str | None = None
    product_type: str | None = None
    status: str = "active"
    tags: list[str] = []
    variants: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    synced_at: datetime | None = None
    created_at: datetime

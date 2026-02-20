"""Shopify webhook handlers for product sync and cart recovery."""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db
from app.integrations.shopify.webhooks import verify_webhook
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.product import Product
from app.workers.tasks.recovery import process_checkout_webhook, process_order_completed
from app.workers.tasks.shopify import sync_single_product

router = APIRouter()


async def _get_store_id_from_shop(shop_domain: str, db: AsyncSession) -> UUID | None:
    """Look up store_id from the shop domain header."""
    stmt = select(StoreIntegration.store_id).where(
        StoreIntegration.platform_domain == shop_domain,
        StoreIntegration.platform == PlatformType.SHOPIFY,
        StoreIntegration.status == IntegrationStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _verify_and_parse(request: Request) -> tuple[bytes, dict[str, Any]]:
    """Read body, verify HMAC, parse JSON."""
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not verify_webhook(body, hmac_header, settings.shopify_client_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")

    return body, json.loads(body)


@router.post("/products-create")
async def products_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle product creation webhook."""
    _, data = await _verify_and_parse(request)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    store_id = await _get_store_id_from_shop(shop, db)

    if not store_id:
        return {"status": "ignored"}

    sync_single_product.delay(str(store_id), data)
    return {"status": "accepted"}


@router.post("/products-update")
async def products_update(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle product update webhook."""
    _, data = await _verify_and_parse(request)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    store_id = await _get_store_id_from_shop(shop, db)

    if not store_id:
        return {"status": "ignored"}

    sync_single_product.delay(str(store_id), data)
    return {"status": "accepted"}


@router.post("/products-delete")
async def products_delete(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle product deletion webhook."""
    _, data = await _verify_and_parse(request)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    store_id = await _get_store_id_from_shop(shop, db)

    if not store_id:
        return {"status": "ignored"}

    product_id = str(data.get("id", ""))
    stmt = delete(Product).where(
        Product.store_id == store_id,
        Product.platform_product_id == product_id,
    )
    await db.execute(stmt)
    await db.commit()

    return {"status": "deleted"}


# --- Cart Recovery Webhooks ---


@router.post("/checkouts-create")
async def checkouts_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle checkout creation webhook."""
    _, data = await _verify_and_parse(request)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    store_id = await _get_store_id_from_shop(shop, db)

    if not store_id:
        return {"status": "ignored"}

    process_checkout_webhook.delay(str(store_id), "create", data)
    return {"status": "accepted"}


@router.post("/checkouts-update")
async def checkouts_update(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle checkout update webhook."""
    _, data = await _verify_and_parse(request)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    store_id = await _get_store_id_from_shop(shop, db)

    if not store_id:
        return {"status": "ignored"}

    process_checkout_webhook.delay(str(store_id), "update", data)
    return {"status": "accepted"}


@router.post("/orders-create")
async def orders_create(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle order creation webhook (marks checkouts as completed)."""
    _, data = await _verify_and_parse(request)
    shop = request.headers.get("X-Shopify-Shop-Domain", "")
    store_id = await _get_store_id_from_shop(shop, db)

    if not store_id:
        return {"status": "ignored"}

    process_order_completed.delay(str(store_id), data)
    return {"status": "accepted"}

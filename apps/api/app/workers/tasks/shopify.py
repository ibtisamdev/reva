"""Celery tasks for Shopify product sync and embedding generation."""

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import async_session_maker
from app.core.encryption import decrypt_token
from app.integrations.shopify.client import ShopifyClient
from app.models.integration import IntegrationStatus, StoreIntegration
from app.models.product import Product
from app.services.embedding_service import get_embedding_service
from app.workers.celery_app import BaseTask, celery_app


def _strip_html(html: str | None) -> str:
    """Remove HTML tags from a string."""
    if not html:
        return ""
    return re.sub(r"<[^>]+>", "", html).strip()


def product_to_text(product: Product) -> str:
    """Convert a product model to searchable text for embedding."""
    parts = [f"Product: {product.title}"]

    description = _strip_html(product.description)
    if description:
        parts.append(f"Description: {description}")

    if product.variants:
        first_variant = product.variants[0] if product.variants else None
        if first_variant and isinstance(first_variant, dict):
            price = first_variant.get("price")
            if price:
                parts.append(f"Price: ${price}")

        non_default = [
            v.get("title", "") for v in product.variants
            if isinstance(v, dict) and v.get("title") not in (None, "", "Default Title")
        ]
        if non_default:
            parts.append(f"Available options: {', '.join(non_default)}")

    if product.tags:
        parts.append(f"Tags: {', '.join(product.tags)}")

    if product.vendor:
        parts.append(f"Vendor: {product.vendor}")

    if product.product_type:
        parts.append(f"Type: {product.product_type}")

    return "\n".join(parts)


def _map_shopify_product(store_id: UUID, data: dict[str, Any]) -> dict[str, Any]:
    """Map a Shopify product JSON to our Product model fields."""
    return {
        "store_id": store_id,
        "platform_product_id": str(data["id"]),
        "title": data.get("title", ""),
        "description": data.get("body_html"),
        "handle": data.get("handle", ""),
        "vendor": data.get("vendor"),
        "product_type": data.get("product_type"),
        "status": data.get("status", "active"),
        "tags": [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
        if isinstance(data.get("tags"), str)
        else data.get("tags", []),
        "variants": data.get("variants", []),
        "images": data.get("images", []),
        "synced_at": datetime.now(UTC),
    }


@celery_app.task(
    name="tasks.shopify.sync_products_full",
    base=BaseTask,
    bind=True,
)
def sync_products_full(self: BaseTask, store_id: str) -> dict[str, Any]:  # noqa: ARG001
    """Full product sync from Shopify."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_sync_products_full_async(UUID(store_id)))
    finally:
        loop.close()


UPSERT_BATCH_SIZE = 100


async def _sync_products_full_async(store_id: UUID) -> dict[str, Any]:
    """Async implementation of full product sync."""
    async with async_session_maker() as session:
        # Get integration
        stmt = select(StoreIntegration).where(StoreIntegration.store_id == store_id)
        result = await session.execute(stmt)
        integration = result.scalar_one_or_none()

        if not integration or integration.status != IntegrationStatus.ACTIVE:
            return {"store_id": str(store_id), "status": "skipped", "reason": "no active integration"}

        try:
            access_token = decrypt_token(integration.credentials.get("access_token", ""))
            client = ShopifyClient(integration.platform_domain, access_token)

            # Fetch all products
            shopify_products = await client.get_all_products()

            # Batch upsert products
            all_values = [_map_shopify_product(store_id, p) for p in shopify_products]
            for i in range(0, len(all_values), UPSERT_BATCH_SIZE):
                chunk = all_values[i : i + UPSERT_BATCH_SIZE]
                stmt_upsert = pg_insert(Product).values(chunk)
                stmt_upsert = stmt_upsert.on_conflict_do_update(
                    index_elements=["store_id", "platform_product_id"],
                    set_={
                        "title": stmt_upsert.excluded.title,
                        "description": stmt_upsert.excluded.description,
                        "handle": stmt_upsert.excluded.handle,
                        "vendor": stmt_upsert.excluded.vendor,
                        "product_type": stmt_upsert.excluded.product_type,
                        "status": stmt_upsert.excluded.status,
                        "tags": stmt_upsert.excluded.tags,
                        "variants": stmt_upsert.excluded.variants,
                        "images": stmt_upsert.excluded.images,
                        "synced_at": stmt_upsert.excluded.synced_at,
                    },
                )
                await session.execute(stmt_upsert)

            integration.last_synced_at = datetime.now(UTC)
            integration.sync_error = None
            await session.commit()
        except Exception as e:
            integration.sync_error = str(e)[:500]
            await session.commit()
            raise

    # Trigger embedding generation
    generate_product_embeddings.delay(str(store_id))

    return {
        "store_id": str(store_id),
        "products_synced": len(shopify_products),
        "status": "completed",
    }


@celery_app.task(
    name="tasks.shopify.generate_product_embeddings",
    base=BaseTask,
    bind=True,
)
def generate_product_embeddings(self: BaseTask, store_id: str) -> dict[str, Any]:  # noqa: ARG001
    """Generate embeddings for all products in a store."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate_product_embeddings_async(UUID(store_id)))
    finally:
        loop.close()


async def _generate_product_embeddings_async(store_id: UUID) -> dict[str, Any]:
    """Async implementation of product embedding generation."""
    embedding_service = get_embedding_service()

    async with async_session_maker() as session:
        stmt = select(Product).where(Product.store_id == store_id)
        result = await session.execute(stmt)
        products = list(result.scalars().all())

        if not products:
            return {"store_id": str(store_id), "status": "completed", "products_embedded": 0}

        texts = [product_to_text(p) for p in products]
        embeddings = await embedding_service.generate_embeddings_batch(texts)

        for product, embedding in zip(products, embeddings, strict=True):
            product.embedding = embedding

        await session.commit()

    return {
        "store_id": str(store_id),
        "status": "completed",
        "products_embedded": len(products),
    }


@celery_app.task(
    name="tasks.shopify.sync_single_product",
    base=BaseTask,
    bind=True,
)
def sync_single_product(self: BaseTask, store_id: str, shopify_product: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
    """Upsert a single product and generate its embedding."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            _sync_single_product_async(UUID(store_id), shopify_product)
        )
    finally:
        loop.close()


async def _sync_single_product_async(store_id: UUID, shopify_data: dict[str, Any]) -> dict[str, Any]:
    """Async implementation of single product sync."""
    embedding_service = get_embedding_service()

    async with async_session_maker() as session:
        values = _map_shopify_product(store_id, shopify_data)
        stmt = (
            pg_insert(Product)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["store_id", "platform_product_id"],
                set_={k: v for k, v in values.items() if k not in ("store_id", "platform_product_id")},
            )
            .returning(Product)
        )
        result = await session.execute(stmt)
        product = result.scalar_one()

        # Generate embedding
        text = product_to_text(product)
        embedding = await embedding_service.generate_embedding(text)
        product.embedding = embedding

        await session.commit()

    return {"store_id": str(store_id), "product_id": str(shopify_data["id"]), "status": "completed"}

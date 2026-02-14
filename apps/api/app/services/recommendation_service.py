"""Product recommendation service for similar, upsell, and cross-sell products."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import Float, cast, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.search import ProductSearchResult
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating product recommendations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedding_service = get_embedding_service()

    async def get_similar_products(
        self,
        product_id: UUID,
        store_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.35,
    ) -> list[ProductSearchResult]:
        """Find products similar to a given product using embedding cosine similarity.

        Args:
            product_id: Source product to find similar items for
            store_id: Scope to this store (multi-tenant)
            limit: Max number of similar products to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of similar products sorted by similarity score
        """
        # Get the source product's embedding
        source = await self._get_product(product_id, store_id)
        if not source or source.embedding is None:
            return []

        distance_expr = Product.embedding.cosine_distance(source.embedding)
        max_distance = 1 - min_similarity

        stmt = (
            select(
                Product,
                (1 - distance_expr).label("similarity"),
            )
            .where(
                Product.store_id == store_id,
                Product.id != product_id,
                Product.status == "active",
                Product.embedding.isnot(None),
                distance_expr <= max_distance,
            )
            .order_by(distance_expr)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [self._to_search_result(row.Product, row.similarity) for row in rows]

    async def get_upsell_products(
        self,
        product_id: UUID,
        store_id: UUID,
        limit: int = 3,
    ) -> list[ProductSearchResult]:
        """Find upsell products: same category/vendor, 10-30% higher price.

        Args:
            product_id: Source product
            store_id: Store scope
            limit: Max results

        Returns:
            List of upsell product candidates
        """
        source = await self._get_product(product_id, store_id)
        if not source:
            return []

        source_price = self._extract_price(source)
        if source_price is None:
            return []

        # Upsell: 10-30% higher price
        price_min = source_price * 1.10
        price_max = source_price * 1.30

        price_expr = cast(Product.variants[0]["price"].astext, Float)

        conditions = [
            Product.store_id == store_id,
            Product.id != product_id,
            Product.status == "active",
            price_expr >= price_min,
            price_expr <= price_max,
        ]

        # Prefer same category or vendor
        if source.product_type:
            conditions.append(Product.product_type == source.product_type)
        elif source.vendor:
            conditions.append(Product.vendor == source.vendor)

        stmt = select(Product).where(*conditions).order_by(price_expr).limit(limit)

        result = await self.db.execute(stmt)
        products = list(result.scalars().all())

        return [self._to_search_result(p, 0.0) for p in products]

    async def get_cross_sell_products(
        self,
        product_id: UUID,
        store_id: UUID,
        limit: int = 3,
    ) -> list[ProductSearchResult]:
        """Find cross-sell products: overlapping tags, different product type.

        Args:
            product_id: Source product
            store_id: Store scope
            limit: Max results

        Returns:
            List of cross-sell product candidates
        """
        source = await self._get_product(product_id, store_id)
        if not source or not source.tags:
            return []

        conditions = [
            Product.store_id == store_id,
            Product.id != product_id,
            Product.status == "active",
            Product.tags.overlap(source.tags),
        ]

        # Different product type for cross-sell
        if source.product_type:
            conditions.append(not_(Product.product_type == source.product_type))

        stmt = select(Product).where(*conditions).limit(limit)

        result = await self.db.execute(stmt)
        products = list(result.scalars().all())

        return [self._to_search_result(p, 0.0) for p in products]

    async def compare_products(
        self,
        product_ids: list[UUID],
        store_id: UUID,
    ) -> dict[str, Any]:
        """Compare multiple products side by side.

        Args:
            product_ids: List of product IDs to compare
            store_id: Store scope

        Returns:
            Dict with comparison data
        """
        stmt = select(Product).where(
            Product.store_id == store_id,
            Product.id.in_(product_ids),
        )
        result = await self.db.execute(stmt)
        products = list(result.scalars().all())

        if not products:
            return {"error": "No products found", "products": []}

        comparison = []
        for p in products:
            price = self._extract_price(p)
            variants_info = []
            in_stock = False
            if p.variants:
                for v in p.variants:
                    if isinstance(v, dict):
                        qty = v.get("inventory_quantity", 0) or 0
                        if qty > 0:
                            in_stock = True
                        variants_info.append(
                            {
                                "title": v.get("title", "Default"),
                                "price": v.get("price"),
                                "available": qty > 0,
                            }
                        )

            comparison.append(
                {
                    "product_id": str(p.id),
                    "title": p.title,
                    "description": (p.description or "")[:200],
                    "price": f"{price:.2f}" if price else None,
                    "vendor": p.vendor,
                    "product_type": p.product_type,
                    "tags": p.tags or [],
                    "in_stock": in_stock,
                    "variants": variants_info,
                }
            )

        return {"products": comparison, "total": len(comparison)}

    async def _get_product(self, product_id: UUID, store_id: UUID) -> Product | None:
        """Fetch a product by ID, scoped to store."""
        stmt = select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _extract_price(product: Product) -> float | None:
        """Extract price from the first variant."""
        if not product.variants or not isinstance(product.variants, list):
            return None
        for v in product.variants:
            if isinstance(v, dict) and v.get("price"):
                try:
                    return float(v["price"])
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _to_search_result(product: Product, score: float) -> ProductSearchResult:
        """Convert a Product model to a ProductSearchResult."""
        price = None
        in_stock = False
        if product.variants and isinstance(product.variants, list):
            for v in product.variants:
                if isinstance(v, dict):
                    if price is None:
                        price = v.get("price")
                    qty = v.get("inventory_quantity", 0)
                    if isinstance(qty, int) and qty > 0:
                        in_stock = True

        image_url = None
        if product.images and isinstance(product.images, list) and product.images:
            first_img = product.images[0]
            if isinstance(first_img, dict):
                image_url = first_img.get("src")

        return ProductSearchResult(
            product_id=str(product.id),
            title=product.title,
            description=(product.description or "")[:300] if product.description else None,
            price=price,
            vendor=product.vendor,
            product_type=product.product_type,
            tags=product.tags or [],
            in_stock=in_stock,
            image_url=image_url,
            handle=product.handle,
            score=score,
        )

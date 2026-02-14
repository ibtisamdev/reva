"""Hybrid search service combining vector similarity and full-text search."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import Float, cast, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.search import ProductFilters, ProductSearchResult
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

# Reciprocal Rank Fusion constant (standard value from the literature)
RRF_K = 60


class SearchService:
    """Hybrid product search combining vector similarity and full-text search."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedding_service = get_embedding_service()

    async def hybrid_search(
        self,
        query: str,
        store_id: UUID,
        filters: ProductFilters | None = None,
        limit: int = 10,
        min_similarity: float = 0.35,
    ) -> list[ProductSearchResult]:
        """Search products using Reciprocal Rank Fusion of vector + full-text results.

        Args:
            query: Natural language search query
            store_id: Scope to this store (multi-tenant)
            filters: Optional product filters (price, category, stock, etc.)
            limit: Max results to return

        Returns:
            List of ProductSearchResult sorted by combined relevance
        """
        # Run both search methods
        vector_results = await self._vector_search(
            query, store_id, filters, limit=limit * 2, min_similarity=min_similarity
        )
        fulltext_results = await self._fulltext_search(query, store_id, filters, limit=limit * 2)

        # Combine via RRF
        combined = self._reciprocal_rank_fusion(vector_results, fulltext_results)

        return combined[:limit]

    async def _vector_search(
        self,
        query: str,
        store_id: UUID,
        filters: ProductFilters | None = None,
        limit: int = 20,
        min_similarity: float = 0.35,
    ) -> list[ProductSearchResult]:
        """Search products by embedding cosine similarity."""
        try:
            query_embedding = await self.embedding_service.generate_embedding(query)
        except Exception:
            logger.exception("Failed to generate embedding for search query")
            return []

        distance_expr = Product.embedding.cosine_distance(query_embedding)
        max_distance = 1 - min_similarity

        stmt = (
            select(
                Product,
                (1 - distance_expr).label("similarity"),
            )
            .where(
                Product.store_id == store_id,
                Product.status == "active",
                Product.embedding.isnot(None),
                distance_expr <= max_distance,
            )
            .order_by(distance_expr)
            .limit(limit)
        )

        stmt = self._apply_filters(stmt, filters)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [self._product_to_search_result(row.Product, row.similarity) for row in rows]

    async def _fulltext_search(
        self,
        query: str,
        store_id: UUID,
        filters: ProductFilters | None = None,
        limit: int = 20,
    ) -> list[ProductSearchResult]:
        """Search products using PostgreSQL full-text search."""
        # Build the tsvector expression from title + description + tags
        regconfig = text("'english'::regconfig")
        tsv = func.to_tsvector(
            regconfig,
            func.coalesce(Product.title, literal(""))
            + literal(" ")
            + func.coalesce(Product.description, literal(""))
            + literal(" ")
            + func.coalesce(func.array_to_string(Product.tags, literal(" ")), literal("")),
        )

        # Parse query into tsquery — use plainto_tsquery for robustness with user input
        tsq = func.plainto_tsquery(regconfig, query)

        rank = func.ts_rank(tsv, tsq)

        stmt = (
            select(
                Product,
                rank.label("rank"),
            )
            .where(
                Product.store_id == store_id,
                Product.status == "active",
                tsv.op("@@")(tsq),
            )
            .order_by(rank.desc())
            .limit(limit)
        )

        stmt = self._apply_filters(stmt, filters)

        result = await self.db.execute(stmt)
        rows = result.all()

        return [self._product_to_search_result(row.Product, float(row.rank)) for row in rows]

    def _apply_filters(self, stmt: Any, filters: ProductFilters | None) -> Any:
        """Apply product filters to a SQLAlchemy select statement."""
        if not filters:
            return stmt

        if filters.price_min is not None or filters.price_max is not None:
            # Filter on the first variant's price (JSONB path)
            # variants is a JSONB array, extract first element's price
            price_expr = cast(
                Product.variants[0]["price"].astext,
                Float,
            )

            if filters.price_min is not None:
                stmt = stmt.where(price_expr >= filters.price_min)
            if filters.price_max is not None:
                stmt = stmt.where(price_expr <= filters.price_max)

        if filters.categories:
            # product_type matches any of the categories (case-insensitive)
            lower_cats = [c.lower() for c in filters.categories]
            stmt = stmt.where(func.lower(Product.product_type).in_(lower_cats))

        if filters.tags:
            # Product tags array overlap with filter tags
            stmt = stmt.where(Product.tags.overlap(filters.tags))

        if filters.vendors:
            lower_vendors = [v.lower() for v in filters.vendors]
            stmt = stmt.where(func.lower(Product.vendor).in_(lower_vendors))

        if filters.in_stock_only:
            # Check that at least one variant has inventory_quantity > 0
            # Using raw SQL for JSONB array element check
            stmt = stmt.where(
                text(
                    "EXISTS (SELECT 1 FROM jsonb_array_elements(products.variants) v "
                    "WHERE (v->>'inventory_quantity')::int > 0)"
                )
            )

        return stmt

    def _reciprocal_rank_fusion(
        self,
        vector_results: list[ProductSearchResult],
        fulltext_results: list[ProductSearchResult],
    ) -> list[ProductSearchResult]:
        """Combine two ranked lists using Reciprocal Rank Fusion (RRF)."""
        scores: dict[str, float] = {}
        result_map: dict[str, ProductSearchResult] = {}

        for rank, r in enumerate(vector_results):
            scores[r.product_id] = scores.get(r.product_id, 0) + 1.0 / (RRF_K + rank + 1)
            result_map[r.product_id] = r

        for rank, r in enumerate(fulltext_results):
            scores[r.product_id] = scores.get(r.product_id, 0) + 1.0 / (RRF_K + rank + 1)
            if r.product_id not in result_map:
                result_map[r.product_id] = r

        # Sort by RRF score descending
        sorted_ids = sorted(scores.keys(), key=lambda pid: scores[pid], reverse=True)

        results = []
        for pid in sorted_ids:
            r = result_map[pid]
            r.score = scores[pid]
            results.append(r)

        return results

    @staticmethod
    def _product_to_search_result(
        product: Product,
        score: float,
    ) -> ProductSearchResult:
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

    async def get_product_by_id(
        self,
        product_id: UUID,
        store_id: UUID,
    ) -> Product | None:
        """Fetch a single product by ID, scoped to store."""
        stmt = select(Product).where(
            Product.id == product_id,
            Product.store_id == store_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

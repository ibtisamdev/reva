"""RAG retrieval service using pgvector for semantic search."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeArticle, KnowledgeChunk
from app.models.product import Product
from app.services.embedding_service import get_embedding_service


@dataclass
class RetrievedChunk:
    """A chunk retrieved from vector search."""

    chunk_id: UUID
    article_id: UUID
    content: str
    chunk_index: int
    similarity: float
    # Article metadata
    article_title: str
    article_url: str | None


@dataclass
class RetrievedProduct:
    """A product retrieved from vector search."""

    product_id: UUID
    title: str
    description: str | None
    price: str | None
    similarity: float


class RetrievalService:
    """Service for RAG retrieval using vector similarity search."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedding_service = get_embedding_service()

    async def retrieve_context(
        self,
        query: str,
        store_id: UUID,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks for a query.

        Uses pgvector's cosine distance operator for semantic similarity search.

        Args:
            query: The user's question
            store_id: Filter to this store only (multi-tenant security)
            top_k: Maximum number of chunks to return
            threshold: Minimum similarity score (0-1, higher = more similar)

        Returns:
            List of retrieved chunks sorted by relevance (highest first)
        """
        # Generate embedding for the query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # pgvector cosine distance: 1 - cosine_similarity
        # So similarity = 1 - distance
        # We want chunks where similarity >= threshold
        # Which means distance <= 1 - threshold
        max_distance = 1 - threshold

        # Build the vector search query using SQLAlchemy ORM with pgvector's
        # native cosine_distance() method - this avoids the ::vector cast syntax
        # that conflicts with SQLAlchemy's :param binding in raw SQL
        stmt = (
            select(
                KnowledgeChunk.id.label("chunk_id"),
                KnowledgeChunk.article_id,
                KnowledgeChunk.content,
                KnowledgeChunk.chunk_index,
                (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding)).label("similarity"),
                KnowledgeArticle.title.label("article_title"),
                KnowledgeArticle.source_url.label("article_url"),
            )
            .join(KnowledgeArticle, KnowledgeChunk.article_id == KnowledgeArticle.id)
            .where(
                KnowledgeArticle.store_id == store_id,
                KnowledgeChunk.embedding.isnot(None),
                KnowledgeChunk.embedding.cosine_distance(query_embedding) <= max_distance,
            )
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        return [
            RetrievedChunk(
                chunk_id=row.chunk_id,
                article_id=row.article_id,
                content=row.content,
                chunk_index=row.chunk_index,
                similarity=row.similarity,
                article_title=row.article_title,
                article_url=row.article_url,
            )
            for row in rows
        ]

    async def retrieve_by_article(
        self,
        query: str,
        article_id: UUID,
        store_id: UUID,
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant chunks from a specific article.

        Useful when user is on a specific page/product and we want to
        prioritize content from that context.

        Args:
            query: The user's question
            article_id: Limit search to this article
            store_id: The store ID (for multi-tenant security)
            top_k: Maximum number of chunks to return

        Returns:
            List of retrieved chunks sorted by relevance
        """
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Use SQLAlchemy ORM with pgvector's native cosine_distance() method
        stmt = (
            select(
                KnowledgeChunk.id.label("chunk_id"),
                KnowledgeChunk.article_id,
                KnowledgeChunk.content,
                KnowledgeChunk.chunk_index,
                (1 - KnowledgeChunk.embedding.cosine_distance(query_embedding)).label("similarity"),
                KnowledgeArticle.title.label("article_title"),
                KnowledgeArticle.source_url.label("article_url"),
            )
            .join(KnowledgeArticle, KnowledgeChunk.article_id == KnowledgeArticle.id)
            .where(
                KnowledgeArticle.store_id == store_id,
                KnowledgeChunk.article_id == article_id,
                KnowledgeChunk.embedding.isnot(None),
            )
            .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        return [
            RetrievedChunk(
                chunk_id=row.chunk_id,
                article_id=row.article_id,
                content=row.content,
                chunk_index=row.chunk_index,
                similarity=row.similarity,
                article_title=row.article_title,
                article_url=row.article_url,
            )
            for row in rows
        ]

    async def retrieve_products(
        self,
        query: str,
        store_id: UUID,
        top_k: int = 3,
        threshold: float = 0.5,
    ) -> list[RetrievedProduct]:
        """Retrieve relevant products for a query using vector similarity.

        Args:
            query: The user's question
            store_id: Filter to this store only
            top_k: Maximum number of products to return
            threshold: Minimum similarity score

        Returns:
            List of retrieved products sorted by relevance
        """
        query_embedding = await self.embedding_service.generate_embedding(query)
        max_distance = 1 - threshold

        stmt = (
            select(
                Product.id.label("product_id"),
                Product.title,
                Product.description,
                Product.variants,
                (1 - Product.embedding.cosine_distance(query_embedding)).label("similarity"),
            )
            .where(
                Product.store_id == store_id,
                Product.embedding.isnot(None),
                Product.embedding.cosine_distance(query_embedding) <= max_distance,
            )
            .order_by(Product.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        result = await self.db.execute(stmt)
        rows = result.fetchall()

        products: list[RetrievedProduct] = []
        for row in rows:
            price = None
            if row.variants and isinstance(row.variants, list) and row.variants:
                first = row.variants[0]
                if isinstance(first, dict):
                    price = first.get("price")

            products.append(
                RetrievedProduct(
                    product_id=row.product_id,
                    title=row.title,
                    description=row.description,
                    price=price,
                    similarity=row.similarity,
                )
            )
        return products

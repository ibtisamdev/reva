"""RAG retrieval service using pgvector for semantic search."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
        threshold: float = 0.7,
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

        # Build the vector search query with cosine distance
        # Using raw SQL for pgvector operators
        sql = text("""
            SELECT
                kc.id as chunk_id,
                kc.article_id,
                kc.content,
                kc.chunk_index,
                1 - (kc.embedding <=> :query_embedding::vector) as similarity,
                ka.title as article_title,
                ka.source_url as article_url
            FROM knowledge_chunks kc
            JOIN knowledge_articles ka ON kc.article_id = ka.id
            WHERE ka.store_id = :store_id
                AND kc.embedding IS NOT NULL
                AND (kc.embedding <=> :query_embedding::vector) <= :max_distance
            ORDER BY kc.embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = await self.db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "store_id": str(store_id),
                "max_distance": max_distance,
                "top_k": top_k,
            },
        )

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

        sql = text("""
            SELECT
                kc.id as chunk_id,
                kc.article_id,
                kc.content,
                kc.chunk_index,
                1 - (kc.embedding <=> :query_embedding::vector) as similarity,
                ka.title as article_title,
                ka.source_url as article_url
            FROM knowledge_chunks kc
            JOIN knowledge_articles ka ON kc.article_id = ka.id
            WHERE ka.store_id = :store_id
                AND kc.article_id = :article_id
                AND kc.embedding IS NOT NULL
            ORDER BY kc.embedding <=> :query_embedding::vector
            LIMIT :top_k
        """)

        result = await self.db.execute(
            sql,
            {
                "query_embedding": str(query_embedding),
                "store_id": str(store_id),
                "article_id": str(article_id),
                "top_k": top_k,
            },
        )

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

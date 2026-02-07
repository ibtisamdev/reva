"""Knowledge management service for articles and chunks."""

import hashlib
import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import ContentType, KnowledgeArticle, KnowledgeChunk
from app.schemas.knowledge import (
    KnowledgeArticleCreate,
    KnowledgeArticleUpdate,
    TextIngestionRequest,
)
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service for managing knowledge articles and chunks."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedding_service = get_embedding_service()

    async def check_duplicate(self, store_id: UUID, content_hash: str) -> KnowledgeArticle | None:
        """Check if an article with the same content hash exists for this store."""
        query = select(KnowledgeArticle).where(
            KnowledgeArticle.store_id == store_id,
            KnowledgeArticle.content_hash == content_hash,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # === Article CRUD ===

    async def create_article(
        self,
        store_id: UUID,
        data: KnowledgeArticleCreate,
    ) -> KnowledgeArticle:
        """Create a new knowledge article without processing.

        Args:
            store_id: The store to associate the article with
            data: Article creation data

        Returns:
            The created article
        """
        article = KnowledgeArticle(
            store_id=store_id,
            title=data.title,
            content=data.content,
            content_type=data.content_type,
            source_url=data.source_url,
        )
        self.db.add(article)
        await self.db.flush()
        return article

    async def get_article(
        self,
        article_id: UUID,
        store_id: UUID,
    ) -> KnowledgeArticle | None:
        """Get article by ID, scoped to store.

        Args:
            article_id: The article ID
            store_id: The store ID (for multi-tenant security)

        Returns:
            The article if found, None otherwise
        """
        query = (
            select(KnowledgeArticle)
            .where(
                KnowledgeArticle.id == article_id,
                KnowledgeArticle.store_id == store_id,
            )
            .options(selectinload(KnowledgeArticle.chunks))
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_articles(
        self,
        store_id: UUID,
        content_type: ContentType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[KnowledgeArticle], int]:
        """List articles for a store with pagination.

        Args:
            store_id: The store ID
            content_type: Optional filter by content type
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (articles, total_count)
        """
        # Base query
        base_query = select(KnowledgeArticle).where(
            KnowledgeArticle.store_id == store_id,
        )

        if content_type:
            base_query = base_query.where(KnowledgeArticle.content_type == content_type)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await self.db.scalar(count_query) or 0

        # Get paginated results with chunks loaded
        query = (
            base_query.options(selectinload(KnowledgeArticle.chunks))
            .order_by(KnowledgeArticle.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(query)
        articles = list(result.scalars().all())

        return articles, total

    async def update_article(
        self,
        article_id: UUID,
        store_id: UUID,
        data: KnowledgeArticleUpdate,
    ) -> KnowledgeArticle | None:
        """Update an article.

        Args:
            article_id: The article ID
            store_id: The store ID (for multi-tenant security)
            data: Update data

        Returns:
            The updated article if found, None otherwise
        """
        article = await self.get_article(article_id, store_id)
        if not article:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(article, field, value)

        await self.db.flush()
        return article

    async def delete_article(
        self,
        article_id: UUID,
        store_id: UUID,
    ) -> bool:
        """Delete an article and its chunks.

        Args:
            article_id: The article ID
            store_id: The store ID (for multi-tenant security)

        Returns:
            True if deleted, False if not found
        """
        article = await self.get_article(article_id, store_id)
        if not article:
            return False

        await self.db.delete(article)
        await self.db.flush()
        return True

    # === Ingestion ===

    async def ingest_text(
        self,
        store_id: UUID,
        data: TextIngestionRequest,
        process_sync: bool = True,
    ) -> KnowledgeArticle:
        """Ingest text content: create article, chunk, and embed.

        Args:
            store_id: The store to associate content with
            data: Ingestion request data
            process_sync: If True, process embeddings synchronously.
                         If False, caller should trigger async task.

        Returns:
            The created article with chunks
        """
        # Create article
        content_hash = hashlib.sha256(data.content.encode()).hexdigest()
        article = KnowledgeArticle(
            store_id=store_id,
            title=data.title,
            content=data.content,
            content_type=data.content_type,
            content_hash=content_hash,
            source_url=str(data.source_url) if data.source_url else None,
        )
        self.db.add(article)
        await self.db.flush()

        # Chunk the content
        chunks_data = self.embedding_service.chunk_text(data.content)

        # Create chunk records
        chunks: list[KnowledgeChunk] = []
        for idx, (chunk_text, token_count) in enumerate(chunks_data):
            chunk = KnowledgeChunk(
                article_id=article.id,
                content=chunk_text,
                chunk_index=idx,
                token_count=token_count,
            )
            self.db.add(chunk)
            chunks.append(chunk)

        await self.db.flush()

        # Generate embeddings synchronously if requested
        if process_sync:
            try:
                texts = [chunk.content for chunk in chunks]
                embeddings = await self.embedding_service.generate_embeddings_batch(texts)
                for chunk, embedding in zip(chunks, embeddings, strict=True):
                    chunk.embedding = embedding
                await self.db.flush()
                logger.info(
                    "Generated embeddings for %d chunks of article '%s'", len(chunks), data.title
                )
            except Exception:
                logger.exception("Failed to generate embeddings for article '%s'", data.title)

        # Refresh to get the chunks relationship loaded
        await self.db.refresh(article, ["chunks"])

        return article

    async def process_article_embeddings(
        self,
        article_id: UUID,
    ) -> int:
        """Generate embeddings for an article's chunks.

        Used by Celery task for async processing.

        Args:
            article_id: The article ID

        Returns:
            Number of chunks processed
        """
        query = (
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.article_id == article_id,
                KnowledgeChunk.embedding.is_(None),
            )
            .order_by(KnowledgeChunk.chunk_index)
        )

        result = await self.db.execute(query)
        chunks = list(result.scalars().all())

        if not chunks:
            return 0

        # Batch generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_service.generate_embeddings_batch(texts)

        for chunk, embedding in zip(chunks, embeddings, strict=True):
            chunk.embedding = embedding

        await self.db.flush()
        return len(chunks)

    async def get_article_chunks_count(
        self,
        article_id: UUID,
    ) -> int:
        """Get the number of chunks for an article.

        Args:
            article_id: The article ID

        Returns:
            Number of chunks
        """
        query = select(func.count()).where(KnowledgeChunk.article_id == article_id)
        return await self.db.scalar(query) or 0

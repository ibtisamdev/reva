"""Tests for the Celery embedding task.

Tests the async function _process_article_embeddings_async directly
to avoid needing a Celery worker.
"""

from typing import Any, Callable
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.workers.tasks.embedding import _process_article_embeddings_async


class TestProcessArticleEmbeddings:
    """Tests for _process_article_embeddings_async()."""

    @pytest.mark.asyncio
    async def test_fills_chunks_without_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Chunks without embeddings are filled."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
        )

        # Create chunks without embeddings
        await knowledge_chunk_factory(
            article_id=article.id,
            content="First chunk.",
            chunk_index=0,
            embedding=None,
        )
        await knowledge_chunk_factory(
            article_id=article.id,
            content="Second chunk.",
            chunk_index=1,
            embedding=None,
        )

        result = await _process_article_embeddings_async(article.id)

        assert result["article_id"] == str(article.id)
        assert result["chunks_processed"] == 2
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_returns_correct_count(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Returns correct count of processed chunks."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
        )

        # Create 5 chunks without embeddings
        for i in range(5):
            await knowledge_chunk_factory(
                article_id=article.id,
                content=f"Chunk {i} content.",
                chunk_index=i,
                embedding=None,
            )

        result = await _process_article_embeddings_async(article.id)

        assert result["chunks_processed"] == 5

    @pytest.mark.asyncio
    async def test_skips_chunks_with_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Chunks that already have embeddings are skipped."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
        )

        # One chunk with embedding, one without
        await knowledge_chunk_factory(
            article_id=article.id,
            content="Has embedding.",
            chunk_index=0,
            embedding=mock_embedding,
        )
        await knowledge_chunk_factory(
            article_id=article.id,
            content="No embedding.",
            chunk_index=1,
            embedding=None,
        )

        result = await _process_article_embeddings_async(article.id)

        # Should only process the one without embedding
        assert result["chunks_processed"] == 1

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_chunks_to_process(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Returns 0 when all chunks already have embeddings."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
        )

        # All chunks have embeddings
        await knowledge_chunk_factory(
            article_id=article.id,
            content="Chunk with embedding.",
            chunk_index=0,
            embedding=mock_embedding,
        )

        result = await _process_article_embeddings_async(article.id)

        assert result["chunks_processed"] == 0
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_handles_article_with_no_chunks(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Article with no chunks returns 0 processed."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Empty Article",
            num_chunks=0,
        )

        result = await _process_article_embeddings_async(article.id)

        assert result["chunks_processed"] == 0
        assert result["status"] == "completed"

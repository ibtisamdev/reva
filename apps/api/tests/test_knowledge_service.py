"""Tests for KnowledgeService business logic.

Tests article/chunk CRUD, ingestion pipeline, and embedding generation.
Uses mocked embedding service to avoid OpenAI API calls.
"""

import hashlib
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import ContentType, KnowledgeArticle, KnowledgeChunk
from app.models.store import Store
from app.schemas.knowledge import TextIngestionRequest
from app.services.knowledge_service import KnowledgeService


class TestIngestText:
    """Tests for KnowledgeService.ingest_text()."""

    @pytest.mark.asyncio
    async def test_creates_article_with_correct_fields(
        self,
        db_session: AsyncSession,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Article is created with all provided fields."""
        service = KnowledgeService(db_session)

        data = TextIngestionRequest(
            title="Shipping Policy",
            content="We ship worldwide within 5-7 business days.",
            content_type=ContentType.POLICY,
            source_url="https://example.com/shipping",
        )

        article, embedding_failed = await service.ingest_text(store.id, data, process_sync=True)
        await db_session.commit()

        assert article.title == "Shipping Policy"
        assert article.content == "We ship worldwide within 5-7 business days."
        assert article.content_type == ContentType.POLICY
        assert article.source_url == "https://example.com/shipping"
        assert article.store_id == store.id
        assert embedding_failed is False

    @pytest.mark.asyncio
    async def test_creates_chunks_from_content(
        self,
        db_session: AsyncSession,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Content is chunked and chunks are created."""
        service = KnowledgeService(db_session)

        # Short content that fits in one chunk
        data = TextIngestionRequest(
            title="FAQ",
            content="What is your return policy? You can return items within 30 days.",
            content_type=ContentType.FAQ,
        )

        article, _ = await service.ingest_text(store.id, data, process_sync=True)
        await db_session.commit()

        assert article.chunks is not None
        assert len(article.chunks) >= 1

        # Check first chunk
        first_chunk = article.chunks[0]
        assert first_chunk.chunk_index == 0
        assert first_chunk.content  # Not empty
        assert first_chunk.token_count > 0

    @pytest.mark.asyncio
    async def test_computes_content_hash(
        self,
        db_session: AsyncSession,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Content hash is computed as SHA-256."""
        service = KnowledgeService(db_session)

        content = "This is the content to hash."
        expected_hash = hashlib.sha256(content.encode()).hexdigest()

        data = TextIngestionRequest(
            title="Test",
            content=content,
            content_type=ContentType.FAQ,
        )

        article, _ = await service.ingest_text(store.id, data, process_sync=True)
        await db_session.commit()

        assert article.content_hash == expected_hash

    @pytest.mark.asyncio
    async def test_sync_generates_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """With process_sync=True, chunks have embeddings."""
        service = KnowledgeService(db_session)

        data = TextIngestionRequest(
            title="Test",
            content="Content that will be embedded.",
            content_type=ContentType.FAQ,
        )

        article, embedding_failed = await service.ingest_text(store.id, data, process_sync=True)
        await db_session.commit()

        assert embedding_failed is False

        # All chunks should have embeddings
        for chunk in article.chunks:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == len(mock_embedding)

    @pytest.mark.asyncio
    async def test_async_skips_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """With process_sync=False, chunks have no embeddings."""
        service = KnowledgeService(db_session)

        data = TextIngestionRequest(
            title="Test",
            content="Content without embeddings.",
            content_type=ContentType.FAQ,
        )

        article, embedding_failed = await service.ingest_text(store.id, data, process_sync=False)
        await db_session.commit()

        # embedding_failed is False because we didn't attempt sync processing
        assert embedding_failed is False

        # Chunks should exist but without embeddings
        assert len(article.chunks) >= 1
        for chunk in article.chunks:
            assert chunk.embedding is None

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_flag(
        self,
        db_session: AsyncSession,
        store: Store,
        _mock_knowledge_embedding_service_failure: MagicMock,
    ) -> None:
        """When embedding generation fails, article is created and failure flag is set.

        The article is created with chunks but no embeddings.
        The embedding_failed flag is True so the caller can report the error.
        """
        service = KnowledgeService(db_session)

        data = TextIngestionRequest(
            title="Will Fail Embedding",
            content="This content will fail embedding generation.",
            content_type=ContentType.FAQ,
        )

        # Should not raise - failure is caught and logged, flag is returned
        article, embedding_failed = await service.ingest_text(store.id, data, process_sync=True)
        await db_session.commit()

        # Article should still be created
        assert article.id is not None
        assert article.title == "Will Fail Embedding"

        # Failure flag should be True
        assert embedding_failed is True

        # Chunks should exist but without embeddings
        assert len(article.chunks) >= 1
        for chunk in article.chunks:
            assert chunk.embedding is None


class TestCheckDuplicate:
    """Tests for KnowledgeService.check_duplicate()."""

    @pytest.mark.asyncio
    async def test_finds_duplicate_by_hash(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Returns existing article when content hash matches."""
        content = "Unique content that will be duplicated."
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Create article with known hash
        existing = await knowledge_article_factory(
            store_id=store.id,
            title="Original",
            content=content,
            content_hash=content_hash,
        )

        service = KnowledgeService(db_session)
        duplicate = await service.check_duplicate(store.id, content_hash)

        assert duplicate is not None
        assert duplicate.id == existing.id

    @pytest.mark.asyncio
    async def test_returns_none_when_no_match(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Returns None when no matching hash exists."""
        service = KnowledgeService(db_session)

        result = await service.check_duplicate(store.id, "nonexistent-hash-value")

        assert result is None

    @pytest.mark.asyncio
    async def test_scoped_to_store(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Duplicate check is scoped to the specific store."""
        content = "Content that exists in other store."
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Create article in OTHER store
        await knowledge_article_factory(
            store_id=other_store.id,
            title="Other Store Article",
            content=content,
            content_hash=content_hash,
        )

        service = KnowledgeService(db_session)

        # Check in OUR store - should not find it
        result = await service.check_duplicate(store.id, content_hash)

        assert result is None


class TestProcessArticleEmbeddings:
    """Tests for KnowledgeService.process_article_embeddings()."""

    @pytest.mark.asyncio
    async def test_fills_missing_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        _mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Chunks without embeddings get filled."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
        )

        # Create chunks without embeddings
        chunk1 = await knowledge_chunk_factory(
            article_id=article.id,
            content="First chunk content.",
            chunk_index=0,
            embedding=None,
        )
        chunk2 = await knowledge_chunk_factory(
            article_id=article.id,
            content="Second chunk content.",
            chunk_index=1,
            embedding=None,
        )

        service = KnowledgeService(db_session)
        count = await service.process_article_embeddings(article.id)
        await db_session.commit()

        assert count == 2

        # Refresh and check embeddings
        await db_session.refresh(chunk1)
        await db_session.refresh(chunk2)

        # Embeddings are stored as pgvector/numpy arrays, check they're not None
        # and have the correct length
        assert chunk1.embedding is not None
        assert chunk2.embedding is not None
        assert len(chunk1.embedding) == len(mock_embedding)
        assert len(chunk2.embedding) == len(mock_embedding)

    @pytest.mark.asyncio
    async def test_skips_existing_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        _mock_knowledge_embedding_service: MagicMock,
        mock_embedding: list[float],
    ) -> None:
        """Chunks that already have embeddings are not re-processed."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
        )

        # Create one chunk with embedding, one without
        await knowledge_chunk_factory(
            article_id=article.id,
            content="Has embedding.",
            chunk_index=0,
            embedding=mock_embedding,  # Already has embedding
        )
        await knowledge_chunk_factory(
            article_id=article.id,
            content="No embedding yet.",
            chunk_index=1,
            embedding=None,
        )

        service = KnowledgeService(db_session)
        count = await service.process_article_embeddings(article.id)

        # Should only process the one without embedding
        assert count == 1

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_chunks(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Returns 0 when article has no chunks."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Empty Article",
            num_chunks=0,
        )

        service = KnowledgeService(db_session)
        count = await service.process_article_embeddings(article.id)

        assert count == 0


class TestListArticles:
    """Tests for KnowledgeService.list_articles()."""

    @pytest.mark.asyncio
    async def test_returns_paginated_results(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Pagination works correctly."""
        # Create 5 articles
        for i in range(5):
            await knowledge_article_factory(
                store_id=store.id,
                title=f"Article {i}",
            )

        service = KnowledgeService(db_session)

        # Get first page
        articles, total = await service.list_articles(store.id, limit=2, offset=0)

        assert total == 5
        assert len(articles) == 2

        # Get second page
        articles2, total2 = await service.list_articles(store.id, limit=2, offset=2)

        assert total2 == 5
        assert len(articles2) == 2

    @pytest.mark.asyncio
    async def test_filters_by_content_type(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Content type filter works."""
        await knowledge_article_factory(
            store_id=store.id,
            title="FAQ 1",
            content_type=ContentType.FAQ,
        )
        await knowledge_article_factory(
            store_id=store.id,
            title="Policy 1",
            content_type=ContentType.POLICY,
        )
        await knowledge_article_factory(
            store_id=store.id,
            title="FAQ 2",
            content_type=ContentType.FAQ,
        )

        service = KnowledgeService(db_session)

        # Filter FAQs only
        articles, total = await service.list_articles(store.id, content_type=ContentType.FAQ)

        assert total == 2
        assert all(a.content_type == ContentType.FAQ for a in articles)

    @pytest.mark.asyncio
    async def test_scoped_to_store(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Only returns articles from the specified store."""
        await knowledge_article_factory(store_id=store.id, title="Our Article")
        await knowledge_article_factory(store_id=other_store.id, title="Their Article")

        service = KnowledgeService(db_session)
        articles, total = await service.list_articles(store.id)

        assert total == 1
        assert articles[0].title == "Our Article"


class TestDeleteArticle:
    """Tests for KnowledgeService.delete_article()."""

    @pytest.mark.asyncio
    async def test_deletes_article_and_chunks(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Deleting article also deletes all its chunks."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="To Delete",
            num_chunks=3,
        )
        article_id = article.id

        service = KnowledgeService(db_session)
        result = await service.delete_article(article_id, store.id)
        await db_session.commit()

        assert result is True

        # Verify article is gone
        stmt = select(KnowledgeArticle).where(KnowledgeArticle.id == article_id)
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        # Verify chunks are gone
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.article_id == article_id)
        result = await db_session.execute(stmt)
        assert list(result.scalars().all()) == []

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(
        self,
        db_session: AsyncSession,
        store: Store,
    ) -> None:
        """Returns False when article doesn't exist."""
        import uuid

        service = KnowledgeService(db_session)
        result = await service.delete_article(uuid.uuid4(), store.id)

        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_delete_other_store_article(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Cannot delete an article belonging to another store."""
        article = await knowledge_article_factory(
            store_id=other_store.id,
            title="Other Store Article",
        )

        service = KnowledgeService(db_session)

        # Try to delete using OUR store_id
        result = await service.delete_article(article.id, store.id)

        assert result is False

        # Article should still exist
        stmt = select(KnowledgeArticle).where(KnowledgeArticle.id == article.id)
        db_result = await db_session.execute(stmt)
        assert db_result.scalar_one_or_none() is not None

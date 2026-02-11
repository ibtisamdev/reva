"""Unit tests for RetrievalService.

Tests vector similarity search with pgvector.
Embedding generation is mocked to control similarity matching.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.store import Store
from app.services.retrieval_service import RetrievalService


class TestRetrieveContext:
    """Tests for RetrievalService.retrieve_context()."""

    @pytest.mark.asyncio
    async def test_returns_matching_chunks(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Returns chunks with embeddings that match the query."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Store Hours FAQ",
            source_url="/pages/hours",
        )
        await knowledge_chunk_factory(
            article_id=article.id,
            content="Our store is open Monday through Friday, 9am to 5pm.",
            embedding=mock_embedding,
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            chunks = await service.retrieve_context(
                query="What are your hours?",
                store_id=store.id,
                top_k=5,
                threshold=0.5,
            )

        assert len(chunks) == 1
        assert chunks[0].article_title == "Store Hours FAQ"
        assert "9am to 5pm" in chunks[0].content

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_matches(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_embedding: list[float],
    ) -> None:
        """Returns empty list when no knowledge articles exist."""
        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            chunks = await service.retrieve_context(
                query="Random question",
                store_id=store.id,
            )

        assert chunks == []

    @pytest.mark.asyncio
    async def test_scoped_to_store_id(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Only returns chunks from the specified store (multi-tenancy)."""
        # Create article in OTHER store
        other_article = await knowledge_article_factory(
            store_id=other_store.id,
            title="Other Store Secret Info",
        )
        await knowledge_chunk_factory(
            article_id=other_article.id,
            content="This is confidential to the other store.",
            embedding=mock_embedding,
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            chunks = await service.retrieve_context(
                query="secret info",
                store_id=store.id,  # Query against OUR store
            )

        # Should NOT return other store's chunks
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_excludes_chunks_without_embeddings(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Chunks without embeddings are not returned."""
        article = await knowledge_article_factory(store_id=store.id, title="Test")
        await knowledge_chunk_factory(
            article_id=article.id,
            content="This chunk has no embedding.",
            embedding=None,  # No embedding!
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            chunks = await service.retrieve_context(
                query="test",
                store_id=store.id,
                threshold=0.0,  # Low threshold
            )

        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_respects_top_k_limit(
        self,
        db_session: AsyncSession,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
        knowledge_chunk_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Returns at most top_k results."""
        article = await knowledge_article_factory(store_id=store.id, title="Big Article")

        for i in range(10):
            await knowledge_chunk_factory(
                article_id=article.id,
                content=f"Chunk number {i} with some content.",
                chunk_index=i,
                embedding=mock_embedding,
            )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            chunks = await service.retrieve_context(
                query="chunk content",
                store_id=store.id,
                top_k=3,
                threshold=0.0,
            )

        assert len(chunks) == 3


class TestRetrieveProducts:
    """Tests for RetrievalService.retrieve_products()."""

    @pytest.mark.asyncio
    async def test_returns_matching_products(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Returns products with embeddings that match the query."""
        await product_factory(
            store_id=store.id,
            title="Widget Pro Max",
            description="The ultimate professional widget.",
            variants=[{"price": "149.99", "title": "Standard"}],
            embedding=mock_embedding,
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            products = await service.retrieve_products(
                query="professional widget",
                store_id=store.id,
            )

        assert len(products) == 1
        assert products[0].title == "Widget Pro Max"
        assert products[0].price == "149.99"

    @pytest.mark.asyncio
    async def test_scoped_to_store_id(
        self,
        db_session: AsyncSession,
        store: Store,
        other_store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Only returns products from the specified store."""
        await product_factory(
            store_id=other_store.id,
            title="Other Store Product",
            embedding=mock_embedding,
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            products = await service.retrieve_products(
                query="product",
                store_id=store.id,
            )

        assert len(products) == 0

    @pytest.mark.asyncio
    async def test_extracts_price_from_first_variant(
        self,
        db_session: AsyncSession,
        store: Store,
        product_factory: Callable[..., Any],
        mock_embedding: list[float],
    ) -> None:
        """Price is extracted from the first variant in the list."""
        await product_factory(
            store_id=store.id,
            title="Multi-Size Widget",
            variants=[
                {"price": "29.99", "title": "Small"},
                {"price": "49.99", "title": "Medium"},
                {"price": "79.99", "title": "Large"},
            ],
            embedding=mock_embedding,
        )

        with patch("app.services.retrieval_service.get_embedding_service") as mock_get:
            mock_svc = MagicMock()
            mock_svc.generate_embedding = AsyncMock(return_value=mock_embedding)
            mock_get.return_value = mock_svc

            service = RetrievalService(db_session)
            products = await service.retrieve_products(
                query="widget",
                store_id=store.id,
            )

        assert products[0].price == "29.99"  # First variant's price

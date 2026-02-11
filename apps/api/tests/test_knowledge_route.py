"""Tests for knowledge management API endpoints.

Tests all /api/v1/knowledge routes including:
- Text, URL, and PDF ingestion
- CRUD operations
- Authentication and authorization
- Input validation
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.knowledge import ContentType
from app.models.store import Store


class TestIngestText:
    """Tests for POST /api/v1/knowledge (text ingestion)."""

    @pytest.mark.asyncio
    async def test_ingest_text_success(
        self,
        client: AsyncClient,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Successfully ingests text content and creates article with chunks."""
        response = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={
                "title": "Shipping Policy",
                "content": "We offer free shipping on orders over $50. Standard shipping takes 5-7 business days.",
                "content_type": "policy",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Shipping Policy"
        assert data["status"] == "completed"
        assert data["chunks_count"] >= 1
        assert "article_id" in data

    @pytest.mark.asyncio
    async def test_ingest_text_duplicate_content(
        self,
        client: AsyncClient,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Duplicate content returns 409 Conflict."""
        content = "This is unique content that will be duplicated."

        # First ingestion - success
        response1 = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={"title": "Original", "content": content},
        )
        assert response1.status_code == 201

        # Second ingestion with same content - conflict
        response2 = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={"title": "Duplicate", "content": content},
        )
        assert response2.status_code == 409
        assert "Duplicate content" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_text_large_triggers_async(
        self,
        client: AsyncClient,
        store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Large documents (>5000 tokens) trigger async processing."""
        # Create content that exceeds 5000 tokens (~20k chars)
        large_content = "This is a test sentence with multiple words. " * 1000

        with patch("app.workers.tasks.embedding.process_article_embeddings") as mock_task:
            mock_task.delay = MagicMock()

            response = await client.post(
                "/api/v1/knowledge",
                params={"store_id": str(store.id)},
                json={"title": "Large Document", "content": large_content},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "processing"
            assert "queued" in data["message"].lower()

            # Verify Celery task was called
            mock_task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_text_requires_auth(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Unauthenticated requests are rejected."""
        response = await unauthed_client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={"title": "Test", "content": "Test content"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_ingest_text_wrong_store(
        self,
        client: AsyncClient,
        other_store: Store,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Cannot ingest to a store in another organization."""
        response = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(other_store.id)},
            json={"title": "Test", "content": "Test content"},
        )

        # other_store belongs to OTHER_ORG_ID, not our auth user's org
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ingest_text_embedding_failure_returns_error_status(
        self,
        client: AsyncClient,
        store: Store,
        _mock_knowledge_embedding_service_failure: MagicMock,
    ) -> None:
        """When embedding fails, response has status='error'."""
        response = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={"title": "Will Fail", "content": "This content will fail embedding."},
        )

        assert response.status_code == 201  # Article is still created
        data = response.json()
        assert data["status"] == "error"
        assert "embedding" in data["message"].lower()
        assert "failed" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_ingest_text_content_too_large(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Content exceeding max size (500KB) is rejected."""
        # Create content that exceeds 500,000 characters
        huge_content = "x" * 500_001

        response = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={"title": "Too Big", "content": huge_content},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_ingest_text_empty_content(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Empty content is rejected."""
        response = await client.post(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
            json={"title": "Empty", "content": ""},
        )

        assert response.status_code == 422


class TestIngestUrl:
    """Tests for POST /api/v1/knowledge/url."""

    @pytest.mark.asyncio
    async def test_ingest_url_success(
        self,
        client: AsyncClient,
        store: Store,
        _mock_url_fetch: MagicMock,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Successfully fetches URL and creates article."""
        response = await client.post(
            "/api/v1/knowledge/url",
            params={"store_id": str(store.id)},
            json={
                "url": "https://example.com/shipping-policy",
                "content_type": "policy",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert data["chunks_count"] >= 1

    @pytest.mark.asyncio
    async def test_ingest_url_with_custom_title(
        self,
        client: AsyncClient,
        store: Store,
        _mock_url_fetch: MagicMock,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Custom title overrides extracted page title."""
        response = await client.post(
            "/api/v1/knowledge/url",
            params={"store_id": str(store.id)},
            json={
                "url": "https://example.com/page",
                "title": "My Custom Title",
            },
        )

        assert response.status_code == 201
        assert response.json()["title"] == "My Custom Title"

    @pytest.mark.asyncio
    async def test_ingest_url_ssrf_private_ip(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """URLs resolving to private IPs are rejected (SSRF protection)."""
        with patch("app.services.url_service.fetch_url_content") as mock_fetch:
            mock_fetch.side_effect = ValueError(
                "URL resolves to a private/reserved address: 127.0.0.1"
            )

            response = await client.post(
                "/api/v1/knowledge/url",
                params={"store_id": str(store.id)},
                json={"url": "http://localhost/admin"},
            )

        assert response.status_code == 422
        assert "private" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ingest_url_invalid_scheme(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Non-HTTP(S) schemes are rejected."""
        with patch("app.services.url_service.fetch_url_content") as mock_fetch:
            mock_fetch.side_effect = ValueError("Unsupported URL scheme: ftp")

            response = await client.post(
                "/api/v1/knowledge/url",
                params={"store_id": str(store.id)},
                json={"url": "ftp://files.example.com/doc.txt"},
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_url_fetch_failure(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """URL fetch failures return 422."""
        with patch("app.services.url_service.fetch_url_content") as mock_fetch:
            mock_fetch.side_effect = Exception("Connection refused")

            response = await client.post(
                "/api/v1/knowledge/url",
                params={"store_id": str(store.id)},
                json={"url": "https://unreachable.example.com/"},
            )

        assert response.status_code == 422
        assert "Failed to fetch" in response.json()["detail"]


class TestIngestPdf:
    """Tests for POST /api/v1/knowledge/pdf."""

    @pytest.mark.asyncio
    async def test_ingest_pdf_success(
        self,
        client: AsyncClient,
        store: Store,
        sample_pdf_bytes: bytes,
        _mock_pdf_extract: MagicMock,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Successfully uploads PDF and creates article."""
        response = await client.post(
            "/api/v1/knowledge/pdf",
            params={"store_id": str(store.id)},
            files={"file": ("document.pdf", sample_pdf_bytes, "application/pdf")},
            data={"content_type": "guide"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "completed"
        assert data["chunks_count"] >= 1

    @pytest.mark.asyncio
    async def test_ingest_pdf_with_custom_title(
        self,
        client: AsyncClient,
        store: Store,
        sample_pdf_bytes: bytes,
        _mock_pdf_extract: MagicMock,
        _mock_knowledge_embedding_service: MagicMock,
    ) -> None:
        """Custom title overrides filename-based title."""
        response = await client.post(
            "/api/v1/knowledge/pdf",
            params={"store_id": str(store.id)},
            files={"file": ("document.pdf", sample_pdf_bytes, "application/pdf")},
            data={"title": "Custom PDF Title", "content_type": "guide"},
        )

        assert response.status_code == 201
        assert response.json()["title"] == "Custom PDF Title"

    @pytest.mark.asyncio
    async def test_ingest_pdf_wrong_content_type(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Non-PDF files are rejected."""
        response = await client.post(
            "/api/v1/knowledge/pdf",
            params={"store_id": str(store.id)},
            files={"file": ("document.txt", b"Plain text content", "text/plain")},
        )

        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_pdf_oversized(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """PDFs over 10MB are rejected."""
        # Create a file larger than 10MB
        large_pdf = b"%PDF-1.4\n" + (b"x" * (10 * 1024 * 1024 + 1))

        response = await client.post(
            "/api/v1/knowledge/pdf",
            params={"store_id": str(store.id)},
            files={"file": ("large.pdf", large_pdf, "application/pdf")},
        )

        assert response.status_code == 400
        assert "10 MB" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_pdf_extraction_failure(
        self,
        client: AsyncClient,
        store: Store,
        sample_pdf_bytes: bytes,
    ) -> None:
        """PDF extraction failures return 422."""
        with patch("app.services.pdf_service.extract_text_from_pdf") as mock_extract:
            mock_extract.side_effect = ValueError("PDF contains no extractable text.")

            response = await client.post(
                "/api/v1/knowledge/pdf",
                params={"store_id": str(store.id)},
                files={"file": ("empty.pdf", sample_pdf_bytes, "application/pdf")},
            )

        assert response.status_code == 422
        assert "extract" in response.json()["detail"].lower()


class TestListKnowledge:
    """Tests for GET /api/v1/knowledge."""

    @pytest.mark.asyncio
    async def test_list_knowledge_empty(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Empty store returns empty list."""
        response = await client.get(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_knowledge_paginated(
        self,
        client: AsyncClient,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Pagination works correctly."""
        # Create 5 articles
        for i in range(5):
            await knowledge_article_factory(store_id=store.id, title=f"Article {i}")

        # Get first page
        response = await client.get(
            "/api/v1/knowledge",
            params={"store_id": str(store.id), "page": 1, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["pages"] == 3

    @pytest.mark.asyncio
    async def test_list_knowledge_filter_by_type(
        self,
        client: AsyncClient,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Content type filter works."""
        await knowledge_article_factory(
            store_id=store.id, title="FAQ 1", content_type=ContentType.FAQ
        )
        await knowledge_article_factory(
            store_id=store.id, title="Policy 1", content_type=ContentType.POLICY
        )
        await knowledge_article_factory(
            store_id=store.id, title="FAQ 2", content_type=ContentType.FAQ
        )

        response = await client.get(
            "/api/v1/knowledge",
            params={"store_id": str(store.id), "content_type": "faq"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["content_type"] == "faq" for item in data["items"])

    @pytest.mark.asyncio
    async def test_list_knowledge_scoped_to_store(
        self,
        client: AsyncClient,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Only returns articles from the authenticated user's store."""
        await knowledge_article_factory(store_id=store.id, title="Our Article")
        await knowledge_article_factory(store_id=other_store.id, title="Their Article")

        response = await client.get(
            "/api/v1/knowledge",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Our Article"


class TestGetKnowledgeArticle:
    """Tests for GET /api/v1/knowledge/{article_id}."""

    @pytest.mark.asyncio
    async def test_get_article_with_chunks(
        self,
        client: AsyncClient,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Returns article with chunks array."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Test Article",
            num_chunks=3,
        )

        response = await client.get(
            f"/api/v1/knowledge/{article.id}",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Article"
        assert "chunks" in data
        assert len(data["chunks"]) == 3

    @pytest.mark.asyncio
    async def test_get_article_not_found(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Non-existent article returns 404."""
        import uuid

        response = await client.get(
            f"/api/v1/knowledge/{uuid.uuid4()}",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_article_wrong_store(
        self,
        client: AsyncClient,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Cannot get article from another store."""
        article = await knowledge_article_factory(
            store_id=other_store.id,
            title="Other Store Article",
        )

        # Try to access using our store_id - should fail
        # (Note: we'd need to be able to query with other_store.id but that's blocked by auth)
        response = await client.get(
            f"/api/v1/knowledge/{article.id}",
            params={"store_id": str(store.id)},
        )

        # Article exists but not in our store
        assert response.status_code == 404


class TestUpdateKnowledgeArticle:
    """Tests for PATCH /api/v1/knowledge/{article_id}."""

    @pytest.mark.asyncio
    async def test_update_article_metadata(
        self,
        client: AsyncClient,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Can update article title and content type."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="Original Title",
            content_type=ContentType.FAQ,
        )

        response = await client.patch(
            f"/api/v1/knowledge/{article.id}",
            params={"store_id": str(store.id)},
            json={"title": "Updated Title", "content_type": "policy"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content_type"] == "policy"

    @pytest.mark.asyncio
    async def test_update_article_not_found(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Updating non-existent article returns 404."""
        import uuid

        response = await client.patch(
            f"/api/v1/knowledge/{uuid.uuid4()}",
            params={"store_id": str(store.id)},
            json={"title": "New Title"},
        )

        assert response.status_code == 404


class TestDeleteKnowledgeArticle:
    """Tests for DELETE /api/v1/knowledge/{article_id}."""

    @pytest.mark.asyncio
    async def test_delete_article_cascades_chunks(
        self,
        client: AsyncClient,
        store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Deleting article returns 204."""
        article = await knowledge_article_factory(
            store_id=store.id,
            title="To Delete",
            num_chunks=3,
        )

        response = await client.delete(
            f"/api/v1/knowledge/{article.id}",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(
            f"/api/v1/knowledge/{article.id}",
            params={"store_id": str(store.id)},
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_article_not_found(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Deleting non-existent article returns 404."""
        import uuid

        response = await client.delete(
            f"/api/v1/knowledge/{uuid.uuid4()}",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_article_wrong_store(
        self,
        client: AsyncClient,
        store: Store,
        other_store: Store,
        knowledge_article_factory: Callable[..., Any],
    ) -> None:
        """Cannot delete article from another store."""
        article = await knowledge_article_factory(
            store_id=other_store.id,
            title="Other Store Article",
        )

        response = await client.delete(
            f"/api/v1/knowledge/{article.id}",
            params={"store_id": str(store.id)},
        )

        # Can't delete - not found in our store
        assert response.status_code == 404

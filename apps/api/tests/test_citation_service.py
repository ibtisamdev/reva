"""Tests for the citation service."""

import uuid

import pytest

from app.services.citation_service import CitationService
from app.services.retrieval_service import RetrievedChunk


class TestCitationService:
    """Tests for CitationService."""

    @pytest.fixture
    def service(self) -> CitationService:
        """Create a citation service instance."""
        return CitationService()

    @pytest.fixture
    def sample_chunks(self) -> list[RetrievedChunk]:
        """Create sample retrieved chunks."""
        article_id_1 = uuid.uuid4()
        article_id_2 = uuid.uuid4()

        return [
            RetrievedChunk(
                chunk_id=uuid.uuid4(),
                article_id=article_id_1,
                content="This is the first chunk with some content about shipping policies.",
                chunk_index=0,
                similarity=0.95,
                article_title="Shipping Policy",
                article_url="/pages/shipping",
            ),
            RetrievedChunk(
                chunk_id=uuid.uuid4(),
                article_id=article_id_1,
                content="Another chunk from the same article about international shipping.",
                chunk_index=1,
                similarity=0.88,
                article_title="Shipping Policy",
                article_url="/pages/shipping",
            ),
            RetrievedChunk(
                chunk_id=uuid.uuid4(),
                article_id=article_id_2,
                content="This chunk is about returns and refunds.",
                chunk_index=0,
                similarity=0.82,
                article_title="Return Policy",
                article_url="/pages/returns",
            ),
        ]

    def test_create_sources_from_chunks(
        self, service: CitationService, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Test creating sources from chunks."""
        sources = service.create_sources_from_chunks(sample_chunks)

        # Should deduplicate by article, so only 2 sources
        assert len(sources) == 2
        assert sources[0].title == "Shipping Policy"
        assert sources[1].title == "Return Policy"

    def test_create_sources_without_deduplication(
        self, service: CitationService, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Test creating sources without deduplication."""
        sources = service.create_sources_from_chunks(sample_chunks, deduplicate_by_article=False)

        # Should include all chunks
        assert len(sources) == 3

    def test_create_sources_empty(self, service: CitationService) -> None:
        """Test creating sources from empty list."""
        sources = service.create_sources_from_chunks([])
        assert sources == []

    def test_truncate_snippet_short(self, service: CitationService) -> None:
        """Test snippet truncation with short text."""
        text = "Short text"
        result = service._truncate_snippet(text)
        assert result == text

    def test_truncate_snippet_long(self, service: CitationService) -> None:
        """Test snippet truncation with long text."""
        text = "This is a very long text " * 20  # Much longer than 150 chars
        result = service._truncate_snippet(text, max_length=150)

        assert len(result) <= 153  # 150 + "..."
        assert result.endswith("...")

    def test_truncate_snippet_word_boundary(self, service: CitationService) -> None:
        """Test snippet truncation respects word boundaries."""
        text = "Word " * 50  # 250 chars
        result = service._truncate_snippet(text, max_length=150)

        # Should not cut in middle of "Word"
        assert not result.endswith("Wor...")

    def test_format_context_for_prompt(
        self, service: CitationService, sample_chunks: list[RetrievedChunk]
    ) -> None:
        """Test formatting context for LLM prompt."""
        context = service.format_context_for_prompt(sample_chunks)

        assert "[1]" in context
        assert "[2]" in context
        assert "[3]" in context
        assert "Shipping Policy" in context
        assert "Return Policy" in context

    def test_format_context_for_prompt_empty(self, service: CitationService) -> None:
        """Test formatting empty context."""
        context = service.format_context_for_prompt([])
        assert context == "No relevant context found."

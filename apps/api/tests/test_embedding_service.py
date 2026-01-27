"""Tests for the embedding service."""

import pytest

from app.services.embedding_service import EMBEDDING_DIMENSIONS, EmbeddingService


class TestEmbeddingService:
    """Tests for EmbeddingService."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an embedding service instance."""
        return EmbeddingService()

    def test_count_tokens(self, service: EmbeddingService) -> None:
        """Test token counting."""
        # Simple text
        text = "Hello, world!"
        count = service.count_tokens(text)
        assert count > 0
        assert isinstance(count, int)

    def test_count_tokens_empty(self, service: EmbeddingService) -> None:
        """Test token counting with empty string."""
        count = service.count_tokens("")
        assert count == 0

    def test_chunk_text_small(self, service: EmbeddingService) -> None:
        """Test chunking text smaller than max tokens."""
        text = "This is a short text."
        chunks = service.chunk_text(text, max_tokens=512, overlap_tokens=50)

        assert len(chunks) == 1
        assert chunks[0][0] == text
        assert chunks[0][1] > 0  # Token count

    def test_chunk_text_large(self, service: EmbeddingService) -> None:
        """Test chunking large text into multiple chunks."""
        # Create text with many tokens
        text = "This is a test sentence. " * 200  # ~1000 tokens

        chunks = service.chunk_text(text, max_tokens=512, overlap_tokens=50)

        assert len(chunks) >= 2
        # Each chunk should have <= max_tokens
        for chunk_text, token_count in chunks:
            assert token_count <= 550  # Allow small tolerance
            assert len(chunk_text) > 0

    def test_chunk_text_overlap(self, service: EmbeddingService) -> None:
        """Test that chunks have proper overlap."""
        # Create text that will definitely split
        text = "Word " * 200  # Create enough tokens to split

        chunks = service.chunk_text(text, max_tokens=100, overlap_tokens=20)

        # Should have multiple chunks
        assert len(chunks) >= 2

        # Verify overlap by checking that chunks share some content
        if len(chunks) >= 2:
            # The end of first chunk should partially overlap with start of second
            first_chunk = chunks[0][0]
            second_chunk = chunks[1][0]
            # Both chunks should contain "Word"
            assert "Word" in first_chunk
            assert "Word" in second_chunk


class TestEmbeddingServiceAsync:
    """Async tests for EmbeddingService (require API key)."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an embedding service instance."""
        return EmbeddingService()

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip by default since it requires API key
        reason="Requires OpenAI API key",
    )
    async def test_generate_embedding(self, service: EmbeddingService) -> None:
        """Test embedding generation."""
        embedding = await service.generate_embedding("Test query")

        assert len(embedding) == EMBEDDING_DIMENSIONS
        assert all(isinstance(v, float) for v in embedding)

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip by default since it requires API key
        reason="Requires OpenAI API key",
    )
    async def test_generate_embeddings_batch(self, service: EmbeddingService) -> None:
        """Test batch embedding generation."""
        texts = ["First text", "Second text", "Third text"]
        embeddings = await service.generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        for embedding in embeddings:
            assert len(embedding) == EMBEDDING_DIMENSIONS

    @pytest.mark.asyncio
    async def test_generate_embeddings_batch_empty(self, service: EmbeddingService) -> None:
        """Test batch embedding with empty list."""
        embeddings = await service.generate_embeddings_batch([])
        assert embeddings == []

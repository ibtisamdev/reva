"""OpenAI embedding service for generating vector embeddings."""

import tiktoken
from openai import AsyncOpenAI

from app.core.config import settings

# Constants
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MAX_TOKENS_PER_CHUNK = 512
CHUNK_OVERLAP_TOKENS = 50


class EmbeddingService:
    """Service for generating embeddings using OpenAI."""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._encoding: tiktoken.Encoding | None = None

    @property
    def encoding(self) -> tiktoken.Encoding:
        """Lazy-load the tiktoken encoding."""
        if self._encoding is None:
            self._encoding = tiktoken.encoding_for_model(EMBEDDING_MODEL)
        return self._encoding

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding vector
        """
        response = await self.client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors in the same order as input
        """
        if not texts:
            return []

        # OpenAI allows up to 2048 inputs per batch
        response = await self.client.embeddings.create(
            input=texts,
            model=EMBEDDING_MODEL,
        )
        return [item.embedding for item in response.data]

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def chunk_text(
        self,
        text: str,
        max_tokens: int = MAX_TOKENS_PER_CHUNK,
        overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
    ) -> list[tuple[str, int]]:
        """Split text into chunks with token overlap.

        Uses token-based splitting to ensure accurate chunk sizes.

        Args:
            text: The text to chunk
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of overlapping tokens between chunks

        Returns:
            List of tuples (chunk_text, token_count)
        """
        tokens = self.encoding.encode(text)

        if len(tokens) <= max_tokens:
            return [(text, len(tokens))]

        chunks: list[tuple[str, int]] = []
        start = 0

        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append((chunk_text, len(chunk_tokens)))

            # If we've reached the end, stop
            if end >= len(tokens):
                break

            # Move start forward, accounting for overlap
            # Ensure we always make progress (at least 1 token forward)
            next_start = end - overlap_tokens
            if next_start <= start:
                next_start = start + 1
            start = next_start

        return chunks


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

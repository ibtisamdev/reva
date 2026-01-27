"""Citation extraction and formatting service."""

from uuid import UUID

from app.schemas.chat import SourceReference
from app.services.retrieval_service import RetrievedChunk


class CitationService:
    """Service for extracting and formatting citations."""

    def create_sources_from_chunks(
        self,
        chunks: list[RetrievedChunk],
        deduplicate_by_article: bool = True,
    ) -> list[SourceReference]:
        """Convert retrieved chunks to source references.

        Args:
            chunks: Retrieved chunks from RAG
            deduplicate_by_article: If True, only include one chunk per article

        Returns:
            List of source references for the response
        """
        sources: list[SourceReference] = []
        seen_articles: set[UUID] = set()

        for chunk in chunks:
            # Skip if we've already added a source from this article
            if deduplicate_by_article and chunk.article_id in seen_articles:
                continue

            source = SourceReference(
                title=chunk.article_title,
                url=chunk.article_url,
                snippet=self._truncate_snippet(chunk.content),
                chunk_id=chunk.chunk_id,
            )
            sources.append(source)
            seen_articles.add(chunk.article_id)

        return sources

    def _truncate_snippet(
        self,
        text: str,
        max_length: int = 150,
    ) -> str:
        """Truncate text to create a snippet.

        Args:
            text: The text to truncate
            max_length: Maximum length of the snippet

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text

        # Try to break at a word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(" ")
        if last_space > max_length * 0.7:
            truncated = truncated[:last_space]

        return truncated.rstrip() + "..."

    def format_context_for_prompt(
        self,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Format retrieved chunks for inclusion in LLM prompt.

        Numbers each source so the LLM can reference them.

        Args:
            chunks: Retrieved chunks to format

        Returns:
            Formatted context string for the prompt
        """
        if not chunks:
            return "No relevant context found."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source_label = f"[{i}]"
            title = f"Source: {chunk.article_title}"
            context_parts.append(f"{source_label} {title}\n{chunk.content}")

        return "\n\n".join(context_parts)

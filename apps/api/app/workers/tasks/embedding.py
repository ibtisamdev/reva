"""Celery tasks for async embedding generation."""

import asyncio
from typing import Any
from uuid import UUID

from app.core.database import async_session_maker
from app.services.knowledge_service import KnowledgeService
from app.workers.celery_app import BaseTask, celery_app


@celery_app.task(  # type: ignore[untyped-decorator]
    name="tasks.embedding.process_article",
    base=BaseTask,
    bind=True,
)
def process_article_embeddings(self: BaseTask, article_id: str) -> dict[str, Any]:  # noqa: ARG001
    """Process embeddings for a knowledge article.

    This task is triggered for large documents that need
    async embedding generation.

    Args:
        article_id: The article ID as a string

    Returns:
        Dict with processing results
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(_process_article_embeddings_async(UUID(article_id)))
        return result
    finally:
        loop.close()


async def _process_article_embeddings_async(article_id: UUID) -> dict[str, Any]:
    """Async implementation of embedding processing.

    Args:
        article_id: The article ID

    Returns:
        Dict with article_id, chunks_processed count, and status
    """
    async with async_session_maker() as session:
        service = KnowledgeService(session)
        chunks_processed = await service.process_article_embeddings(article_id)
        await session.commit()

        return {
            "article_id": str(article_id),
            "chunks_processed": chunks_processed,
            "status": "completed",
        }

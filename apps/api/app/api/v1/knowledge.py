"""Knowledge management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DBSession, get_user_organization_id
from app.models.knowledge import ContentType
from app.models.store import Store
from app.schemas.common import PaginatedResponse
from app.schemas.knowledge import (
    IngestionResponse,
    KnowledgeArticleDetailResponse,
    KnowledgeArticleResponse,
    KnowledgeArticleUpdate,
    KnowledgeChunkResponse,
    TextIngestionRequest,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter()


# === Dependencies ===


async def get_store_for_user(
    store_id: UUID = Query(..., description="Store ID"),
    user: CurrentUser = None,  # type: ignore[assignment]
    db: DBSession = None,  # type: ignore[assignment]
) -> Store:
    """Get and validate store access for the authenticated user.

    Validates that the store exists, is active, and belongs to the user's organization.
    """
    org_id = get_user_organization_id(user)

    query = select(Store).where(
        Store.id == store_id,
        Store.is_active == True,  # noqa: E712
        Store.organization_id == org_id,
    )
    result = await db.execute(query)
    store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found or access denied",
        )

    return store


# === Endpoints ===


@router.post(
    "",
    response_model=IngestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a knowledge document",
    description="""
    Ingest a text document into the knowledge base.

    The content will be automatically:
    - Chunked into ~512 token segments with overlap
    - Embedded using OpenAI text-embedding-3-small
    - Stored in pgvector for semantic search

    For small documents (< ~5000 tokens), processing is synchronous.
    For larger documents, processing happens asynchronously via background task.
    """,
)
async def ingest_knowledge(
    data: TextIngestionRequest,
    db: DBSession,
    store: Store = Depends(get_store_for_user),
) -> IngestionResponse:
    """Ingest a text document into the knowledge base."""
    service = KnowledgeService(db)

    # Check document size (rough estimate)
    token_count = service.embedding_service.count_tokens(data.content)
    is_large = token_count > 5000  # ~10 chunks

    article = await service.ingest_text(
        store_id=store.id,
        data=data,
        process_sync=not is_large,
    )

    await db.commit()

    # If large, trigger async processing
    if is_large:
        # Import here to avoid circular imports
        from app.workers.tasks.embedding import process_article_embeddings

        process_article_embeddings.delay(str(article.id))

    chunks_count = len(article.chunks) if article.chunks else 0

    return IngestionResponse(
        article_id=article.id,
        title=article.title,
        chunks_count=chunks_count,
        status="processing" if is_large else "completed",
        message=(
            "Document queued for processing" if is_large else "Document ingested successfully"
        ),
    )


@router.get(
    "",
    response_model=PaginatedResponse[KnowledgeArticleResponse],
    summary="List knowledge articles",
)
async def list_knowledge(
    db: DBSession,
    store: Store = Depends(get_store_for_user),
    content_type: ContentType | None = Query(None, description="Filter by content type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[KnowledgeArticleResponse]:
    """List all knowledge articles for the store."""
    service = KnowledgeService(db)

    offset = (page - 1) * page_size
    articles, total = await service.list_articles(
        store_id=store.id,
        content_type=content_type,
        limit=page_size,
        offset=offset,
    )

    items = [
        KnowledgeArticleResponse(
            id=a.id,
            store_id=a.store_id,
            title=a.title,
            content=a.content,
            content_type=a.content_type,
            source_url=a.source_url,
            chunks_count=len(a.chunks) if a.chunks else 0,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in articles
    ]

    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{article_id}",
    response_model=KnowledgeArticleDetailResponse,
    summary="Get a knowledge article",
)
async def get_knowledge_article(
    article_id: UUID,
    db: DBSession,
    store: Store = Depends(get_store_for_user),
) -> KnowledgeArticleDetailResponse:
    """Get a specific knowledge article with its chunks."""
    service = KnowledgeService(db)

    article = await service.get_article(article_id, store.id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge article not found",
        )

    chunks = [
        KnowledgeChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            content=c.content,
            token_count=c.token_count,
            has_embedding=c.embedding is not None,
        )
        for c in article.chunks
    ]

    return KnowledgeArticleDetailResponse(
        id=article.id,
        store_id=article.store_id,
        title=article.title,
        content=article.content,
        content_type=article.content_type,
        source_url=article.source_url,
        chunks_count=len(chunks),
        created_at=article.created_at,
        updated_at=article.updated_at,
        chunks=chunks,
    )


@router.patch(
    "/{article_id}",
    response_model=KnowledgeArticleResponse,
    summary="Update a knowledge article",
)
async def update_knowledge_article(
    article_id: UUID,
    data: KnowledgeArticleUpdate,
    db: DBSession,
    store: Store = Depends(get_store_for_user),
) -> KnowledgeArticleResponse:
    """Update a knowledge article's metadata.

    Note: Updating content requires re-ingestion for new embeddings.
    """
    service = KnowledgeService(db)

    article = await service.update_article(article_id, store.id, data)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge article not found",
        )

    await db.commit()

    return KnowledgeArticleResponse(
        id=article.id,
        store_id=article.store_id,
        title=article.title,
        content=article.content,
        content_type=article.content_type,
        source_url=article.source_url,
        chunks_count=len(article.chunks) if article.chunks else 0,
        created_at=article.created_at,
        updated_at=article.updated_at,
    )


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge article",
)
async def delete_knowledge_article(
    article_id: UUID,
    db: DBSession,
    store: Store = Depends(get_store_for_user),
) -> None:
    """Delete a knowledge article and all its chunks."""
    service = KnowledgeService(db)

    deleted = await service.delete_article(article_id, store.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge article not found",
        )

    await db.commit()

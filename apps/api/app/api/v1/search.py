"""Product search API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_store_by_id
from app.models.store import Store
from app.schemas.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_products(
    request: SearchRequest,
    store: Store = Depends(get_store_by_id),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Search products using natural language with optional filters.

    Combines vector similarity search with full-text search using
    Reciprocal Rank Fusion for optimal results.
    """
    service = SearchService(db)
    results = await service.hybrid_search(
        query=request.query,
        store_id=store.id,
        filters=request.filters,
        limit=request.limit,
    )

    return SearchResponse(
        results=results,
        total=len(results),
        query=request.query,
        filters_applied=request.filters,
    )

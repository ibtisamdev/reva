"""Product recommendation API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_store_by_id
from app.models.store import Store
from app.schemas.search import ProductSearchResult
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.get("/{product_id}/similar", response_model=list[ProductSearchResult])
async def get_similar_products(
    product_id: UUID,
    store: Store = Depends(get_store_by_id),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[ProductSearchResult]:
    """Get products similar to a given product."""
    service = RecommendationService(db)
    return await service.get_similar_products(product_id, store.id, limit=limit)


@router.get("/{product_id}/upsell", response_model=list[ProductSearchResult])
async def get_upsell_products(
    product_id: UUID,
    store: Store = Depends(get_store_by_id),
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
) -> list[ProductSearchResult]:
    """Get upsell product suggestions (higher-priced, same category)."""
    service = RecommendationService(db)
    return await service.get_upsell_products(product_id, store.id, limit=limit)


@router.post("/compare")
async def compare_products(
    product_ids: list[UUID],
    store: Store = Depends(get_store_by_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Compare multiple products side by side."""
    service = RecommendationService(db)
    return await service.compare_products(product_ids, store.id)

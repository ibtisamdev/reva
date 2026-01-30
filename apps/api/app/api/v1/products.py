"""Products API endpoints for listing synced products."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, get_db, get_store_for_user
from app.models.product import Product
from app.schemas.common import PaginatedResponse
from app.schemas.shopify import ProductResponse

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    user: CurrentUser,
    store_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProductResponse]:
    """List synced products for a store."""
    await get_store_for_user(store_id, user, db)

    # Count
    count_stmt = select(func.count()).select_from(Product).where(Product.store_id == store_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    stmt = (
        select(Product)
        .where(Product.store_id == store_id)
        .order_by(Product.title)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    products = list(result.scalars().all())

    pages = (total + page_size - 1) // page_size

    return PaginatedResponse[ProductResponse](
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

"""Dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Re-export auth dependencies for convenience
from app.core.auth import (
    CurrentUser,
    OptionalUser,
    get_current_user,
    get_optional_user,
)
from app.core.config import settings
from app.core.database import get_async_session

if TYPE_CHECKING:
    from app.models.store import Store

# Type alias for database session dependency
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_async_session for backwards compatibility."""
    async for session in get_async_session():
        yield session


# Shared Redis connection pool
_redis_pool: aioredis.ConnectionPool | None = None


def _get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool  # noqa: PLW0603
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            str(settings.redis_url), decode_responses=True
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """Yield a Redis client from the shared connection pool."""
    pool = _get_redis_pool()
    r = aioredis.Redis(connection_pool=pool)
    try:
        yield r
    finally:
        await r.aclose()


# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_store_by_id(
    store_id: UUID = Query(..., description="Store ID"),
    db: AsyncSession = Depends(get_db),
) -> "Store":
    """Get store from query parameter.

    Used by endpoints that need to identify the store from a query parameter,
    such as the chat widget and dashboard APIs.
    """
    from app.models.store import Store

    query = select(Store).where(
        Store.id == store_id,
        Store.is_active == True,  # noqa: E712
    )
    result = await db.execute(query)
    store = result.scalar_one_or_none()

    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found or inactive",
        )

    return store


def get_user_organization_id(user: dict[str, Any]) -> str:
    """Extract organization ID from the authenticated user's JWT payload.

    Better Auth's JWT includes activeOrganizationId when a user has an active org.
    """
    org_id = user.get("activeOrganizationId")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active organization. Please select or create an organization.",
        )
    return str(org_id)


async def get_store_for_user(
    store_id: UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> "Store":
    """Get store by ID, verifying it belongs to the user's organization.

    Used by endpoints that need to validate store ownership via path parameter.
    """
    from app.models.store import Store

    org_id = get_user_organization_id(user)

    query = select(Store).where(
        Store.id == store_id,
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


__all__ = [
    "AsyncSessionDep",
    "CurrentUser",
    "DBSession",
    "OptionalUser",
    "get_current_user",
    "get_db",
    "get_optional_user",
    "get_store_by_id",
    "get_redis",
    "get_store_for_user",
    "get_user_organization_id",
]

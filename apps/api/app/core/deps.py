"""Dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session

# Type alias for database session dependency
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_async_session for backwards compatibility."""
    async for session in get_async_session():
        yield session


# Database session dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]

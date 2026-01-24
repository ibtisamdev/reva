"""Health check endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Health check endpoint.

    Checks database connectivity and returns service status.
    """
    health_status: dict[str, Any] = {
        "status": "healthy",
        "version": settings.version,
        "environment": settings.environment,
        "checks": {},
    }

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"

    # Check Redis connection
    try:
        import redis.asyncio as redis

        redis_client = redis.from_url(str(settings.redis_url))  # type: ignore[no-untyped-call]
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"

    return health_status


@router.get("/health/live")
async def liveness_check() -> dict[str, str]:
    """
    Liveness probe for Kubernetes/container orchestration.

    Simple check that the service is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Readiness probe for Kubernetes/container orchestration.

    Checks if the service is ready to receive traffic.
    """
    # Check database
    await db.execute(text("SELECT 1"))

    return {"status": "ready"}

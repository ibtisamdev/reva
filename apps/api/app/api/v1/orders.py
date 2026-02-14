"""Order verification endpoints."""

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Request

from app.core.deps import DBSession, get_redis, get_store_by_id
from app.core.rate_limit import limiter
from app.models.store import Store
from app.schemas.order import OrderVerificationRequest, OrderVerificationResponse
from app.services.order_service import OrderService

router = APIRouter()


@router.post("/verify", response_model=OrderVerificationResponse)
@limiter.limit("5/minute")
async def verify_order(
    request: Request,  # noqa: ARG001 — required by slowapi
    data: OrderVerificationRequest,
    db: DBSession,
    store: Store = Depends(get_store_by_id),
    redis: aioredis.Redis = Depends(get_redis),
) -> OrderVerificationResponse:
    """Verify a customer's identity and look up their order.

    Rate limited to 5 requests per minute per IP.
    Used by the chat widget for direct order verification.
    """
    service = OrderService(db, redis)
    return await service.verify_and_lookup(store.id, data.order_number, data.email)

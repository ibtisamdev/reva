"""API v1 router combining all route modules."""

from fastapi import APIRouter

from app.api.v1 import health

api_router = APIRouter()

# Include health check routes (no prefix)
api_router.include_router(health.router)

# Future routes will be added here:
# api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
# api_router.include_router(shopify.router, prefix="/shopify", tags=["shopify"])
# api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
# api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])

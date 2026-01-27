"""API v1 router combining all route modules."""

from fastapi import APIRouter

from app.api.v1 import chat, health, knowledge

api_router = APIRouter()

# Include health check routes (no prefix)
api_router.include_router(health.router)

# Knowledge management (requires auth)
api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["knowledge"],
)

# Chat endpoints (for widget, auth optional)
api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["chat"],
)

# Future routes will be added here:
# api_router.include_router(shopify.router, prefix="/shopify", tags=["shopify"])
# api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])

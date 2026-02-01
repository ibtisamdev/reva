"""API v1 router combining all route modules."""

from fastapi import APIRouter

from app.api.v1 import chat, health, knowledge, products, shopify, stores
from app.api.v1.webhooks import shopify as shopify_webhooks

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

# Store settings endpoints
api_router.include_router(
    stores.router,
    prefix="/stores",
    tags=["stores"],
)

# Shopify OAuth and management
api_router.include_router(
    shopify.router,
    prefix="/shopify",
    tags=["shopify"],
)

# Shopify webhooks (no auth - verified via HMAC)
api_router.include_router(
    shopify_webhooks.router,
    prefix="/webhooks/shopify",
    tags=["webhooks"],
)

# Products
api_router.include_router(
    products.router,
    prefix="/products",
    tags=["products"],
)

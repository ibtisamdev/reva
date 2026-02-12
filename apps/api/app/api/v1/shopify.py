"""Shopify OAuth and management endpoints."""

import hashlib
import hmac as hmac_mod
import secrets
import time
from uuid import UUID

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import CurrentUser, get_db, get_redis, get_store_for_user
from app.core.encryption import decrypt_token, encrypt_token
from app.integrations.shopify.client import ShopifyClient
from app.integrations.shopify.oauth import build_auth_url, exchange_code_for_token, verify_hmac
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.product import Product
from app.schemas.shopify import ShopifyConnectionResponse, SyncStatusResponse
from app.workers.tasks.shopify import sync_products_full

router = APIRouter()

NONCE_TTL_SECONDS = 600  # 10 minutes
INSTALL_TOKEN_TTL_SECONDS = 300  # 5 minutes


def _sign_install_token(store_id: str, timestamp: int) -> str:
    """Create an HMAC signature for a store install request."""
    msg = f"{store_id}:{timestamp}"
    return hmac_mod.new(settings.secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()


@router.get("/install-url")
async def get_install_url(
    user: CurrentUser,
    store_id: UUID = Query(...),
    shop: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Generate a signed install URL. Requires authentication."""
    await get_store_for_user(store_id, user, db)

    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid shop domain")

    ts = int(time.time())
    sig = _sign_install_token(str(store_id), ts)
    url = (
        f"{settings.api_url}/api/v1/shopify/install"
        f"?shop={shop}&store_id={store_id}&ts={ts}&sig={sig}"
    )
    return {"install_url": url}


@router.get("/install")
async def install(
    shop: str,
    store_id: UUID,
    ts: int = Query(...),
    sig: str = Query(...),
    r: aioredis.Redis = Depends(get_redis),
) -> RedirectResponse:
    """Start Shopify OAuth flow.

    This endpoint is called via browser redirect so it cannot use Bearer auth.
    Security is provided by a signed token from the /install-url endpoint
    and the nonce/state parameter validated in the callback.
    """
    # Verify install signature
    expected = _sign_install_token(str(store_id), ts)
    if not hmac_mod.compare_digest(expected, sig):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid signature")
    if abs(time.time() - ts) > INSTALL_TOKEN_TTL_SECONDS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Expired install token")

    # Validate shop domain
    if not shop.endswith(".myshopify.com"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid shop domain")

    # Generate and store nonce
    nonce = secrets.token_urlsafe(16)
    await r.set(f"shopify_oauth:{nonce}", f"{store_id}:{shop}", ex=NONCE_TTL_SECONDS)

    auth_url = build_auth_url(shop, nonce)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    shop: str = Query(...),
    state: str = Query(...),
    hmac: str = Query(...),  # noqa: ARG001 — used via request.query_params
    db: AsyncSession = Depends(get_db),
    r: aioredis.Redis = Depends(get_redis),
) -> RedirectResponse:
    """Handle Shopify OAuth callback."""
    # Verify HMAC
    params = dict(request.query_params)
    if not verify_hmac(params, settings.shopify_client_secret):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid HMAC signature")

    # Verify nonce
    stored = await r.get(f"shopify_oauth:{state}")
    await r.delete(f"shopify_oauth:{state}")

    if not stored:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired state")

    store_id_str, expected_shop = stored.split(":", 1)
    if expected_shop != shop:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Shop mismatch")

    store_id = UUID(store_id_str)

    # Exchange code for access token
    try:
        access_token, granted_scopes = await exchange_code_for_token(shop, code)
    except httpx.HTTPStatusError:
        return RedirectResponse(
            f"{settings.frontend_url}/dashboard/settings/integrations?error=token_exchange_failed"
        )
    encrypted_token = encrypt_token(access_token)

    # Upsert StoreIntegration
    stmt = select(StoreIntegration).where(StoreIntegration.store_id == store_id)
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()

    credentials = {"access_token": encrypted_token, "granted_scopes": granted_scopes}

    if integration:
        integration.platform = PlatformType.SHOPIFY
        integration.platform_store_id = shop
        integration.platform_domain = shop
        integration.credentials = credentials
        integration.status = IntegrationStatus.ACTIVE
        integration.sync_error = None
    else:
        integration = StoreIntegration(
            store_id=store_id,
            platform=PlatformType.SHOPIFY,
            platform_store_id=shop,
            platform_domain=shop,
            credentials=credentials,
            status=IntegrationStatus.ACTIVE,
        )
        db.add(integration)

    await db.commit()

    # Register webhooks (best-effort)
    try:
        client = ShopifyClient(shop, access_token)
        await client.register_webhooks()
    except Exception:
        pass  # Non-fatal — webhooks can be registered later

    # Trigger initial sync
    sync_products_full.delay(str(store_id))

    return RedirectResponse(
        f"{settings.frontend_url}/dashboard/settings/integrations?connected=true"
    )


@router.post("/disconnect")
async def disconnect(
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """Disconnect Shopify integration."""
    await get_store_for_user(store_id, user, db)

    stmt = select(StoreIntegration).where(
        StoreIntegration.store_id == store_id,
        StoreIntegration.platform == PlatformType.SHOPIFY,
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No Shopify integration found")

    # Delete webhooks (best-effort)
    if integration.status == IntegrationStatus.ACTIVE:
        try:
            access_token = decrypt_token(integration.credentials.get("access_token", ""))
            client = ShopifyClient(integration.platform_domain, access_token)
            await client.delete_webhooks()
        except Exception:
            pass

    integration.status = IntegrationStatus.DISCONNECTED
    integration.credentials = {}
    await db.commit()

    return SyncStatusResponse(status="disconnected", message="Shopify store disconnected")


@router.post("/sync")
async def trigger_sync(
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """Trigger a manual product sync."""
    await get_store_for_user(store_id, user, db)

    stmt = select(StoreIntegration).where(
        StoreIntegration.store_id == store_id,
        StoreIntegration.platform == PlatformType.SHOPIFY,
        StoreIntegration.status == IntegrationStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No active Shopify integration")

    # Clear previous sync error before starting new sync
    integration.sync_error = None
    await db.commit()

    sync_products_full.delay(str(store_id))
    return SyncStatusResponse(status="syncing", message="Product sync started")


@router.get("/status")
async def connection_status(
    user: CurrentUser,
    store_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
) -> ShopifyConnectionResponse:
    """Get Shopify connection status."""
    await get_store_for_user(store_id, user, db)

    stmt = select(StoreIntegration).where(StoreIntegration.store_id == store_id)
    result = await db.execute(stmt)
    integration = result.scalar_one_or_none()

    if not integration or integration.platform != PlatformType.SHOPIFY:
        return ShopifyConnectionResponse(
            platform="shopify",
            platform_domain="",
            status="disconnected",
            product_count=0,
        )

    # Count products
    count_stmt = select(func.count()).select_from(Product).where(Product.store_id == store_id)
    count_result = await db.execute(count_stmt)
    product_count = count_result.scalar() or 0

    return ShopifyConnectionResponse(
        platform=integration.platform.value,
        platform_domain=integration.platform_domain,
        status=integration.status.value,
        last_synced_at=integration.last_synced_at,
        product_count=product_count,
        sync_error=integration.sync_error,
    )

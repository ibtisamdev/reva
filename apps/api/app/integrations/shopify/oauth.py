"""Shopify OAuth helpers for HMAC verification and token exchange."""

import hashlib
import hmac
from urllib.parse import urlencode

import httpx

from app.core.config import settings


def verify_hmac(query_params: dict[str, str], secret: str) -> bool:
    """Verify Shopify OAuth callback HMAC signature.

    Args:
        query_params: All query parameters from the callback URL.
        secret: The Shopify client secret.

    Returns:
        True if HMAC is valid.
    """
    received_hmac = query_params.get("hmac", "")
    # Build message from sorted params excluding 'hmac'
    params = {k: v for k, v in sorted(query_params.items()) if k != "hmac"}
    message = urlencode(params)

    computed = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, received_hmac)


def build_auth_url(shop: str, nonce: str) -> str:
    """Build the Shopify OAuth authorization URL.

    Args:
        shop: The shop domain (e.g. mystore.myshopify.com).
        nonce: Random state parameter for CSRF protection.

    Returns:
        The full authorization URL to redirect the merchant to.
    """
    redirect_uri = f"{settings.api_url}/api/v1/shopify/callback"
    params = urlencode({
        "client_id": settings.shopify_client_id,
        "scope": settings.shopify_scopes,
        "redirect_uri": redirect_uri,
        "state": nonce,
    })
    return f"https://{shop}/admin/oauth/authorize?{params}"


async def exchange_code_for_token(shop: str, code: str) -> str:
    """Exchange the OAuth authorization code for a permanent access token.

    Args:
        shop: The shop domain.
        code: The authorization code from Shopify.

    Returns:
        The access token string.

    Raises:
        httpx.HTTPStatusError: If the token exchange fails.
    """
    url = f"https://{shop}/admin/oauth/access_token"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "client_id": settings.shopify_client_id,
            "client_secret": settings.shopify_client_secret,
            "code": code,
        })
        response.raise_for_status()
        data = response.json()
        return data["access_token"]

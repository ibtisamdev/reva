"""Tests for Shopify OAuth helpers and routes.

Covers:
- OAuth helper functions (verify_hmac, build_auth_url, exchange_code_for_token)
- Install token signing (_sign_install_token)
- GET /api/v1/shopify/install-url
- GET /api/v1/shopify/install
- GET /api/v1/shopify/callback
- POST /api/v1/shopify/disconnect
- POST /api/v1/shopify/sync
- GET /api/v1/shopify/status
"""

import hashlib
import hmac
import time
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import AsyncClient, HTTPStatusError, Response

from app.core.encryption import encrypt_token
from app.integrations.shopify.oauth import (
    build_auth_url,
    exchange_code_for_token,
    verify_hmac,
)
from app.models.integration import IntegrationStatus, PlatformType, StoreIntegration
from app.models.store import Store
from tests.conftest import (
    SHOPIFY_TEST_CLIENT_ID,
    SHOPIFY_TEST_CLIENT_SECRET,
    SHOPIFY_TEST_SECRET_KEY,
    SHOPIFY_TEST_SHOP,
)

# ---------------------------------------------------------------------------
# Unit Tests: verify_hmac
# ---------------------------------------------------------------------------


class TestVerifyHmac:
    """Unit tests for Shopify OAuth HMAC verification."""

    def test_valid_signature(self, shopify_oauth_hmac: Callable[[dict[str, str]], str]) -> None:
        """verify_hmac returns True for correctly signed params."""
        params = {
            "code": "auth-code-123",
            "shop": SHOPIFY_TEST_SHOP,
            "state": "nonce-abc",
            "timestamp": "1234567890",
        }
        params["hmac"] = shopify_oauth_hmac(params)

        assert verify_hmac(params, SHOPIFY_TEST_CLIENT_SECRET) is True

    def test_tampered_params(self, shopify_oauth_hmac: Callable[[dict[str, str]], str]) -> None:
        """verify_hmac returns False when any param is modified after signing."""
        params = {
            "code": "auth-code-123",
            "shop": SHOPIFY_TEST_SHOP,
            "state": "nonce-abc",
        }
        params["hmac"] = shopify_oauth_hmac(params)

        # Tamper with a param
        params["code"] = "different-code"

        assert verify_hmac(params, SHOPIFY_TEST_CLIENT_SECRET) is False

    def test_missing_hmac_param(self) -> None:
        """verify_hmac handles missing hmac key gracefully (returns False)."""
        params = {
            "code": "auth-code-123",
            "shop": SHOPIFY_TEST_SHOP,
        }
        # No hmac key — should return False, not crash
        assert verify_hmac(params, SHOPIFY_TEST_CLIENT_SECRET) is False

    def test_wrong_secret(self, shopify_oauth_hmac: Callable[[dict[str, str]], str]) -> None:
        """verify_hmac returns False with wrong secret."""
        params = {
            "code": "auth-code-123",
            "shop": SHOPIFY_TEST_SHOP,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        assert verify_hmac(params, "wrong-secret") is False

    def test_empty_params(self) -> None:
        """verify_hmac handles empty params dict."""
        # Compute HMAC of empty string
        expected_hmac = hmac.new(
            SHOPIFY_TEST_CLIENT_SECRET.encode(),
            b"",
            hashlib.sha256,
        ).hexdigest()

        params = {"hmac": expected_hmac}
        assert verify_hmac(params, SHOPIFY_TEST_CLIENT_SECRET) is True

    def test_special_characters_in_params(
        self, shopify_oauth_hmac: Callable[[dict[str, str]], str]
    ) -> None:
        """verify_hmac correctly handles URL encoding of special characters."""
        params = {
            "shop": "test-store.myshopify.com",
            "code": "abc=123&foo",  # Contains special chars
            "state": "state/with/slashes",
        }
        params["hmac"] = shopify_oauth_hmac(params)

        assert verify_hmac(params, SHOPIFY_TEST_CLIENT_SECRET) is True


# ---------------------------------------------------------------------------
# Unit Tests: build_auth_url
# ---------------------------------------------------------------------------


class TestBuildAuthUrl:
    """Unit tests for Shopify OAuth URL builder."""

    def test_url_structure(self) -> None:
        """build_auth_url produces correct URL with required params."""
        shop = "my-store.myshopify.com"
        nonce = "random-nonce-123"

        url = build_auth_url(shop, nonce)

        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == shop
        assert parsed.path == "/admin/oauth/authorize"

        query_params = parse_qs(parsed.query)
        assert query_params["client_id"] == [SHOPIFY_TEST_CLIENT_ID]
        assert query_params["state"] == [nonce]
        assert "redirect_uri" in query_params
        assert "scope" in query_params

    def test_redirect_uri_format(self) -> None:
        """Redirect URI points to the callback endpoint."""
        url = build_auth_url("shop.myshopify.com", "nonce")

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        redirect_uri = query_params["redirect_uri"][0]

        assert "/api/v1/shopify/callback" in redirect_uri

    def test_encodes_special_chars_in_nonce(self) -> None:
        """URL params are properly encoded."""
        nonce = "nonce+with/special=chars"

        url = build_auth_url("shop.myshopify.com", nonce)

        # The URL should be valid and contain the encoded nonce
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        assert query_params["state"] == [nonce]


# ---------------------------------------------------------------------------
# Unit Tests: exchange_code_for_token
# ---------------------------------------------------------------------------


class TestExchangeCodeForToken:
    """Unit tests for Shopify token exchange."""

    async def test_success(self, mock_shopify_token_exchange: MagicMock) -> None:
        """exchange_code_for_token returns access token and scopes on success."""
        token, scopes = await exchange_code_for_token("shop.myshopify.com", "auth-code-123")

        assert token == "shpat_test_access_token_123"
        assert scopes == "read_products,read_content,read_orders"
        mock_shopify_token_exchange.post.assert_called_once()

    async def test_http_error_raises(self) -> None:
        """exchange_code_for_token raises HTTPStatusError on failure."""
        with patch("app.integrations.shopify.oauth.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            )
            mock_client.post.return_value = mock_response

            with pytest.raises(HTTPStatusError):
                await exchange_code_for_token("shop.myshopify.com", "bad-code")

    async def test_sends_correct_payload(self) -> None:
        """Token exchange sends correct client credentials."""
        with patch("app.integrations.shopify.oauth.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"access_token": "token"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post.return_value = mock_response

            await exchange_code_for_token("shop.myshopify.com", "the-code")

            call_args = mock_client.post.call_args
            assert "shop.myshopify.com" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["code"] == "the-code"
            assert payload["client_id"] == SHOPIFY_TEST_CLIENT_ID
            assert payload["client_secret"] == SHOPIFY_TEST_CLIENT_SECRET


# ---------------------------------------------------------------------------
# Unit Tests: _sign_install_token
# ---------------------------------------------------------------------------


class TestSignInstallToken:
    """Unit tests for install token signing."""

    def test_deterministic(self) -> None:
        """Same inputs produce same signature."""
        from app.api.v1.shopify import _sign_install_token

        store_id = "store-123"
        timestamp = 1234567890

        sig1 = _sign_install_token(store_id, timestamp)
        sig2 = _sign_install_token(store_id, timestamp)

        assert sig1 == sig2

    def test_different_inputs(self) -> None:
        """Different store_id or timestamp produce different signatures."""
        from app.api.v1.shopify import _sign_install_token

        sig1 = _sign_install_token("store-1", 1000)
        sig2 = _sign_install_token("store-2", 1000)
        sig3 = _sign_install_token("store-1", 2000)

        assert sig1 != sig2
        assert sig1 != sig3
        assert sig2 != sig3

    def test_uses_secret_key(self) -> None:
        """Signature is computed using settings.secret_key."""
        from app.api.v1.shopify import _sign_install_token

        store_id = "store-123"
        timestamp = 1234567890

        # Compute expected signature manually
        msg = f"{store_id}:{timestamp}"
        expected = hmac.new(
            SHOPIFY_TEST_SECRET_KEY.encode(),
            msg.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert _sign_install_token(store_id, timestamp) == expected


# ---------------------------------------------------------------------------
# Route Tests: GET /api/v1/shopify/install-url
# ---------------------------------------------------------------------------


class TestInstallUrlRoute:
    """Tests for the install-url endpoint."""

    async def test_requires_auth(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 401 without authentication."""
        response = await unauthed_client.get(
            "/api/v1/shopify/install-url",
            params={"store_id": str(store.id), "shop": SHOPIFY_TEST_SHOP},
        )
        assert response.status_code == 401

    async def test_returns_signed_url(self, client: AsyncClient, store: Store) -> None:
        """Returns URL with store_id, ts, and sig params."""
        response = await client.get(
            "/api/v1/shopify/install-url",
            params={"store_id": str(store.id), "shop": SHOPIFY_TEST_SHOP},
        )

        assert response.status_code == 200
        data = response.json()
        assert "install_url" in data

        url = data["install_url"]
        assert f"store_id={store.id}" in url
        assert "ts=" in url
        assert "sig=" in url
        assert f"shop={SHOPIFY_TEST_SHOP}" in url

    async def test_validates_shop_domain(self, client: AsyncClient, store: Store) -> None:
        """Rejects shop not ending in .myshopify.com."""
        response = await client.get(
            "/api/v1/shopify/install-url",
            params={"store_id": str(store.id), "shop": "not-a-shopify-domain.com"},
        )

        assert response.status_code == 400
        assert "Invalid shop domain" in response.json()["detail"]

    async def test_validates_store_ownership(self, client: AsyncClient, other_store: Store) -> None:
        """Returns 404 if store belongs to different org."""
        response = await client.get(
            "/api/v1/shopify/install-url",
            params={"store_id": str(other_store.id), "shop": SHOPIFY_TEST_SHOP},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Route Tests: GET /api/v1/shopify/install
# ---------------------------------------------------------------------------


class TestInstallRoute:
    """Tests for the install endpoint (OAuth initiation)."""

    def _sign(self, store_id: str, ts: int) -> str:
        """Helper to sign install tokens."""
        msg = f"{store_id}:{ts}"
        return hmac.new(SHOPIFY_TEST_SECRET_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()

    async def test_validates_signature(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 403 for tampered signature."""
        ts = int(time.time())

        response = await unauthed_client.get(
            "/api/v1/shopify/install",
            params={
                "shop": SHOPIFY_TEST_SHOP,
                "store_id": str(store.id),
                "ts": ts,
                "sig": "invalid-signature",
            },
            follow_redirects=False,
        )

        assert response.status_code == 403
        assert "Invalid signature" in response.json()["detail"]

    async def test_rejects_expired_token(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 403 if timestamp is > 5 minutes old."""
        ts = int(time.time()) - 400  # 6+ minutes ago
        sig = self._sign(str(store.id), ts)

        response = await unauthed_client.get(
            "/api/v1/shopify/install",
            params={
                "shop": SHOPIFY_TEST_SHOP,
                "store_id": str(store.id),
                "ts": ts,
                "sig": sig,
            },
            follow_redirects=False,
        )

        assert response.status_code == 403
        assert "Expired" in response.json()["detail"]

    async def test_validates_shop_domain(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 400 for invalid shop domain."""
        ts = int(time.time())
        sig = self._sign(str(store.id), ts)

        response = await unauthed_client.get(
            "/api/v1/shopify/install",
            params={
                "shop": "invalid-domain.com",
                "store_id": str(store.id),
                "ts": ts,
                "sig": sig,
            },
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "Invalid shop domain" in response.json()["detail"]

    async def test_stores_nonce_in_redis(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
    ) -> None:
        """Nonce is stored in Redis."""
        ts = int(time.time())
        sig = self._sign(str(store.id), ts)

        response = await unauthed_client.get(
            "/api/v1/shopify/install",
            params={
                "shop": SHOPIFY_TEST_SHOP,
                "store_id": str(store.id),
                "ts": ts,
                "sig": sig,
            },
            follow_redirects=False,
        )

        assert response.status_code == 307

        # Find the nonce from the redirect URL
        location = response.headers["location"]
        parsed = urlparse(location)
        query_params = parse_qs(parsed.query)
        nonce = query_params["state"][0]

        # Verify it's stored in Redis
        stored = await fake_redis.get(f"shopify_oauth:{nonce}")
        assert stored is not None
        assert str(store.id) in stored
        assert SHOPIFY_TEST_SHOP in stored

    async def test_redirects_to_shopify(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns RedirectResponse to Shopify OAuth URL."""
        ts = int(time.time())
        sig = self._sign(str(store.id), ts)

        response = await unauthed_client.get(
            "/api/v1/shopify/install",
            params={
                "shop": SHOPIFY_TEST_SHOP,
                "store_id": str(store.id),
                "ts": ts,
                "sig": sig,
            },
            follow_redirects=False,
        )

        assert response.status_code == 307
        location = response.headers["location"]
        assert f"https://{SHOPIFY_TEST_SHOP}/admin/oauth/authorize" in location


# ---------------------------------------------------------------------------
# Route Tests: GET /api/v1/shopify/callback
# ---------------------------------------------------------------------------


class TestCallbackRoute:
    """Tests for the OAuth callback endpoint."""

    async def test_verifies_hmac(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
    ) -> None:
        """Returns 400 for invalid HMAC."""
        # Set up nonce in Redis
        nonce = "test-nonce"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:{SHOPIFY_TEST_SHOP}")

        response = await unauthed_client.get(
            "/api/v1/shopify/callback",
            params={
                "code": "auth-code",
                "shop": SHOPIFY_TEST_SHOP,
                "state": nonce,
                "hmac": "invalid-hmac",
            },
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "HMAC" in response.json()["detail"]

    async def test_verifies_nonce(
        self,
        unauthed_client: AsyncClient,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
    ) -> None:
        """Returns 400 if state/nonce not in Redis."""
        params = {
            "code": "auth-code",
            "shop": SHOPIFY_TEST_SHOP,
            "state": "nonexistent-nonce",
        }
        params["hmac"] = shopify_oauth_hmac(params)

        response = await unauthed_client.get(
            "/api/v1/shopify/callback",
            params=params,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "Invalid or expired state" in response.json()["detail"]

    async def test_verifies_shop_match(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
    ) -> None:
        """Returns 400 if shop doesn't match stored value."""
        nonce = "test-nonce"
        # Store expects "expected-shop.myshopify.com"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:expected-shop.myshopify.com")

        params = {
            "code": "auth-code",
            "shop": "different-shop.myshopify.com",  # Different shop
            "state": nonce,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        response = await unauthed_client.get(
            "/api/v1/shopify/callback",
            params=params,
            follow_redirects=False,
        )

        assert response.status_code == 400
        assert "Shop mismatch" in response.json()["detail"]

    async def test_creates_integration(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
        mock_shopify_token_exchange: MagicMock,
        mock_shopify_client: MagicMock,
        mock_celery_shopify_tasks: dict[str, MagicMock],
        db_session: Any,
    ) -> None:
        """Creates StoreIntegration with status ACTIVE."""
        nonce = "test-nonce"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:{SHOPIFY_TEST_SHOP}")

        params = {
            "code": "auth-code",
            "shop": SHOPIFY_TEST_SHOP,
            "state": nonce,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        response = await unauthed_client.get(
            "/api/v1/shopify/callback",
            params=params,
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert "connected=true" in response.headers["location"]

        # Verify integration was created
        from sqlalchemy import select

        stmt = select(StoreIntegration).where(StoreIntegration.store_id == store.id)
        result = await db_session.execute(stmt)
        integration = result.scalar_one_or_none()

        assert integration is not None
        assert integration.platform == PlatformType.SHOPIFY
        assert integration.status == IntegrationStatus.ACTIVE
        assert integration.platform_domain == SHOPIFY_TEST_SHOP
        assert "access_token" in integration.credentials

    async def test_updates_existing_integration(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        fake_redis: Any,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
        mock_shopify_token_exchange: MagicMock,
        mock_shopify_client: MagicMock,
        mock_celery_shopify_tasks: dict[str, MagicMock],
        db_session: Any,
    ) -> None:
        """Existing integration is updated, not duplicated."""
        # Create existing integration
        existing = await integration_factory(
            store_id=store.id,
            platform=PlatformType.SHOPIFY,
            platform_domain="old-shop.myshopify.com",
            status=IntegrationStatus.DISCONNECTED,
        )

        nonce = "test-nonce"
        new_shop = "new-shop.myshopify.com"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:{new_shop}")

        params = {
            "code": "auth-code",
            "shop": new_shop,
            "state": nonce,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        response = await unauthed_client.get(
            "/api/v1/shopify/callback",
            params=params,
            follow_redirects=False,
        )

        assert response.status_code == 307

        # Verify integration was updated, not duplicated
        from sqlalchemy import func, select

        count_stmt = (
            select(func.count())
            .select_from(StoreIntegration)
            .where(StoreIntegration.store_id == store.id)
        )
        count = await db_session.scalar(count_stmt)
        assert count == 1

        # Verify it was updated
        await db_session.refresh(existing)
        assert existing.platform_domain == new_shop
        assert existing.status == IntegrationStatus.ACTIVE

    async def test_triggers_sync_task(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
        mock_shopify_token_exchange: MagicMock,
        mock_shopify_client: MagicMock,
        mock_celery_shopify_tasks: dict[str, MagicMock],
    ) -> None:
        """sync_products_full.delay() is called after successful callback."""
        nonce = "test-nonce"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:{SHOPIFY_TEST_SHOP}")

        params = {
            "code": "auth-code",
            "shop": SHOPIFY_TEST_SHOP,
            "state": nonce,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        await unauthed_client.get(
            "/api/v1/shopify/callback",
            params=params,
            follow_redirects=False,
        )

        mock_celery_shopify_tasks["sync_products_full"].delay.assert_called_once_with(str(store.id))

    async def test_token_exchange_failure_redirects_with_error(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
    ) -> None:
        """Redirects to frontend with ?error=token_exchange_failed on HTTP error."""
        nonce = "test-nonce"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:{SHOPIFY_TEST_SHOP}")

        params = {
            "code": "bad-code",
            "shop": SHOPIFY_TEST_SHOP,
            "state": nonce,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        # Mock token exchange to fail
        with patch("app.api.v1.shopify.exchange_code_for_token") as mock_exchange:
            mock_exchange.side_effect = HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
            )

            response = await unauthed_client.get(
                "/api/v1/shopify/callback",
                params=params,
                follow_redirects=False,
            )

        assert response.status_code == 307
        assert "error=token_exchange_failed" in response.headers["location"]

    async def test_encrypts_token(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        fake_redis: Any,
        shopify_oauth_hmac: Callable[[dict[str, str]], str],
        mock_shopify_token_exchange: MagicMock,
        mock_shopify_client: MagicMock,
        mock_celery_shopify_tasks: dict[str, MagicMock],
        db_session: Any,
    ) -> None:
        """Stored credentials contain encrypted token (not plaintext)."""
        nonce = "test-nonce"
        await fake_redis.set(f"shopify_oauth:{nonce}", f"{store.id}:{SHOPIFY_TEST_SHOP}")

        params = {
            "code": "auth-code",
            "shop": SHOPIFY_TEST_SHOP,
            "state": nonce,
        }
        params["hmac"] = shopify_oauth_hmac(params)

        await unauthed_client.get(
            "/api/v1/shopify/callback",
            params=params,
            follow_redirects=False,
        )

        from sqlalchemy import select

        stmt = select(StoreIntegration).where(StoreIntegration.store_id == store.id)
        result = await db_session.execute(stmt)
        integration = result.scalar_one()

        # Token should be encrypted (Fernet produces base64 starting with 'gAAA...')
        stored_token = integration.credentials["access_token"]
        assert stored_token != "shpat_test_access_token_123"  # Not plaintext
        assert stored_token.startswith("gAAA")  # Fernet prefix


# ---------------------------------------------------------------------------
# Route Tests: POST /api/v1/shopify/disconnect
# ---------------------------------------------------------------------------


class TestDisconnectRoute:
    """Tests for the disconnect endpoint."""

    async def test_requires_auth(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 401 without authentication."""
        response = await unauthed_client.post(
            "/api/v1/shopify/disconnect",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 401

    async def test_validates_store_ownership(self, client: AsyncClient, other_store: Store) -> None:
        """Returns 404 for store in different org."""
        response = await client.post(
            "/api/v1/shopify/disconnect",
            params={"store_id": str(other_store.id)},
        )
        assert response.status_code == 404

    async def test_returns_404_if_no_integration(self, client: AsyncClient, store: Store) -> None:
        """Returns 404 if no integration exists."""
        response = await client.post(
            "/api/v1/shopify/disconnect",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 404
        assert "No Shopify integration found" in response.json()["detail"]

    async def test_marks_integration_disconnected(
        self,
        client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        mock_shopify_client: MagicMock,
        db_session: Any,
    ) -> None:
        """Sets status to DISCONNECTED and clears credentials."""
        encrypted_token = encrypt_token("shpat_token")
        integration = await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        # Mock ShopifyClient at the route level (where it's instantiated)
        with patch("app.api.v1.shopify.ShopifyClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance.delete_webhooks = AsyncMock()
            mock_class.return_value = mock_instance

            response = await client.post(
                "/api/v1/shopify/disconnect",
                params={"store_id": str(store.id)},
            )

        assert response.status_code == 200
        assert response.json()["status"] == "disconnected"

        await db_session.refresh(integration)
        assert integration.status == IntegrationStatus.DISCONNECTED
        assert integration.credentials == {}

    async def test_calls_delete_webhooks(
        self,
        client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
    ) -> None:
        """Calls client.delete_webhooks() for active integration."""
        encrypted_token = encrypt_token("shpat_token")
        await integration_factory(
            store_id=store.id,
            credentials={"access_token": encrypted_token},
            status=IntegrationStatus.ACTIVE,
        )

        with patch("app.api.v1.shopify.ShopifyClient") as mock_class:
            mock_instance = MagicMock()
            mock_instance.delete_webhooks = AsyncMock()
            mock_class.return_value = mock_instance

            await client.post(
                "/api/v1/shopify/disconnect",
                params={"store_id": str(store.id)},
            )

            mock_instance.delete_webhooks.assert_called_once()


# ---------------------------------------------------------------------------
# Route Tests: POST /api/v1/shopify/sync
# ---------------------------------------------------------------------------


class TestSyncRoute:
    """Tests for the manual sync trigger endpoint."""

    async def test_requires_auth(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 401 without authentication."""
        response = await unauthed_client.post(
            "/api/v1/shopify/sync",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 401

    async def test_validates_store_ownership(self, client: AsyncClient, other_store: Store) -> None:
        """Returns 404 for store in different org."""
        response = await client.post(
            "/api/v1/shopify/sync",
            params={"store_id": str(other_store.id)},
        )
        assert response.status_code == 404

    async def test_requires_active_integration(
        self,
        client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
    ) -> None:
        """Returns 404 if integration is disconnected."""
        await integration_factory(
            store_id=store.id,
            status=IntegrationStatus.DISCONNECTED,
        )

        response = await client.post(
            "/api/v1/shopify/sync",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 404
        assert "No active Shopify integration" in response.json()["detail"]

    async def test_triggers_task(
        self,
        client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        mock_celery_shopify_tasks: dict[str, MagicMock],
    ) -> None:
        """sync_products_full.delay() is called."""
        await integration_factory(
            store_id=store.id,
            status=IntegrationStatus.ACTIVE,
        )

        response = await client.post(
            "/api/v1/shopify/sync",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "syncing"

        mock_celery_shopify_tasks["sync_products_full"].delay.assert_called_once_with(str(store.id))


# ---------------------------------------------------------------------------
# Route Tests: GET /api/v1/shopify/status
# ---------------------------------------------------------------------------


class TestStatusRoute:
    """Tests for the connection status endpoint."""

    async def test_requires_auth(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Returns 401 without authentication."""
        response = await unauthed_client.get(
            "/api/v1/shopify/status",
            params={"store_id": str(store.id)},
        )
        assert response.status_code == 401

    async def test_returns_disconnected_if_no_integration(
        self, client: AsyncClient, store: Store
    ) -> None:
        """Returns status='disconnected' when no integration exists."""
        response = await client.get(
            "/api/v1/shopify/status",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disconnected"
        assert data["platform"] == "shopify"
        assert data["product_count"] == 0

    async def test_returns_connection_info(
        self,
        client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
    ) -> None:
        """Returns platform_domain, status, and product_count."""
        await integration_factory(
            store_id=store.id,
            platform_domain="my-shop.myshopify.com",
            status=IntegrationStatus.ACTIVE,
        )

        response = await client.get(
            "/api/v1/shopify/status",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "shopify"
        assert data["platform_domain"] == "my-shop.myshopify.com"
        assert data["status"] == "active"

    async def test_counts_products_correctly(
        self,
        client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        product_factory: Callable[..., Any],
    ) -> None:
        """product_count matches actual product count in DB."""
        await integration_factory(store_id=store.id, status=IntegrationStatus.ACTIVE)

        # Create 3 products
        for i in range(3):
            await product_factory(store_id=store.id, title=f"Product {i}")

        response = await client.get(
            "/api/v1/shopify/status",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        assert response.json()["product_count"] == 3

    async def test_validates_store_ownership(self, client: AsyncClient, other_store: Store) -> None:
        """Returns 404 for store in different org."""
        response = await client.get(
            "/api/v1/shopify/status",
            params={"store_id": str(other_store.id)},
        )
        assert response.status_code == 404

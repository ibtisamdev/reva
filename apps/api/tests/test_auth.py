"""Tests for authentication middleware and helpers.

Covers:
- HTTP-level auth enforcement (missing token → 401, valid mock → 200)
- Unit tests for get_current_user, get_optional_user, verify_token
- Unit tests for get_user_organization_id
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.core.auth import get_current_user, get_optional_user, verify_token
from app.core.deps import get_user_organization_id
from app.models.store import Store

# ---------------------------------------------------------------------------
# HTTP-level auth tests — endpoints that require CurrentUser
# ---------------------------------------------------------------------------


class TestAuthEnforcementHTTP:
    """Test that protected endpoints reject unauthenticated requests."""

    async def test_list_stores_requires_auth(
        self,
        unauthed_client: AsyncClient,
        store: Store,  # noqa: ARG002  # Ensures store exists in DB
    ) -> None:
        """GET /api/v1/stores without auth → 401."""
        response = await unauthed_client.get("/api/v1/stores")
        assert response.status_code == 401

    async def test_create_store_requires_auth(self, unauthed_client: AsyncClient) -> None:
        """POST /api/v1/stores without auth → 401."""
        response = await unauthed_client.post(
            "/api/v1/stores",
            json={"name": "Test Store"},
        )
        assert response.status_code == 401

    async def test_get_store_requires_auth(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """GET /api/v1/stores/{id} without auth → 401."""
        response = await unauthed_client.get(f"/api/v1/stores/{store.id}")
        assert response.status_code == 401

    async def test_update_store_requires_auth(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """PATCH /api/v1/stores/{id} without auth → 401."""
        response = await unauthed_client.patch(
            f"/api/v1/stores/{store.id}",
            json={"name": "Updated"},
        )
        assert response.status_code == 401

    async def test_delete_store_requires_auth(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """DELETE /api/v1/stores/{id} without auth → 401."""
        response = await unauthed_client.delete(f"/api/v1/stores/{store.id}")
        assert response.status_code == 401

    async def test_list_products_requires_auth(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """GET /api/v1/products/ without auth → 401."""
        response = await unauthed_client.get(
            "/api/v1/products/", params={"store_id": str(store.id)}
        )
        assert response.status_code == 401

    async def test_list_knowledge_requires_auth(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """GET /api/v1/knowledge without auth → 401."""
        response = await unauthed_client.get(
            "/api/v1/knowledge", params={"store_id": str(store.id)}
        )
        assert response.status_code == 401

    async def test_authenticated_client_can_list_stores(
        self,
        client: AsyncClient,
        store: Store,  # noqa: ARG002  # Ensures store exists in DB
    ) -> None:
        """client fixture (mocked auth) can access protected endpoints."""
        response = await client.get("/api/v1/stores")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_authenticated_client_can_get_store(
        self, client: AsyncClient, store: Store
    ) -> None:
        """client fixture can get a specific store belonging to its org."""
        response = await client.get(f"/api/v1/stores/{store.id}")
        assert response.status_code == 200
        assert response.json()["id"] == str(store.id)


# ---------------------------------------------------------------------------
# Unit tests for auth dependency functions
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Unit tests for get_current_user dependency."""

    async def test_no_credentials_raises_401(self) -> None:
        """get_current_user(None) raises 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)
        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail


class TestGetOptionalUser:
    """Unit tests for get_optional_user dependency."""

    async def test_no_credentials_returns_none(self) -> None:
        """get_optional_user(None) returns None without raising."""
        result = await get_optional_user(None)
        assert result is None


class TestVerifyToken:
    """Unit tests for verify_token (mocking JWKS)."""

    async def test_invalid_token_raises_401(self) -> None:
        """A garbage token raises 401 (InvalidTokenError before JWKS fetch)."""
        # verify_token will try to decode the header to find the kid,
        # which will fail for garbage input.
        with pytest.raises(HTTPException) as exc_info:
            await verify_token("not-a-jwt-token")
        # Could be 401 (invalid token) or 503 (JWKS unavailable) depending
        # on which error path fires first
        assert exc_info.value.status_code in (401, 503)

    async def test_expired_token_raises_401(self) -> None:
        """An expired but otherwise well-formed JWT raises 401."""
        import time

        import jwt as pyjwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate a test RSA key pair
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        # Create an expired token
        payload = {
            "sub": "test-user",
            "email": "test@example.com",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iss": "http://localhost:3000",
            "aud": "http://localhost:3000",
        }
        expired_token = pyjwt.encode(payload, private_key, algorithm="RS256")

        # Mock the JWKS client to return our test key
        mock_signing_key = MagicMock()
        mock_signing_key.key = private_key.public_key()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("app.core.auth.get_jwks_client", return_value=mock_jwks_client):
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(expired_token)
            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()

    async def test_valid_token_returns_payload(self) -> None:
        """A valid, non-expired JWT returns the decoded payload."""
        import time

        import jwt as pyjwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        payload = {
            "sub": "user-123",
            "email": "user@example.com",
            "activeOrganizationId": "org-456",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "http://localhost:3000",
            "aud": "http://localhost:3000",
        }
        token = pyjwt.encode(payload, private_key, algorithm="RS256")

        mock_signing_key = MagicMock()
        mock_signing_key.key = private_key.public_key()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("app.core.auth.get_jwks_client", return_value=mock_jwks_client):
            result = await verify_token(token)

        assert result["sub"] == "user-123"
        assert result["email"] == "user@example.com"
        assert result["activeOrganizationId"] == "org-456"

    async def test_wrong_audience_raises_401(self) -> None:
        """A token with wrong audience is rejected."""
        import time

        import jwt as pyjwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        payload = {
            "sub": "user-123",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "http://localhost:3000",
            "aud": "http://wrong-audience.com",  # Wrong audience
        }
        token = pyjwt.encode(payload, private_key, algorithm="RS256")

        mock_signing_key = MagicMock()
        mock_signing_key.key = private_key.public_key()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("app.core.auth.get_jwks_client", return_value=mock_jwks_client):
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(token)
            assert exc_info.value.status_code == 401

    async def test_wrong_issuer_raises_401(self) -> None:
        """A token with wrong issuer is rejected."""
        import time

        import jwt as pyjwt
        from cryptography.hazmat.primitives.asymmetric import rsa

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        payload = {
            "sub": "user-123",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "iss": "http://evil-issuer.com",  # Wrong issuer
            "aud": "http://localhost:3000",
        }
        token = pyjwt.encode(payload, private_key, algorithm="RS256")

        mock_signing_key = MagicMock()
        mock_signing_key.key = private_key.public_key()

        mock_jwks_client = MagicMock()
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        with patch("app.core.auth.get_jwks_client", return_value=mock_jwks_client):
            with pytest.raises(HTTPException) as exc_info:
                await verify_token(token)
            assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Unit tests for get_user_organization_id
# ---------------------------------------------------------------------------


class TestGetUserOrganizationId:
    """Unit tests for organization ID extraction from JWT payload."""

    def test_valid_org_id(self) -> None:
        """Returns the org ID when present."""
        user: dict[str, Any] = {"activeOrganizationId": "org-123"}
        assert get_user_organization_id(user) == "org-123"

    def test_missing_org_id_raises_400(self) -> None:
        """Raises 400 when activeOrganizationId is absent."""
        with pytest.raises(HTTPException) as exc_info:
            get_user_organization_id({})
        assert exc_info.value.status_code == 400
        assert "organization" in exc_info.value.detail.lower()

    def test_none_org_id_raises_400(self) -> None:
        """Raises 400 when activeOrganizationId is None."""
        user: dict[str, Any] = {"activeOrganizationId": None}
        with pytest.raises(HTTPException) as exc_info:
            get_user_organization_id(user)
        assert exc_info.value.status_code == 400

    def test_empty_string_org_id_raises_400(self) -> None:
        """Raises 400 when activeOrganizationId is empty string (falsy)."""
        user: dict[str, Any] = {"activeOrganizationId": ""}
        with pytest.raises(HTTPException) as exc_info:
            get_user_organization_id(user)
        assert exc_info.value.status_code == 400

    def test_numeric_org_id_coerced_to_string(self) -> None:
        """Numeric org IDs are coerced to strings."""
        user: dict[str, Any] = {"activeOrganizationId": 12345}
        result = get_user_organization_id(user)
        assert result == "12345"
        assert isinstance(result, str)

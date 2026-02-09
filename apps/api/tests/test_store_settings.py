"""Tests for store settings endpoints.

Covers:
- GET /api/v1/stores/settings (public — widget needs it)
- PATCH /api/v1/stores/settings (requires auth + org ownership)
- Default settings, partial updates, validation, auth enforcement
"""

import uuid
from typing import Any

from httpx import AsyncClient

from app.models.store import Store

# ---------------------------------------------------------------------------
# GET /api/v1/stores/settings (public)
# ---------------------------------------------------------------------------


class TestGetStoreSettings:
    """Tests for the public GET settings endpoint."""

    async def test_returns_default_settings_for_new_store(
        self, client: AsyncClient, store: Store
    ) -> None:
        """A store with no custom settings returns all defaults."""
        response = await client.get("/api/v1/stores/settings", params={"store_id": str(store.id)})
        assert response.status_code == 200
        widget = response.json()["widget"]
        assert widget["primary_color"] == "#0d9488"
        assert widget["welcome_message"] == "Hi! How can I help you today?"
        assert widget["position"] == "bottom-right"
        assert widget["agent_name"] == "Reva Support"

    async def test_returns_custom_settings_merged_with_defaults(
        self, client: AsyncClient, store_factory: Any
    ) -> None:
        """Custom settings are merged on top of defaults."""
        store = await store_factory(
            settings_data={"widget": {"primary_color": "#ff0000", "agent_name": "Acme Bot"}}
        )
        response = await client.get("/api/v1/stores/settings", params={"store_id": str(store.id)})
        assert response.status_code == 200
        widget = response.json()["widget"]
        # Custom values
        assert widget["primary_color"] == "#ff0000"
        assert widget["agent_name"] == "Acme Bot"
        # Defaults for fields not customized
        assert widget["welcome_message"] == "Hi! How can I help you today?"
        assert widget["position"] == "bottom-right"

    async def test_inactive_store_returns_404(
        self, client: AsyncClient, store_factory: Any
    ) -> None:
        """Inactive (soft-deleted) stores are not accessible."""
        store = await store_factory(is_active=False)
        response = await client.get("/api/v1/stores/settings", params={"store_id": str(store.id)})
        assert response.status_code == 404

    async def test_nonexistent_store_returns_404(self, client: AsyncClient) -> None:
        """Random UUID returns 404."""
        response = await client.get(
            "/api/v1/stores/settings", params={"store_id": str(uuid.uuid4())}
        )
        assert response.status_code == 404

    async def test_missing_store_id_returns_422(self, client: AsyncClient) -> None:
        """Missing required store_id query param → 422."""
        response = await client.get("/api/v1/stores/settings")
        assert response.status_code == 422

    async def test_public_access_any_active_store(
        self, unauthed_client: AsyncClient, store: Store
    ) -> None:
        """Unauthenticated clients can read settings (widget use case)."""
        response = await unauthed_client.get(
            "/api/v1/stores/settings", params={"store_id": str(store.id)}
        )
        assert response.status_code == 200
        assert "widget" in response.json()


# ---------------------------------------------------------------------------
# PATCH /api/v1/stores/settings (requires auth)
# ---------------------------------------------------------------------------


class TestUpdateStoreSettings:
    """Tests for the authenticated PATCH settings endpoint."""

    async def test_update_single_field(self, client: AsyncClient, store: Store) -> None:
        """Updating only primary_color keeps other settings at defaults."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"primary_color": "#123456"}},
        )
        assert response.status_code == 200
        widget = response.json()["widget"]
        assert widget["primary_color"] == "#123456"
        # Other fields still defaults
        assert widget["welcome_message"] == "Hi! How can I help you today?"
        assert widget["agent_name"] == "Reva Support"

    async def test_update_all_fields(self, client: AsyncClient, store: Store) -> None:
        """Updating all widget fields at once."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={
                "widget": {
                    "primary_color": "#abcdef",
                    "welcome_message": "Welcome!",
                    "position": "bottom-left",
                    "agent_name": "Custom Bot",
                }
            },
        )
        assert response.status_code == 200
        widget = response.json()["widget"]
        assert widget["primary_color"] == "#abcdef"
        assert widget["welcome_message"] == "Welcome!"
        assert widget["position"] == "bottom-left"
        assert widget["agent_name"] == "Custom Bot"

    async def test_invalid_hex_color_returns_422(self, client: AsyncClient, store: Store) -> None:
        """Non-hex color value is rejected by Pydantic validation."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"primary_color": "not-a-hex"}},
        )
        assert response.status_code == 422

    async def test_invalid_position_returns_422(self, client: AsyncClient, store: Store) -> None:
        """Invalid position value is rejected."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"position": "top-center"}},
        )
        assert response.status_code == 422

    async def test_sequential_updates_preserve_previous(
        self, client: AsyncClient, store: Store
    ) -> None:
        """Updating color, then agent_name, preserves the previously set color."""
        # First update: set color
        await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"primary_color": "#111111"}},
        )

        # Second update: set agent_name
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"agent_name": "New Bot"}},
        )
        assert response.status_code == 200
        widget = response.json()["widget"]
        # Color from first update should be preserved
        assert widget["primary_color"] == "#111111"
        assert widget["agent_name"] == "New Bot"

    async def test_requires_auth(self, unauthed_client: AsyncClient, store: Store) -> None:
        """Unauthenticated clients cannot update settings (security fix regression)."""
        response = await unauthed_client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={"widget": {"primary_color": "#000000"}},
        )
        assert response.status_code == 401

    async def test_wrong_org_returns_404(self, client: AsyncClient, other_store: Store) -> None:
        """Authenticated user cannot update another org's store settings."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(other_store.id)},
            json={"widget": {"primary_color": "#000000"}},
        )
        assert response.status_code == 404

    async def test_empty_body_is_noop(self, client: AsyncClient, store: Store) -> None:
        """PATCH with empty body (no widget key) is a valid no-op."""
        response = await client.patch(
            "/api/v1/stores/settings",
            params={"store_id": str(store.id)},
            json={},
        )
        assert response.status_code == 200
        # Settings should remain defaults
        widget = response.json()["widget"]
        assert widget["primary_color"] == "#0d9488"

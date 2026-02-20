"""Tests for cart recovery: webhook endpoints, tasks, service, and API routes.

Covers:
- Checkout webhook processing (create/update)
- Order completion webhook
- Abandonment detection task
- Recovery sequence lifecycle
- Recovery API endpoints (sequences, checkouts, analytics, settings)
- Unsubscribe flow
- Widget recovery check
"""

import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abandoned_checkout import AbandonedCheckout, CheckoutStatus
from app.models.email_unsubscribe import EmailUnsubscribe
from app.models.recovery_sequence import SequenceStatus
from app.models.store import Store

# ---------------------------------------------------------------------------
# Webhook endpoint tests
# ---------------------------------------------------------------------------


class TestCheckoutWebhooks:
    """Tests for POST /api/v1/webhooks/shopify/checkouts-create and checkouts-update."""

    @pytest.mark.asyncio
    async def test_checkout_create_dispatches_task(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        mock_celery_recovery_tasks: dict[str, MagicMock],
    ) -> None:
        """Valid checkout/create webhook dispatches process_checkout_webhook task."""
        shop = "test-store.myshopify.com"
        await integration_factory(store_id=store.id, platform_domain=shop)

        body = json.dumps({"id": 123, "email": "test@example.com"}).encode()
        headers = shopify_webhook_headers(body, shop)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/checkouts-create",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        mock_celery_recovery_tasks["process_checkout_webhook"].delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_checkout_update_dispatches_task(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        mock_celery_recovery_tasks: dict[str, MagicMock],
    ) -> None:
        """Valid checkout/update webhook dispatches process_checkout_webhook task."""
        shop = "test-store.myshopify.com"
        await integration_factory(store_id=store.id, platform_domain=shop)

        body = json.dumps({"id": 456, "email": "update@example.com"}).encode()
        headers = shopify_webhook_headers(body, shop)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/checkouts-update",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        mock_celery_recovery_tasks["process_checkout_webhook"].delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_signature_returns_401(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
    ) -> None:
        """Invalid HMAC signature returns 401."""
        shop = "test-store.myshopify.com"
        await integration_factory(store_id=store.id, platform_domain=shop)

        body = json.dumps({"id": 123}).encode()
        headers = {
            "X-Shopify-Hmac-Sha256": "invalid-signature",
            "X-Shopify-Shop-Domain": shop,
            "Content-Type": "application/json",
        }

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/checkouts-create",
            content=body,
            headers=headers,
        )

        assert response.status_code == 401


class TestOrderWebhook:
    """Tests for POST /api/v1/webhooks/shopify/orders-create."""

    @pytest.mark.asyncio
    async def test_order_create_dispatches_task(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        integration_factory: Callable[..., Any],
        shopify_webhook_headers: Callable[[bytes, str], dict[str, str]],
        mock_celery_recovery_tasks: dict[str, MagicMock],
    ) -> None:
        """Valid order/create webhook dispatches process_order_completed task."""
        shop = "test-store.myshopify.com"
        await integration_factory(store_id=store.id, platform_domain=shop)

        body = json.dumps(
            {"id": 789, "email": "buyer@example.com", "checkout_token": "tok_123"}
        ).encode()
        headers = shopify_webhook_headers(body, shop)

        response = await unauthed_client.post(
            "/api/v1/webhooks/shopify/orders-create",
            content=body,
            headers=headers,
        )

        assert response.status_code == 200
        mock_celery_recovery_tasks["process_order_completed"].delay.assert_called_once()


# ---------------------------------------------------------------------------
# Task tests (async implementations directly)
# ---------------------------------------------------------------------------


class TestProcessCheckoutWebhookTask:
    """Tests for the checkout webhook processing async implementation."""

    @pytest.mark.asyncio
    async def test_upserts_checkout(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_async_session_maker_recovery: None,
        sample_shopify_checkout: dict[str, Any],
    ) -> None:
        """Processing a checkout webhook creates an AbandonedCheckout record."""
        from app.workers.tasks.recovery import _process_checkout_webhook_async

        result = await _process_checkout_webhook_async(
            store.id, "checkouts/create", sample_shopify_checkout
        )

        assert result["status"] == "processed"
        assert result["checkout_id"] == str(sample_shopify_checkout["id"])

        # Verify record was created
        stmt = select(AbandonedCheckout).where(AbandonedCheckout.store_id == store.id)
        checkout = (await db_session.execute(stmt)).scalar_one_or_none()
        assert checkout is not None
        assert checkout.customer_email == "shopper@example.com"
        assert checkout.customer_name == "Jane Doe"
        assert float(checkout.total_price) == 129.99
        assert len(checkout.line_items) == 2

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(
        self,
        db_session: AsyncSession,
        store: Store,
        mock_async_session_maker_recovery: None,
        sample_shopify_checkout: dict[str, Any],
    ) -> None:
        """Processing same checkout ID updates existing record (upsert)."""
        from app.workers.tasks.recovery import _process_checkout_webhook_async

        await _process_checkout_webhook_async(store.id, "checkouts/create", sample_shopify_checkout)

        # Update email and re-process
        sample_shopify_checkout["email"] = "updated@example.com"
        sample_shopify_checkout["total_price"] = "199.99"
        await _process_checkout_webhook_async(store.id, "checkouts/update", sample_shopify_checkout)

        stmt = select(AbandonedCheckout).where(AbandonedCheckout.store_id == store.id)
        checkouts = (await db_session.execute(stmt)).scalars().all()
        assert len(checkouts) == 1
        assert checkouts[0].customer_email == "updated@example.com"
        assert float(checkouts[0].total_price) == 199.99

    @pytest.mark.asyncio
    async def test_ignores_missing_id(
        self,
        store: Store,
        mock_async_session_maker_recovery: None,
    ) -> None:
        """Checkout with no ID is ignored."""
        from app.workers.tasks.recovery import _process_checkout_webhook_async

        result = await _process_checkout_webhook_async(store.id, "checkouts/create", {})
        assert result["status"] == "ignored"


class TestProcessOrderCompletedTask:
    """Tests for the order completed processing async implementation."""

    @pytest.mark.asyncio
    async def test_marks_checkout_completed(
        self,
        db_session: AsyncSession,
        store: Store,
        abandoned_checkout_factory: Callable[..., Any],
        mock_async_session_maker_recovery: None,
    ) -> None:
        """Order completion marks matching abandoned checkout as completed."""
        checkout = await abandoned_checkout_factory(
            store_id=store.id,
            shopify_checkout_token="tok_match",
            status=CheckoutStatus.ABANDONED,
        )

        from app.workers.tasks.recovery import _process_order_completed_async

        with patch("app.workers.tasks.recovery.stop_sequences_for_email"):
            result = await _process_order_completed_async(
                store.id,
                {"id": 999, "checkout_token": "tok_match", "email": "shopper@example.com"},
            )

        assert result["status"] == "completed"
        assert result["checkouts_updated"] == 1

        await db_session.refresh(checkout)
        assert checkout.status == CheckoutStatus.COMPLETED
        assert checkout.completed_order_id == "999"

    @pytest.mark.asyncio
    async def test_matches_by_email_fallback(
        self,
        db_session: AsyncSession,
        store: Store,
        abandoned_checkout_factory: Callable[..., Any],
        mock_async_session_maker_recovery: None,
    ) -> None:
        """When no checkout_token, falls back to email matching."""
        checkout = await abandoned_checkout_factory(
            store_id=store.id,
            shopify_checkout_token=None,
            customer_email="buyer@example.com",
            status=CheckoutStatus.ABANDONED,
        )

        from app.workers.tasks.recovery import _process_order_completed_async

        with patch("app.workers.tasks.recovery.stop_sequences_for_email"):
            result = await _process_order_completed_async(
                store.id,
                {"id": 888, "email": "buyer@example.com"},
            )

        assert result["status"] == "completed"
        await db_session.refresh(checkout)
        assert checkout.status == CheckoutStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_ignores_no_email_or_token(
        self,
        store: Store,
        mock_async_session_maker_recovery: None,
    ) -> None:
        """Order with no email or checkout_token is ignored."""
        from app.workers.tasks.recovery import _process_order_completed_async

        result = await _process_order_completed_async(store.id, {"id": 777})
        assert result["status"] == "ignored"


class TestCheckAbandonedCheckoutsTask:
    """Tests for the periodic abandonment detection task."""

    @pytest.mark.asyncio
    async def test_detects_stale_checkouts(
        self,
        db_session: AsyncSession,
        store_factory: Callable[..., Any],
        abandoned_checkout_factory: Callable[..., Any],
        mock_async_session_maker_recovery: None,
    ) -> None:
        """Stale active checkouts are detected as abandoned."""
        store = await store_factory(
            settings_data={
                "recovery": {
                    "enabled": True,
                    "abandonment_threshold_minutes": 60,
                    "min_cart_value": 0,
                    "exclude_email_patterns": [],
                }
            }
        )

        checkout = await abandoned_checkout_factory(store_id=store.id)
        # Backdate updated_at to make it stale
        checkout.updated_at = datetime.now(UTC) - timedelta(hours=2)
        await db_session.commit()

        from app.workers.tasks.recovery import _check_abandoned_checkouts_async

        with patch("app.workers.tasks.recovery.start_recovery_sequence"):
            result = await _check_abandoned_checkouts_async()

        assert result["detected"] == 1

        await db_session.refresh(checkout)
        assert checkout.status == CheckoutStatus.ABANDONED
        assert checkout.abandonment_detected_at is not None

    @pytest.mark.asyncio
    async def test_skips_disabled_stores(
        self,
        store_factory: Callable[..., Any],
        abandoned_checkout_factory: Callable[..., Any],
        db_session: AsyncSession,
        mock_async_session_maker_recovery: None,
    ) -> None:
        """Stores with recovery disabled are skipped."""
        store = await store_factory(settings_data={"recovery": {"enabled": False}})
        checkout = await abandoned_checkout_factory(store_id=store.id)
        checkout.updated_at = datetime.now(UTC) - timedelta(hours=2)
        await db_session.commit()

        from app.workers.tasks.recovery import _check_abandoned_checkouts_async

        result = await _check_abandoned_checkouts_async()
        assert result["detected"] == 0

    @pytest.mark.asyncio
    async def test_excludes_email_patterns(
        self,
        db_session: AsyncSession,
        store_factory: Callable[..., Any],
        abandoned_checkout_factory: Callable[..., Any],
        mock_async_session_maker_recovery: None,
    ) -> None:
        """Emails matching exclusion patterns are not flagged."""
        store = await store_factory(
            settings_data={
                "recovery": {
                    "enabled": True,
                    "abandonment_threshold_minutes": 60,
                    "min_cart_value": 0,
                    "exclude_email_patterns": [r"@internal\.com$"],
                }
            }
        )
        checkout = await abandoned_checkout_factory(
            store_id=store.id,
            customer_email="admin@internal.com",
        )
        checkout.updated_at = datetime.now(UTC) - timedelta(hours=2)
        await db_session.commit()

        from app.workers.tasks.recovery import _check_abandoned_checkouts_async

        result = await _check_abandoned_checkouts_async()
        assert result["detected"] == 0


# ---------------------------------------------------------------------------
# API route tests (authenticated endpoints)
# ---------------------------------------------------------------------------


class TestRecoverySequencesEndpoint:
    """Tests for GET /api/v1/recovery/sequences."""

    @pytest.mark.asyncio
    async def test_list_sequences(
        self,
        client: AsyncClient,
        store: Store,
        abandoned_checkout_factory: Callable[..., Any],
        recovery_sequence_factory: Callable[..., Any],
    ) -> None:
        """Returns paginated list of recovery sequences."""
        checkout = await abandoned_checkout_factory(store_id=store.id)
        await recovery_sequence_factory(store_id=store.id, abandoned_checkout_id=checkout.id)

        response = await client.get(
            "/api/v1/recovery/sequences",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["customer_email"] == "shopper@example.com"
        assert data["items"][0]["total_steps"] == 4  # default timing has 4 steps

    @pytest.mark.asyncio
    async def test_list_sequences_other_store_not_found(
        self,
        client: AsyncClient,
        other_store: Store,
    ) -> None:
        """Cannot list sequences for a store in another org (returns 404)."""
        response = await client.get(
            "/api/v1/recovery/sequences",
            params={"store_id": str(other_store.id)},
        )

        assert response.status_code == 404


class TestStopSequenceEndpoint:
    """Tests for POST /api/v1/recovery/sequences/{id}/stop."""

    @pytest.mark.asyncio
    async def test_stop_active_sequence(
        self,
        client: AsyncClient,
        store: Store,
        abandoned_checkout_factory: Callable[..., Any],
        recovery_sequence_factory: Callable[..., Any],
        db_session: AsyncSession,
    ) -> None:
        """Stopping an active sequence returns 200."""
        checkout = await abandoned_checkout_factory(store_id=store.id)
        sequence = await recovery_sequence_factory(
            store_id=store.id, abandoned_checkout_id=checkout.id
        )

        response = await client.post(
            f"/api/v1/recovery/sequences/{sequence.id}/stop",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

        await db_session.refresh(sequence)
        assert sequence.status == SequenceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_stop_nonexistent_sequence(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Stopping a non-existent sequence returns 404."""
        response = await client.post(
            f"/api/v1/recovery/sequences/{uuid.uuid4()}/stop",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 404


class TestAbandonedCheckoutsEndpoint:
    """Tests for GET /api/v1/recovery/checkouts."""

    @pytest.mark.asyncio
    async def test_list_checkouts(
        self,
        client: AsyncClient,
        store: Store,
        abandoned_checkout_factory: Callable[..., Any],
    ) -> None:
        """Returns paginated list of abandoned checkouts."""
        await abandoned_checkout_factory(store_id=store.id)

        response = await client.get(
            "/api/v1/recovery/checkouts",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["customer_email"] == "shopper@example.com"

    @pytest.mark.asyncio
    async def test_list_checkouts_empty(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Returns empty list when no checkouts exist."""
        response = await client.get(
            "/api/v1/recovery/checkouts",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestRecoveryAnalyticsEndpoints:
    """Tests for GET /api/v1/recovery/analytics/summary and /trend."""

    @pytest.mark.asyncio
    async def test_summary_returns_zeros_when_empty(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Summary returns zero values when no data exists."""
        response = await client.get(
            "/api/v1/recovery/analytics/summary",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_abandoned"] == 0
        assert data["total_recovered"] == 0
        assert data["recovery_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_trend_returns_empty_list(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Trend returns empty list when no data exists."""
        response = await client.get(
            "/api/v1/recovery/analytics/trend",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        assert response.json() == []


class TestRecoverySettingsEndpoints:
    """Tests for GET/PATCH /api/v1/recovery/settings."""

    @pytest.mark.asyncio
    async def test_get_default_settings(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """Returns default recovery settings when none configured."""
        response = await client.get(
            "/api/v1/recovery/settings",
            params={"store_id": str(store.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["abandonment_threshold_minutes"] == 60

    @pytest.mark.asyncio
    async def test_update_settings(
        self,
        client: AsyncClient,
        store: Store,
    ) -> None:
        """PATCH updates recovery settings."""
        response = await client.patch(
            "/api/v1/recovery/settings",
            params={"store_id": str(store.id)},
            json={
                "enabled": True,
                "abandonment_threshold_minutes": 30,
                "min_cart_value": 25,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["abandonment_threshold_minutes"] == 30
        assert data["min_cart_value"] == 25

        # Verify persistence
        get_response = await client.get(
            "/api/v1/recovery/settings",
            params={"store_id": str(store.id)},
        )
        assert get_response.json()["enabled"] is True


# ---------------------------------------------------------------------------
# Public endpoint tests
# ---------------------------------------------------------------------------


class TestUnsubscribeEndpoint:
    """Tests for GET /api/v1/recovery/unsubscribe."""

    @pytest.mark.asyncio
    async def test_valid_token_unsubscribes(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        db_session: AsyncSession,
    ) -> None:
        """Valid JWT token creates unsubscribe record and returns HTML."""
        import jwt

        token = jwt.encode(
            {"store_id": str(store.id), "email": "shopper@example.com"},
            "test-secret-key-for-signing-install-tokens",
            algorithm="HS256",
        )

        response = await unauthed_client.get(
            "/api/v1/recovery/unsubscribe",
            params={"token": token},
        )

        assert response.status_code == 200
        assert "Unsubscribed" in response.text

        # Verify unsubscribe record exists
        stmt = select(EmailUnsubscribe).where(
            EmailUnsubscribe.store_id == store.id,
            EmailUnsubscribe.email == "shopper@example.com",
        )
        unsub = (await db_session.execute(stmt)).scalar_one_or_none()
        assert unsub is not None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_400(
        self,
        unauthed_client: AsyncClient,
    ) -> None:
        """Invalid JWT token returns 400 with error HTML."""
        response = await unauthed_client.get(
            "/api/v1/recovery/unsubscribe",
            params={"token": "invalid.jwt.token"},
        )

        assert response.status_code == 400
        assert "Invalid" in response.text


class TestRecoveryCheckEndpoint:
    """Tests for GET /api/v1/recovery/check (widget popup)."""

    @pytest.mark.asyncio
    async def test_no_recovery_when_no_session(
        self,
        unauthed_client: AsyncClient,
        store: Store,
    ) -> None:
        """Returns has_recovery=False when no matching session exists."""
        response = await unauthed_client.get(
            "/api/v1/recovery/check",
            params={
                "store_id": str(store.id),
                "session_id": "nonexistent-session",
            },
        )

        assert response.status_code == 200
        assert response.json()["has_recovery"] is False

    @pytest.mark.asyncio
    async def test_recovery_found_via_session(
        self,
        unauthed_client: AsyncClient,
        store: Store,
        conversation_factory: Callable[..., Any],
        abandoned_checkout_factory: Callable[..., Any],
        recovery_sequence_factory: Callable[..., Any],
    ) -> None:
        """Returns recovery data when session maps to active recovery sequence."""
        session_id = "widget-session-123"
        email = "shopper@example.com"

        # Create conversation with email linked to session
        await conversation_factory(
            store_id=store.id,
            session_id=session_id,
            customer_email=email,
        )

        # Create abandoned checkout and active recovery sequence
        checkout = await abandoned_checkout_factory(store_id=store.id, customer_email=email)
        await recovery_sequence_factory(
            store_id=store.id,
            abandoned_checkout_id=checkout.id,
            customer_email=email,
        )

        response = await unauthed_client.get(
            "/api/v1/recovery/check",
            params={
                "store_id": str(store.id),
                "session_id": session_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_recovery"] is True
        assert len(data["items"]) > 0
        assert data["checkout_url"] is not None


# ---------------------------------------------------------------------------
# Email pattern matching utility
# ---------------------------------------------------------------------------


class TestEmailPatternMatching:
    """Tests for _email_matches_patterns utility."""

    def test_matches_domain_pattern(self) -> None:
        """Email matching a domain regex returns True."""
        from app.workers.tasks.recovery import _email_matches_patterns

        assert _email_matches_patterns("user@test.com", [r"@test\.com$"]) is True

    def test_no_match_returns_false(self) -> None:
        """Email not matching any pattern returns False."""
        from app.workers.tasks.recovery import _email_matches_patterns

        assert _email_matches_patterns("user@other.com", [r"@test\.com$"]) is False

    def test_invalid_regex_skipped(self) -> None:
        """Invalid regex patterns are silently skipped."""
        from app.workers.tasks.recovery import _email_matches_patterns

        assert _email_matches_patterns("user@test.com", [r"[invalid"]) is False

    def test_empty_patterns_returns_false(self) -> None:
        """Empty pattern list always returns False."""
        from app.workers.tasks.recovery import _email_matches_patterns

        assert _email_matches_patterns("user@test.com", []) is False


# ---------------------------------------------------------------------------
# Recovery settings validation tests
# ---------------------------------------------------------------------------


class TestRecoverySettingsValidation:
    """Tests for RecoverySettings Pydantic validators."""

    def test_valid_patterns_accepted(self) -> None:
        """Valid regex patterns pass validation."""
        from app.schemas.recovery import RecoverySettings

        s = RecoverySettings(exclude_email_patterns=[r"@test\.com$", r"noreply"])
        assert s.exclude_email_patterns == [r"@test\.com$", r"noreply"]

    def test_invalid_regex_rejected(self) -> None:
        """Invalid regex pattern raises ValidationError."""
        from pydantic import ValidationError

        from app.schemas.recovery import RecoverySettings

        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            RecoverySettings(exclude_email_patterns=[r"[unclosed"])

    def test_pattern_too_long_rejected(self) -> None:
        """Pattern exceeding 200 chars raises ValidationError."""
        from pydantic import ValidationError

        from app.schemas.recovery import RecoverySettings

        with pytest.raises(ValidationError, match="Pattern too long"):
            RecoverySettings(exclude_email_patterns=["a" * 201])

    def test_empty_patterns_accepted(self) -> None:
        """Empty pattern list passes validation."""
        from app.schemas.recovery import RecoverySettings

        s = RecoverySettings(exclude_email_patterns=[])
        assert s.exclude_email_patterns == []


# ---------------------------------------------------------------------------
# Recovery message service tests
# ---------------------------------------------------------------------------


class TestRecoveryMessageService:
    """Tests for AI-powered recovery email generation."""

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self) -> None:
        """Falls back to pre-written template when LLM fails."""
        from app.services.recovery_message_service import (
            FALLBACK_TEMPLATES,
            RecoveryMessageService,
        )

        with patch("app.services.recovery_message_service.ChatOpenAI") as mock_cls:
            mock_llm = AsyncMock()
            mock_cls.return_value = mock_llm
            mock_llm.ainvoke.side_effect = Exception("API error")

            service = RecoveryMessageService()
            result = await service.generate_recovery_email(
                cart_items=[{"title": "Widget", "price": "29.99", "quantity": 1}],
                total_price="29.99",
                customer_name="Test",
                step_index=0,
                store_name="Test Store",
                sequence_type="first_time",
            )

        assert result["subject"] == FALLBACK_TEMPLATES[0]["subject"]
        assert result["cta_text"] == FALLBACK_TEMPLATES[0]["cta_text"]

    @pytest.mark.asyncio
    async def test_successful_llm_generation(self) -> None:
        """Successful LLM call returns parsed JSON response."""
        from app.services.recovery_message_service import RecoveryMessageService

        mock_response_content = json.dumps(
            {
                "subject": "Don't forget your cart!",
                "body_html": "<p>Hi Test, your items are waiting.</p>",
                "cta_text": "Complete Purchase",
            }
        )

        with patch("app.services.recovery_message_service.ChatOpenAI") as mock_cls:
            mock_llm = AsyncMock()
            mock_cls.return_value = mock_llm

            mock_ai_message = MagicMock()
            mock_ai_message.content = mock_response_content
            mock_llm.ainvoke.return_value = mock_ai_message

            service = RecoveryMessageService()
            result = await service.generate_recovery_email(
                cart_items=[{"title": "Widget", "price": "29.99", "quantity": 1}],
                total_price="29.99",
                customer_name="Test",
                step_index=0,
                store_name="Test Store",
                sequence_type="first_time",
            )

        assert result["subject"] == "Don't forget your cart!"
        assert result["cta_text"] == "Complete Purchase"

    @pytest.mark.asyncio
    async def test_handles_markdown_code_blocks(self) -> None:
        """Correctly parses JSON wrapped in markdown code blocks."""
        from app.services.recovery_message_service import RecoveryMessageService

        wrapped = '```json\n{"subject": "Hey!", "body_html": "<p>Hi</p>", "cta_text": "Buy"}\n```'

        with patch("app.services.recovery_message_service.ChatOpenAI") as mock_cls:
            mock_llm = AsyncMock()
            mock_cls.return_value = mock_llm

            mock_ai_message = MagicMock()
            mock_ai_message.content = wrapped
            mock_llm.ainvoke.return_value = mock_ai_message

            service = RecoveryMessageService()
            result = await service.generate_recovery_email(
                cart_items=[],
                total_price="0",
                customer_name=None,
                step_index=0,
                store_name="Store",
                sequence_type="first_time",
            )

        assert result["subject"] == "Hey!"
        assert result["cta_text"] == "Buy"


# ---------------------------------------------------------------------------
# Recovery service unit tests
# ---------------------------------------------------------------------------


class TestRecoveryServiceHelpers:
    """Tests for RecoveryService static helper methods."""

    def test_build_unsubscribe_url(self) -> None:
        """Unsubscribe URL contains a valid JWT token."""
        from app.services.recovery_service import RecoveryService

        url = RecoveryService._build_unsubscribe_url(uuid.uuid4(), "test@example.com")
        assert "unsubscribe?token=" in url

    def test_add_utm_params_empty_url(self) -> None:
        """Empty URL returns empty string."""
        from app.services.recovery_service import RecoveryService

        assert RecoveryService._add_utm_params("", 0) == ""

    def test_add_utm_params_no_query(self) -> None:
        """URL without query string gets ? separator."""
        from app.services.recovery_service import RecoveryService

        result = RecoveryService._add_utm_params("https://example.com/checkout", 0)
        assert "?utm_source=reva" in result
        assert "utm_content=step_0" in result

    def test_add_utm_params_existing_query(self) -> None:
        """URL with existing query string gets & separator."""
        from app.services.recovery_service import RecoveryService

        result = RecoveryService._add_utm_params("https://example.com?foo=bar", 2)
        assert "&utm_source=reva" in result
        assert "utm_content=step_2" in result

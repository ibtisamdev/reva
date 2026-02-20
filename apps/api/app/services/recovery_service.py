"""Core recovery service orchestrating email sequences."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import jwt
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.abandoned_checkout import AbandonedCheckout, CheckoutStatus
from app.models.email_unsubscribe import EmailUnsubscribe
from app.models.recovery_event import RecoveryEvent
from app.models.recovery_sequence import RecoverySequence, SequenceStatus
from app.models.store import Store
from app.schemas.recovery import (
    AbandonedCheckoutResponse,
    RecoverySequenceResponse,
    RecoverySettings,
)
from app.services.email_service import EmailService
from app.services.recovery_message_service import RecoveryMessageService

logger = logging.getLogger(__name__)

# Jinja2 template environment
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"
_jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)

# Default sequence timing (minutes from abandonment detection)
DEFAULT_TIMING = [120, 1440, 2880, 4320]  # 2hr, 24hr, 48hr, 72hr


class RecoveryService:
    """Orchestrates cart recovery email sequences."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.email_service = EmailService()
        self.message_service = RecoveryMessageService()

    async def start_sequence(
        self,
        store_id: UUID,
        checkout_id: UUID,
        customer_email: str,
    ) -> RecoverySequence | None:
        """Start a recovery sequence for an abandoned checkout.

        Returns the created sequence, or None if skipped.
        """
        # Check unsubscribe
        unsub_stmt = select(EmailUnsubscribe).where(
            EmailUnsubscribe.store_id == store_id,
            EmailUnsubscribe.email == customer_email,
        )
        unsub = (await self.db.execute(unsub_stmt)).scalar_one_or_none()
        if unsub:
            logger.info("Skipping recovery for unsubscribed email: %s", customer_email)
            return None

        # Check no existing active sequence for this checkout
        existing_stmt = select(RecoverySequence).where(
            RecoverySequence.abandoned_checkout_id == checkout_id,
            RecoverySequence.status == SequenceStatus.ACTIVE,
        )
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            logger.info("Active sequence already exists for checkout %s", checkout_id)
            return None

        # Load checkout for cart details
        checkout = (
            await self.db.execute(
                select(AbandonedCheckout).where(AbandonedCheckout.id == checkout_id)
            )
        ).scalar_one_or_none()
        if not checkout:
            return None

        # Determine sequence type via order history
        sequence_type = await self._determine_sequence_type(store_id, customer_email)

        now = datetime.now(UTC)
        # Get timing from store settings
        store = (
            await self.db.execute(select(Store).where(Store.id == store_id))
        ).scalar_one_or_none()
        recovery_settings = (store.settings or {}).get("recovery", {}) if store else {}
        timing = recovery_settings.get("sequence_timing_minutes", DEFAULT_TIMING)
        first_delay = timing[0] if timing else 120

        sequence = RecoverySequence(
            store_id=store_id,
            abandoned_checkout_id=checkout_id,
            customer_email=customer_email,
            sequence_type=sequence_type,
            status=SequenceStatus.ACTIVE,
            current_step_index=0,
            steps_completed=[],
            started_at=now,
            next_step_at=now + timedelta(minutes=first_delay),
        )
        self.db.add(sequence)

        # Log event
        event = RecoveryEvent(
            store_id=store_id,
            sequence_id=sequence.id,
            abandoned_checkout_id=checkout_id,
            event_type="sequence_started",
            metadata_={"sequence_type": sequence_type, "email": customer_email},
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(sequence)

        logger.info(
            "Recovery sequence started: id=%s type=%s email=%s",
            sequence.id,
            sequence_type,
            customer_email,
        )

        # Schedule first step execution
        from app.workers.tasks.recovery import execute_sequence_step

        delay_seconds = first_delay * 60
        execute_sequence_step.apply_async(
            args=[str(sequence.id), str(store_id)],
            countdown=delay_seconds,
        )

        return sequence

    async def execute_step(self, sequence_id: UUID, store_id: UUID) -> dict[str, Any]:
        """Execute the current step of a recovery sequence."""
        sequence = (
            await self.db.execute(
                select(RecoverySequence).where(
                    RecoverySequence.id == sequence_id,
                    RecoverySequence.store_id == store_id,
                )
            )
        ).scalar_one_or_none()

        if not sequence or sequence.status != SequenceStatus.ACTIVE:
            return {"status": "skipped", "reason": "sequence not active"}

        # Load checkout
        checkout = (
            await self.db.execute(
                select(AbandonedCheckout).where(
                    AbandonedCheckout.id == sequence.abandoned_checkout_id
                )
            )
        ).scalar_one_or_none()

        if not checkout:
            await self._stop_sequence(sequence, "checkout_deleted")
            return {"status": "stopped", "reason": "checkout deleted"}

        # Check if checkout was completed
        if checkout.status == CheckoutStatus.COMPLETED:
            await self._stop_sequence(sequence, "order_completed")
            return {"status": "stopped", "reason": "order completed"}

        # Check unsubscribe
        unsub = (
            await self.db.execute(
                select(EmailUnsubscribe).where(
                    EmailUnsubscribe.store_id == sequence.store_id,
                    EmailUnsubscribe.email == sequence.customer_email,
                )
            )
        ).scalar_one_or_none()
        if unsub:
            await self._stop_sequence(sequence, "unsubscribed")
            return {"status": "stopped", "reason": "unsubscribed"}

        # Load store for settings and name
        store = (
            await self.db.execute(select(Store).where(Store.id == sequence.store_id))
        ).scalar_one_or_none()
        if not store:
            await self._stop_sequence(sequence, "store_deleted")
            return {"status": "stopped", "reason": "store deleted"}

        store_name = store.name
        recovery_settings = (store.settings or {}).get("recovery", {})
        timing = recovery_settings.get("sequence_timing_minutes", DEFAULT_TIMING)
        discount_enabled = recovery_settings.get("discount_enabled", False)
        discount_percent = (
            recovery_settings.get("discount_percent", 10) if discount_enabled else None
        )

        step_index = sequence.current_step_index

        # Generate AI message
        message = await self.message_service.generate_recovery_email(
            cart_items=checkout.line_items or [],
            total_price=str(checkout.total_price),
            customer_name=checkout.customer_name,
            step_index=step_index,
            store_name=store_name,
            sequence_type=sequence.sequence_type,
            discount_percent=discount_percent,
        )

        # Build unsubscribe URL
        unsubscribe_url = self._build_unsubscribe_url(sequence.store_id, sequence.customer_email)

        # Add UTM params to checkout URL
        checkout_url = self._add_utm_params(
            checkout.checkout_url or "",
            step_index=step_index,
        )

        # Render HTML template
        template = _jinja_env.get_template("cart_recovery.html")
        html_content = template.render(
            subject=message["subject"],
            store_name=store_name,
            body_html=message["body_html"],
            cart_items=checkout.line_items or [],
            total_price=str(checkout.total_price),
            currency=checkout.currency,
            checkout_url=checkout_url,
            cta_text=message["cta_text"],
            unsubscribe_url=unsubscribe_url,
        )

        # Send email
        tags = [
            {"name": "store_id", "value": str(sequence.store_id)},
            {"name": "step", "value": str(step_index)},
            {"name": "type", "value": sequence.sequence_type},
        ]
        email_id = await self.email_service.send_recovery_email(
            to_email=sequence.customer_email,
            subject=message["subject"],
            html_content=html_content,
            store_name=store_name,
            tags=tags,
        )

        # Update sequence
        now = datetime.now(UTC)
        step_record: dict[str, Any] = {
            "step_index": step_index,
            "sent_at": now.isoformat(),
            "subject": message["subject"],
            "email_id": email_id,
        }
        steps = list(sequence.steps_completed or [])
        steps.append(step_record)
        sequence.steps_completed = steps
        sequence.current_step_index = step_index + 1

        # Log event
        event = RecoveryEvent(
            store_id=sequence.store_id,
            sequence_id=sequence.id,
            abandoned_checkout_id=sequence.abandoned_checkout_id,
            event_type="email_sent",
            step_index=step_index,
            channel="email",
            metadata_={
                "subject": message["subject"],
                "email_id": email_id,
                "customer_email": sequence.customer_email,
            },
        )
        self.db.add(event)

        # Schedule next step or complete
        next_step_index = step_index + 1
        if next_step_index < len(timing):
            # Calculate delay from abandonment, not from now
            next_delay_minutes = timing[next_step_index]
            sequence.next_step_at = now + timedelta(minutes=next_delay_minutes - timing[step_index])
            await self.db.commit()

            from app.workers.tasks.recovery import execute_sequence_step

            delay_seconds = int((sequence.next_step_at - now).total_seconds())
            execute_sequence_step.apply_async(
                args=[str(sequence.id), str(sequence.store_id)],
                countdown=max(delay_seconds, 60),
            )
        else:
            # Sequence complete
            sequence.status = SequenceStatus.COMPLETED
            sequence.completed_at = now
            sequence.next_step_at = None

            complete_event = RecoveryEvent(
                store_id=sequence.store_id,
                sequence_id=sequence.id,
                abandoned_checkout_id=sequence.abandoned_checkout_id,
                event_type="sequence_completed",
                metadata_={"steps_total": next_step_index},
            )
            self.db.add(complete_event)
            await self.db.commit()

        return {
            "status": "sent",
            "step_index": step_index,
            "email_id": email_id,
            "subject": message["subject"],
        }

    async def stop_sequence(self, sequence_id: UUID, store_id: UUID, reason: str) -> bool:
        """Stop a recovery sequence by ID."""
        sequence = (
            await self.db.execute(
                select(RecoverySequence).where(
                    RecoverySequence.id == sequence_id,
                    RecoverySequence.store_id == store_id,
                )
            )
        ).scalar_one_or_none()

        if not sequence or sequence.status != SequenceStatus.ACTIVE:
            return False

        await self._stop_sequence(sequence, reason)
        return True

    async def stop_sequences_for_email(self, store_id: UUID, email: str, reason: str) -> int:
        """Stop all active sequences for an email address."""
        stmt = select(RecoverySequence).where(
            RecoverySequence.store_id == store_id,
            RecoverySequence.customer_email == email,
            RecoverySequence.status == SequenceStatus.ACTIVE,
        )
        result = await self.db.execute(stmt)
        sequences = list(result.scalars().all())

        for seq in sequences:
            await self._stop_sequence(seq, reason)

        return len(sequences)

    async def get_sequences(
        self,
        store_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[RecoverySequenceResponse], int]:
        """Paginated recovery sequences with total_steps computed from store settings."""
        store = (
            await self.db.execute(select(Store).where(Store.id == store_id))
        ).scalar_one_or_none()
        recovery_settings = (store.settings or {}).get("recovery", {}) if store else {}
        timing = recovery_settings.get("sequence_timing_minutes", DEFAULT_TIMING)
        total_steps = len(timing)

        count_stmt = (
            select(func.count())
            .select_from(RecoverySequence)
            .where(RecoverySequence.store_id == store_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(RecoverySequence)
            .where(RecoverySequence.store_id == store_id)
            .order_by(RecoverySequence.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        sequences = list(result.scalars().all())

        items = [
            RecoverySequenceResponse(
                id=seq.id,
                abandoned_checkout_id=seq.abandoned_checkout_id,
                customer_email=seq.customer_email,
                sequence_type=seq.sequence_type,
                status=seq.status.value,
                current_step_index=seq.current_step_index,
                steps_completed=seq.steps_completed or [],
                total_steps=total_steps,
                next_step_at=seq.next_step_at,
                started_at=seq.started_at,
                completed_at=seq.completed_at,
                created_at=seq.created_at,
            )
            for seq in sequences
        ]
        return items, total

    async def get_checkouts(
        self,
        store_id: UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[AbandonedCheckoutResponse], int]:
        """Paginated abandoned checkouts."""
        count_stmt = (
            select(func.count())
            .select_from(AbandonedCheckout)
            .where(AbandonedCheckout.store_id == store_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AbandonedCheckout)
            .where(AbandonedCheckout.store_id == store_id)
            .order_by(AbandonedCheckout.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        checkouts = list(result.scalars().all())

        items = [
            AbandonedCheckoutResponse(
                id=c.id,
                shopify_checkout_id=c.shopify_checkout_id,
                customer_email=c.customer_email,
                customer_name=c.customer_name,
                total_price=float(c.total_price),
                currency=c.currency,
                line_items=c.line_items or [],
                checkout_url=c.checkout_url,
                status=c.status.value,
                abandonment_detected_at=c.abandonment_detected_at,
                recovered_at=c.recovered_at,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in checkouts
        ]
        return items, total

    async def update_settings(self, store_id: UUID, data: RecoverySettings) -> RecoverySettings:
        """Persist updated recovery settings for a store."""
        store = (
            await self.db.execute(select(Store).where(Store.id == store_id))
        ).scalar_one_or_none()
        if not store:
            from fastapi import HTTPException, status

            raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")

        current_settings = dict(store.settings or {})
        current_settings["recovery"] = data.model_dump()
        store.settings = current_settings
        await self.db.commit()
        return data

    async def _stop_sequence(self, sequence: RecoverySequence, reason: str) -> None:
        """Internal helper to stop a sequence."""
        sequence.status = SequenceStatus.STOPPED
        sequence.stopped_reason = reason
        sequence.completed_at = datetime.now(UTC)
        sequence.next_step_at = None

        event = RecoveryEvent(
            store_id=sequence.store_id,
            sequence_id=sequence.id,
            abandoned_checkout_id=sequence.abandoned_checkout_id,
            event_type="sequence_stopped",
            metadata_={"reason": reason},
        )
        self.db.add(event)
        await self.db.commit()

    async def _determine_sequence_type(self, store_id: UUID, email: str) -> str:
        """Determine customer segment for personalized messaging."""
        try:
            from app.core.encryption import decrypt_token
            from app.integrations.shopify.client import ShopifyClient
            from app.models.integration import IntegrationStatus, StoreIntegration

            stmt = select(StoreIntegration).where(
                StoreIntegration.store_id == store_id,
                StoreIntegration.status == IntegrationStatus.ACTIVE,
            )
            result = await self.db.execute(stmt)
            integration = result.scalar_one_or_none()

            if not integration:
                return "first_time"

            access_token = decrypt_token(integration.credentials.get("access_token", ""))
            client = ShopifyClient(integration.platform_domain, access_token)
            orders = await client.get_orders_by_email(email, limit=10)

            if not orders:
                return "first_time"

            # Calculate lifetime value
            ltv = sum(float(o.get("total_price", 0)) for o in orders)
            if ltv > 500:
                return "high_value"
            return "returning"
        except Exception:
            logger.exception("Failed to determine sequence type for %s", email)
            return "first_time"

    @staticmethod
    def _build_unsubscribe_url(store_id: UUID, email: str) -> str:
        """Generate a signed unsubscribe URL."""
        token = jwt.encode(
            {"store_id": str(store_id), "email": email},
            settings.secret_key,
            algorithm="HS256",
        )
        return f"{settings.api_url}/api/v1/recovery/unsubscribe?token={token}"

    @staticmethod
    def _add_utm_params(url: str, step_index: int) -> str:
        """Append UTM parameters to a checkout URL."""
        if not url:
            return url
        separator = "&" if "?" in url else "?"
        return (
            f"{url}{separator}"
            f"utm_source=reva&utm_medium=email"
            f"&utm_campaign=cart_recovery&utm_content=step_{step_index}"
        )

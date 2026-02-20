"""RecoveryEvent model for tracking recovery analytics events."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecoveryEvent(Base):
    """Tracks individual events within recovery sequences for analytics.

    Events include: sequence_started, email_sent, email_opened,
    link_clicked, sequence_completed, sequence_stopped, unsubscribed.
    """

    __tablename__ = "recovery_events"

    # Store relationship (multi-tenancy)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional links to sequence and checkout
    sequence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recovery_sequences.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    abandoned_checkout_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("abandoned_checkouts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Event details
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    channel: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<RecoveryEvent {self.event_type} seq={self.sequence_id}>"

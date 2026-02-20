"""RecoverySequence model for tracking email recovery sequences."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.abandoned_checkout import AbandonedCheckout
    from app.models.store import Store


class SequenceStatus(str, enum.Enum):
    """Status of a recovery sequence."""

    ACTIVE = "active"
    COMPLETED = "completed"
    STOPPED = "stopped"


class RecoverySequence(Base):
    """Tracks a multi-step email recovery sequence for an abandoned checkout.

    Each sequence progresses through timed steps (e.g., 2hr, 24hr, 48hr, 72hr),
    sending personalized recovery emails at each step.
    """

    __tablename__ = "recovery_sequences"
    __table_args__ = (
        Index("ix_recovery_sequences_store_status", "store_id", "status"),
        Index("ix_recovery_sequences_store_email", "store_id", "customer_email"),
        Index(
            "ix_recovery_sequences_next_step_active",
            "next_step_at",
            postgresql_where="status = 'active'",
        ),
    )

    # Store relationship (multi-tenancy)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Link to abandoned checkout
    abandoned_checkout_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("abandoned_checkouts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Customer info
    customer_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Sequence configuration
    sequence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="first_time",
    )
    status: Mapped[SequenceStatus] = mapped_column(
        Enum(
            SequenceStatus,
            name="sequence_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=SequenceStatus.ACTIVE,
        nullable=False,
    )
    current_step_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    steps_completed: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    # Lifecycle
    stopped_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    next_step_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Extensible data
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    store: Mapped["Store"] = relationship("Store")
    abandoned_checkout: Mapped["AbandonedCheckout"] = relationship("AbandonedCheckout")

    def __repr__(self) -> str:
        return f"<RecoverySequence {self.customer_email} step={self.current_step_index} ({self.status.value})>"

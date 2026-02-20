"""EmailUnsubscribe model for permanent email opt-outs (GDPR compliant)."""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailUnsubscribe(Base):
    """Permanent per-store email unsubscribe record.

    Once created, this record prevents all future recovery emails
    to the given address for the given store. No expiry per GDPR.
    """

    __tablename__ = "email_unsubscribes"
    __table_args__ = (
        UniqueConstraint("store_id", "email", name="uq_email_unsubscribes_store_email"),
    )

    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EmailUnsubscribe {self.email}>"

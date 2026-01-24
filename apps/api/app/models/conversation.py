"""Conversation model for chat sessions."""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.organization import Organization


class Channel(str, enum.Enum):
    """Communication channels."""

    WIDGET = "widget"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class ConversationStatus(str, enum.Enum):
    """Conversation status."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class Conversation(Base):
    """Conversation model for chat sessions."""

    __tablename__ = "conversations"

    # Organization relationship
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Customer information (optional - can be anonymous)
    customer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Session tracking
    session_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    # Channel and status
    channel: Mapped[Channel] = mapped_column(
        Enum(Channel, name="channel"),
        default=Channel.WIDGET,
        nullable=False,
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"),
        default=ConversationStatus.ACTIVE,
        nullable=False,
    )

    # Context extra data (page URL, product context, etc.)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="conversations",
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} ({self.status.value})>"

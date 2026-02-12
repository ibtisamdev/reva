"""OrderInquiry model for tracking WISMO (Where Is My Order) interactions."""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.store import Store


class InquiryType(str, enum.Enum):
    """Types of order-related inquiries."""

    ORDER_STATUS = "order_status"
    TRACKING = "tracking"
    DELIVERY_ETA = "delivery_eta"
    MISSING_PACKAGE = "missing_package"
    OTHER = "other"


class InquiryResolution(str, enum.Enum):
    """How the inquiry was resolved."""

    ANSWERED = "answered"
    TRACKING_PROVIDED = "tracking_provided"
    ESCALATED = "escalated"
    UNRESOLVED = "unresolved"
    VERIFICATION_FAILED = "verification_failed"


class OrderInquiry(Base):
    """Tracks order status inquiries for WISMO analytics.

    Each record represents a customer asking about an order, with the
    resolution outcome and relevant order data captured at inquiry time.
    """

    __tablename__ = "order_inquiries"

    # Store relationship (multi-tenancy)
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional conversation link
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Customer info
    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Order info
    order_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Inquiry classification
    inquiry_type: Mapped[InquiryType] = mapped_column(
        Enum(
            InquiryType,
            name="inquiry_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=InquiryType.ORDER_STATUS,
        nullable=False,
    )

    # Status snapshot at inquiry time
    order_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    fulfillment_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Resolution
    resolution: Mapped[InquiryResolution | None] = mapped_column(
        Enum(
            InquiryResolution,
            name="inquiry_resolution",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Extensible data (M8 webhook compatibility)
    extra_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Relationships
    store: Mapped["Store"] = relationship("Store")
    conversation: Mapped["Conversation | None"] = relationship("Conversation")

    def __repr__(self) -> str:
        return f"<OrderInquiry {self.order_number} ({self.inquiry_type.value})>"

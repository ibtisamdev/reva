"""Pydantic schemas for M4 Cart Recovery."""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema

# --- Store recovery settings ---


class RecoverySettings(BaseSchema):
    """Store-level recovery configuration (stored in Store.settings['recovery'])."""

    enabled: bool = False
    min_cart_value: float = 0.0
    abandonment_threshold_minutes: int = 60
    sequence_timing_minutes: list[int] = Field(default_factory=lambda: [120, 1440, 2880, 4320])
    discount_enabled: bool = False
    discount_percent: int = 10
    max_emails_per_day: int = 50
    exclude_email_patterns: list[str] = Field(default_factory=list)

    @field_validator("exclude_email_patterns")
    @classmethod
    def validate_email_patterns(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            if len(pattern) > 200:
                raise ValueError(f"Pattern too long (max 200 chars): {pattern[:50]!r}...")
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"Invalid regex pattern {pattern!r}: {exc}") from exc
        return patterns


# --- Abandoned checkout responses ---


class AbandonedCheckoutResponse(BaseSchema):
    """API response for an abandoned checkout."""

    id: UUID
    shopify_checkout_id: str
    customer_email: str | None
    customer_name: str | None
    total_price: float
    currency: str
    line_items: list[dict[str, Any]]
    checkout_url: str | None
    status: str
    abandonment_detected_at: datetime | None
    recovered_at: datetime | None
    created_at: datetime
    updated_at: datetime


# --- Recovery sequence responses ---


class RecoverySequenceResponse(BaseSchema):
    """API response for a recovery sequence."""

    id: UUID
    abandoned_checkout_id: UUID
    customer_email: str
    sequence_type: str
    status: str
    current_step_index: int
    steps_completed: list[dict[str, Any]]
    total_steps: int
    next_step_at: datetime | None
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime


# --- Widget recovery check ---


class RecoveryItem(BaseSchema):
    """A single cart item for the widget recovery popup."""

    title: str
    price: str
    image_url: str | None = None
    quantity: int = 1


class RecoveryCheckResponse(BaseSchema):
    """Response for widget recovery popup check."""

    has_recovery: bool = False
    items: list[RecoveryItem] = Field(default_factory=list)
    checkout_url: str | None = None
    total_price: str | None = None
    sequence_id: UUID | None = None


# --- Recovery analytics ---


class RecoverySummary(BaseSchema):
    """Summary statistics for recovery analytics."""

    total_abandoned: int
    total_recovered: int
    recovery_rate: float
    recovered_revenue: float
    emails_sent: int
    active_sequences: int
    period_days: int


class RecoveryDailyCount(BaseSchema):
    """Daily count for recovery trend data."""

    date: str
    abandoned: int
    recovered: int

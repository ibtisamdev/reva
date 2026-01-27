"""Pydantic schemas for store settings and CRUD operations."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema

# === Store CRUD Schemas ===


class StoreCreate(BaseSchema):
    """Schema for creating a new store."""

    name: str = Field(..., min_length=1, max_length=255, description="Store name")
    email: str | None = Field(default=None, max_length=255, description="Store email")


class StoreUpdate(BaseSchema):
    """Schema for updating a store."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class StoreResponse(BaseSchema):
    """Schema for store response."""

    id: UUID
    organization_id: str
    name: str
    email: str | None
    plan: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StoreListResponse(BaseSchema):
    """Schema for listing stores."""

    items: list[StoreResponse]
    total: int


# === Widget Settings Schemas ===


class WidgetSettings(BaseSchema):
    """Widget configuration settings."""

    primary_color: str = Field(
        default="#0d9488",
        description="Primary color for the widget (hex format)",
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
    welcome_message: str = Field(
        default="Hi! How can I help you today?",
        description="Welcome message shown when widget opens",
        max_length=500,
    )
    position: Literal["bottom-right", "bottom-left"] = Field(
        default="bottom-right",
        description="Widget position on the page",
    )
    agent_name: str = Field(
        default="Reva Support",
        description="Name shown in the widget header",
        max_length=100,
    )


class StoreSettingsResponse(BaseSchema):
    """Response schema for store settings."""

    widget: WidgetSettings


class WidgetSettingsUpdate(BaseSchema):
    """Partial update for widget settings."""

    primary_color: str | None = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
    )
    welcome_message: str | None = Field(default=None, max_length=500)
    position: Literal["bottom-right", "bottom-left"] | None = None
    agent_name: str | None = Field(default=None, max_length=100)


class StoreSettingsUpdate(BaseSchema):
    """Request schema for updating store settings."""

    widget: WidgetSettingsUpdate | None = None


# Default settings
DEFAULT_WIDGET_SETTINGS: dict = {
    "widget": {
        "primary_color": "#0d9488",
        "welcome_message": "Hi! How can I help you today?",
        "position": "bottom-right",
        "agent_name": "Reva Support",
    }
}

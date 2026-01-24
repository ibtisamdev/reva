"""Common Pydantic schemas used across the API."""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class HealthResponse(BaseSchema):
    """Health check response schema."""

    status: str
    version: str
    environment: str
    checks: dict[str, str]


class ErrorResponse(BaseSchema):
    """Error response schema."""

    error: str
    detail: str | None = None
    code: str | None = None


class PaginatedResponse[T](BaseSchema):
    """Paginated response wrapper."""

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

"""Pydantic schemas for product search and filtering."""

from pydantic import BaseModel, Field

from app.schemas.common import BaseSchema


class ProductFilters(BaseModel):
    """Filters that can be applied to product search."""

    price_min: float | None = Field(None, description="Minimum price filter")
    price_max: float | None = Field(None, description="Maximum price filter")
    categories: list[str] | None = Field(None, description="Filter by product type/category")
    tags: list[str] | None = Field(None, description="Filter by product tags")
    vendors: list[str] | None = Field(None, description="Filter by vendor/brand")
    in_stock_only: bool = Field(True, description="Only show in-stock products")


class SearchRequest(BaseModel):
    """Request body for natural language product search."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    filters: ProductFilters | None = Field(None, description="Optional filters")
    limit: int = Field(10, ge=1, le=50, description="Max results to return")


class ProductSearchResult(BaseSchema):
    """A single product search result."""

    product_id: str
    title: str
    description: str | None = None
    price: str | None = None
    vendor: str | None = None
    product_type: str | None = None
    tags: list[str] = []
    in_stock: bool = True
    image_url: str | None = None
    handle: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    """Response from product search."""

    results: list[ProductSearchResult]
    total: int
    query: str
    filters_applied: ProductFilters | None = None

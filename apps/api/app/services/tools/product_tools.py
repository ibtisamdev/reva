"""LangChain @tool definitions for product search and recommendation operations.

Tools are created per-request via create_product_tools() to ensure
multi-tenant isolation — each tool closes over services and store_id.

These tools follow the same factory pattern as order_tools.py.
"""

import json
from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.schemas.search import ProductFilters
from app.services.recommendation_service import RecommendationService
from app.services.search_service import SearchService

# --- Input schemas ---


class SearchProductsInput(BaseModel):
    """Input for product search."""

    query: str = Field(description="Natural language search query (e.g., 'red shoes under $50')")
    price_min: float | None = Field(None, description="Minimum price filter")
    price_max: float | None = Field(None, description="Maximum price filter")
    in_stock_only: bool = Field(True, description="Only show products currently in stock")


class ProductDetailsInput(BaseModel):
    """Input for getting product details."""

    product_id: str = Field(description="The product ID to look up")


class ProductAvailabilityInput(BaseModel):
    """Input for checking product availability."""

    product_id: str = Field(description="The product ID to check")
    variant_title: str | None = Field(
        None, description="Specific variant to check (e.g., 'Large / Blue')"
    )


class SimilarProductsInput(BaseModel):
    """Input for finding similar products."""

    product_id: str = Field(description="The product ID to find similar products for")
    limit: int = Field(5, description="Number of similar products to return", ge=1, le=10)


class SuggestAlternativesInput(BaseModel):
    """Input for suggesting product alternatives."""

    product_id: str = Field(description="The product ID to suggest alternatives for")


class CompareProductsInput(BaseModel):
    """Input for comparing products side by side."""

    product_ids: list[str] = Field(
        description="List of product IDs to compare (2-4 products)",
        min_length=2,
        max_length=4,
    )


def create_product_tools(
    search_service: SearchService,
    recommendation_service: RecommendationService,
    store_id: UUID,
) -> list[Any]:
    """Create LangChain tools for product search and recommendations.

    Returns list of @tool-decorated functions for bind_tools().
    Each tool closes over services and store_id for multi-tenant safety.
    """

    @tool(args_schema=SearchProductsInput)
    async def search_products(
        query: str,
        price_min: float | None = None,
        price_max: float | None = None,
        in_stock_only: bool = True,
    ) -> str:
        """Search for products using natural language. Use when a customer is looking for
        products, browsing, or asking about what's available. Supports price filtering."""
        filters = ProductFilters(
            price_min=price_min,
            price_max=price_max,
            in_stock_only=in_stock_only,
        )
        results = await search_service.hybrid_search(
            query=query,
            store_id=store_id,
            filters=filters,
            limit=5,
        )

        if not results:
            return json.dumps({"results": [], "message": "No products found matching your search."})

        products = []
        for r in results:
            products.append(
                {
                    "product_id": r.product_id,
                    "title": r.title,
                    "price": r.price,
                    "description": r.description,
                    "in_stock": r.in_stock,
                    "image_url": r.image_url,
                    "handle": r.handle,
                    "score": round(r.score, 4),
                }
            )

        return json.dumps({"results": products, "total": len(products)})

    @tool(args_schema=ProductDetailsInput)
    async def get_product_details(product_id: str) -> str:
        """Get full details about a specific product including all variants,
        pricing, and availability. Use when a customer asks about a specific product."""
        product = await search_service.get_product_by_id(UUID(product_id), store_id)

        if not product:
            return json.dumps({"error": "Product not found"})

        variants_info = []
        if product.variants:
            for v in product.variants:
                if isinstance(v, dict):
                    variants_info.append(
                        {
                            "title": v.get("title", "Default"),
                            "price": v.get("price"),
                            "sku": v.get("sku"),
                            "inventory_quantity": v.get("inventory_quantity", 0),
                            "available": (v.get("inventory_quantity", 0) or 0) > 0,
                        }
                    )

        images = []
        if product.images:
            for img in product.images:
                if isinstance(img, dict):
                    images.append(img.get("src"))

        return json.dumps(
            {
                "product_id": str(product.id),
                "title": product.title,
                "description": product.description,
                "vendor": product.vendor,
                "product_type": product.product_type,
                "tags": product.tags or [],
                "variants": variants_info,
                "images": [i for i in images if i],
                "handle": product.handle,
            }
        )

    @tool(args_schema=ProductAvailabilityInput)
    async def check_product_availability(
        product_id: str,
        variant_title: str | None = None,
    ) -> str:
        """Check if a product or specific variant is in stock.
        Use when a customer asks about availability or stock status."""
        product = await search_service.get_product_by_id(UUID(product_id), store_id)

        if not product:
            return json.dumps({"error": "Product not found"})

        if not product.variants:
            return json.dumps(
                {
                    "product": product.title,
                    "available": False,
                    "message": "No variant information available.",
                }
            )

        results = []
        for v in product.variants:
            if not isinstance(v, dict):
                continue
            v_title = v.get("title", "Default")
            qty = v.get("inventory_quantity", 0) or 0
            available = qty > 0

            if variant_title and variant_title.lower() != v_title.lower():
                continue

            results.append(
                {
                    "variant": v_title,
                    "available": available,
                    "quantity": qty,
                    "price": v.get("price"),
                }
            )

        if variant_title and not results:
            return json.dumps(
                {
                    "product": product.title,
                    "error": f"Variant '{variant_title}' not found.",
                    "available_variants": [
                        v.get("title", "Default") for v in product.variants if isinstance(v, dict)
                    ],
                }
            )

        return json.dumps(
            {
                "product": product.title,
                "variants": results,
                "any_available": any(r["available"] for r in results),
            }
        )

    @tool(args_schema=SimilarProductsInput)
    async def get_similar_products(product_id: str, limit: int = 5) -> str:
        """Find products similar to a given product. Use when a customer wants
        to see alternatives or 'more like this'."""
        results = await recommendation_service.get_similar_products(
            UUID(product_id), store_id, limit=limit
        )

        if not results:
            return json.dumps({"results": [], "message": "No similar products found."})

        return json.dumps(
            {
                "results": [
                    {
                        "product_id": r.product_id,
                        "title": r.title,
                        "price": r.price,
                        "description": r.description,
                        "in_stock": r.in_stock,
                        "image_url": r.image_url,
                        "handle": r.handle,
                        "score": r.score,
                    }
                    for r in results
                ]
            }
        )

    @tool(args_schema=SuggestAlternativesInput)
    async def suggest_alternatives(product_id: str) -> str:
        """Suggest alternative products including upsells and cross-sells.
        Use when a customer might be interested in related or complementary products."""
        upsells = await recommendation_service.get_upsell_products(
            UUID(product_id), store_id, limit=3
        )
        cross_sells = await recommendation_service.get_cross_sell_products(
            UUID(product_id), store_id, limit=3
        )

        return json.dumps(
            {
                "upsells": [
                    {
                        "product_id": r.product_id,
                        "title": r.title,
                        "price": r.price,
                        "in_stock": r.in_stock,
                        "image_url": r.image_url,
                        "handle": r.handle,
                    }
                    for r in upsells
                ],
                "cross_sells": [
                    {
                        "product_id": r.product_id,
                        "title": r.title,
                        "price": r.price,
                        "in_stock": r.in_stock,
                        "image_url": r.image_url,
                        "handle": r.handle,
                    }
                    for r in cross_sells
                ],
            }
        )

    @tool(args_schema=CompareProductsInput)
    async def compare_products(product_ids: list[str]) -> str:
        """Compare multiple products side by side. Use when a customer is
        deciding between products and wants to see differences."""
        comparison = await recommendation_service.compare_products(
            [UUID(pid) for pid in product_ids], store_id
        )
        return json.dumps(comparison)

    return [
        search_products,
        get_product_details,
        check_product_availability,
        get_similar_products,
        suggest_alternatives,
        compare_products,
    ]

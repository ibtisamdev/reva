"""Shopify Admin API client using httpx."""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ShopifyClient:
    """Async client for the Shopify Admin REST API."""

    def __init__(self, shop_domain: str, access_token: str) -> None:
        self.shop_domain = shop_domain
        self.base_url = f"https://{shop_domain}/admin/api/{settings.shopify_api_version}"
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
        }

    async def get_all_products(self) -> list[dict[str, Any]]:
        """Fetch all products using cursor-based pagination."""
        products: list[dict[str, Any]] = []
        url: str | None = f"{self.base_url}/products.json?limit=250"

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            while url:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                products.extend(data.get("products", []))

                # Cursor-based pagination via Link header
                url = self._get_next_page_url(response)

        return products

    async def get_pages(self) -> list[dict[str, Any]]:
        """Fetch all store pages (policies, about, FAQ, etc.)."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/pages.json?limit=250")
            response.raise_for_status()
            pages: list[dict[str, Any]] = response.json().get("pages", [])
            return pages

    async def register_webhooks(self) -> None:
        """Register product webhooks for incremental sync."""
        topics = ["products/create", "products/update", "products/delete"]
        base_address = f"{settings.api_url}/api/v1/webhooks/shopify"

        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            for topic in topics:
                # Topic "products/create" -> path segment "products-create"
                path = topic.replace("/", "-")
                response = await client.post(
                    f"{self.base_url}/webhooks.json",
                    json={
                        "webhook": {
                            "topic": topic,
                            "address": f"{base_address}/{path}",
                            "format": "json",
                        }
                    },
                )
                if not response.is_success:
                    logger.warning(
                        "Failed to register webhook %s for %s: %s",
                        topic,
                        self.shop_domain,
                        response.status_code,
                    )

    async def delete_webhooks(self) -> None:
        """Delete all webhooks for this app."""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            response = await client.get(f"{self.base_url}/webhooks.json")
            response.raise_for_status()
            webhooks = response.json().get("webhooks", [])
            for webhook in webhooks:
                await client.delete(f"{self.base_url}/webhooks/{webhook['id']}.json")

    def _get_next_page_url(self, response: httpx.Response) -> str | None:
        """Extract next page URL from Link header for cursor pagination."""
        link_header = response.headers.get("link", "")
        if not link_header:
            return None

        for part in link_header.split(","):
            if 'rel="next"' in part:
                url: str = part.split(";")[0].strip().strip("<>")
                return url
        return None

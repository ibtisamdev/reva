"""Tests for ShopifyClient HTTP wrapper.

Covers:
- ShopifyClient initialization and headers
- get_all_products (single page, pagination, empty, errors)
- get_pages
- register_webhooks
- delete_webhooks
- _get_next_page_url (Link header parsing)
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, Response

from app.integrations.shopify.client import ShopifyClient
from tests.conftest import SHOPIFY_TEST_SHOP

# ---------------------------------------------------------------------------
# Tests: ShopifyClient initialization
# ---------------------------------------------------------------------------


class TestShopifyClientInit:
    """Tests for ShopifyClient initialization."""

    def test_sets_base_url(self) -> None:
        """base_url includes shop domain and API version."""
        client = ShopifyClient("my-shop.myshopify.com", "token123")

        assert "my-shop.myshopify.com" in client.base_url
        assert "/admin/api/" in client.base_url

    def test_sets_headers(self) -> None:
        """Headers include access token."""
        client = ShopifyClient("shop.myshopify.com", "shpat_abc123")

        assert client.headers["X-Shopify-Access-Token"] == "shpat_abc123"
        assert client.headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# Tests: get_all_products
# ---------------------------------------------------------------------------


class TestGetAllProducts:
    """Tests for fetching all products from Shopify."""

    async def test_single_page(self, mock_shopify_http: MagicMock) -> None:
        """Returns products from single-page response."""
        products = [
            {"id": 1, "title": "Product 1"},
            {"id": 2, "title": "Product 2"},
        ]
        mock_shopify_http.get.return_value.json.return_value = {"products": products}
        mock_shopify_http.get.return_value.headers = {}  # No Link header

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        result = await client.get_all_products()

        assert len(result) == 2
        assert result[0]["title"] == "Product 1"
        assert result[1]["title"] == "Product 2"

    async def test_pagination(self) -> None:
        """Follows Link header for multiple pages."""
        page1_products = [{"id": 1, "title": "Product 1"}]
        page2_products = [{"id": 2, "title": "Product 2"}]
        page3_products = [{"id": 3, "title": "Product 3"}]

        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            # Page 1 response
            response1 = MagicMock()
            response1.json.return_value = {"products": page1_products}
            response1.headers = {"link": '<https://shop/page2>; rel="next"'}
            response1.raise_for_status = MagicMock()

            # Page 2 response
            response2 = MagicMock()
            response2.json.return_value = {"products": page2_products}
            response2.headers = {"link": '<https://shop/page3>; rel="next"'}
            response2.raise_for_status = MagicMock()

            # Page 3 response (no next)
            response3 = MagicMock()
            response3.json.return_value = {"products": page3_products}
            response3.headers = {}
            response3.raise_for_status = MagicMock()

            mock_client.get.side_effect = [response1, response2, response3]

            client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
            result = await client.get_all_products()

        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert result[2]["id"] == 3

    async def test_empty_response(self, mock_shopify_http: MagicMock) -> None:
        """Handles empty product list."""
        mock_shopify_http.get.return_value.json.return_value = {"products": []}
        mock_shopify_http.get.return_value.headers = {}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        result = await client.get_all_products()

        assert result == []

    async def test_http_error(self) -> None:
        """Raises on HTTP error."""
        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock(spec=Response)
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response

            client = ShopifyClient(SHOPIFY_TEST_SHOP, "bad-token")

            with pytest.raises(HTTPStatusError):
                await client.get_all_products()


# ---------------------------------------------------------------------------
# Tests: get_pages
# ---------------------------------------------------------------------------


class TestGetPages:
    """Tests for fetching store pages."""

    async def test_returns_pages(self, mock_shopify_http: MagicMock) -> None:
        """Returns pages array."""
        pages = [
            {"id": 1, "title": "About Us"},
            {"id": 2, "title": "Contact"},
        ]
        mock_shopify_http.get.return_value.json.return_value = {"pages": pages}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        result = await client.get_pages()

        assert len(result) == 2
        assert result[0]["title"] == "About Us"

    async def test_empty_pages(self, mock_shopify_http: MagicMock) -> None:
        """Handles empty pages list."""
        mock_shopify_http.get.return_value.json.return_value = {"pages": []}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        result = await client.get_pages()

        assert result == []


# ---------------------------------------------------------------------------
# Tests: register_webhooks
# ---------------------------------------------------------------------------


class TestRegisterWebhooks:
    """Tests for webhook registration."""

    async def test_creates_three_webhooks(self) -> None:
        """POSTs to webhooks.json 3 times (create, update, delete)."""
        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.is_success = True
            mock_client.post.return_value = mock_response

            client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
            await client.register_webhooks()

            assert mock_client.post.call_count == 3

            # Verify topics
            topics_registered = []
            for call in mock_client.post.call_args_list:
                payload = call[1]["json"]["webhook"]
                topics_registered.append(payload["topic"])

            assert "products/create" in topics_registered
            assert "products/update" in topics_registered
            assert "products/delete" in topics_registered

    async def test_logs_warning_on_failure(self, caplog: Any) -> None:
        """Non-fatal failures are logged, not raised."""
        import logging

        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            # First webhook succeeds, second fails, third succeeds
            success_response = MagicMock()
            success_response.is_success = True

            failure_response = MagicMock()
            failure_response.is_success = False
            failure_response.status_code = 422

            mock_client.post.side_effect = [
                success_response,
                failure_response,
                success_response,
            ]

            with caplog.at_level(logging.WARNING):
                client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
                # Should not raise
                await client.register_webhooks()

            # Should have logged the failure
            assert "Failed to register webhook" in caplog.text

    async def test_webhook_addresses_are_correct(self) -> None:
        """Webhook addresses point to correct endpoints."""
        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.is_success = True
            mock_client.post.return_value = mock_response

            client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
            await client.register_webhooks()

            addresses = []
            for call in mock_client.post.call_args_list:
                payload = call[1]["json"]["webhook"]
                addresses.append(payload["address"])

            # All addresses should contain the webhook path
            assert all("/api/v1/webhooks/shopify/" in addr for addr in addresses)
            assert any("products-create" in addr for addr in addresses)
            assert any("products-update" in addr for addr in addresses)
            assert any("products-delete" in addr for addr in addresses)


# ---------------------------------------------------------------------------
# Tests: delete_webhooks
# ---------------------------------------------------------------------------


class TestDeleteWebhooks:
    """Tests for webhook deletion."""

    async def test_deletes_all_webhooks(self) -> None:
        """DELETEs each webhook returned by GET."""
        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            # GET returns 2 webhooks
            get_response = MagicMock()
            get_response.json.return_value = {
                "webhooks": [
                    {"id": 111},
                    {"id": 222},
                ]
            }
            get_response.raise_for_status = MagicMock()

            mock_client.get.return_value = get_response
            mock_client.delete.return_value = MagicMock()

            client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
            await client.delete_webhooks()

            # Should delete both webhooks
            assert mock_client.delete.call_count == 2

            # Verify correct webhook IDs were deleted
            delete_urls = [call[0][0] for call in mock_client.delete.call_args_list]
            assert any("111" in url for url in delete_urls)
            assert any("222" in url for url in delete_urls)

    async def test_handles_no_webhooks(self) -> None:
        """Handles case where no webhooks exist."""
        with patch("app.integrations.shopify.client.httpx.AsyncClient") as mock_class:
            mock_client = AsyncMock()
            mock_class.return_value.__aenter__.return_value = mock_client

            get_response = MagicMock()
            get_response.json.return_value = {"webhooks": []}
            get_response.raise_for_status = MagicMock()
            mock_client.get.return_value = get_response

            client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
            await client.delete_webhooks()

            mock_client.delete.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: _get_next_page_url
# ---------------------------------------------------------------------------


class TestGetNextPageUrl:
    """Tests for Link header parsing."""

    def test_parses_link_header(self) -> None:
        """Correctly extracts rel="next" URL."""
        mock_response = MagicMock()
        mock_response.headers = {"link": '<https://shop.myshopify.com/page2>; rel="next"'}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        url = client._get_next_page_url(mock_response)

        assert url == "https://shop.myshopify.com/page2"

    def test_returns_none_when_no_next(self) -> None:
        """Returns None if no next page."""
        mock_response = MagicMock()
        mock_response.headers = {"link": '<https://shop/page1>; rel="previous"'}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        url = client._get_next_page_url(mock_response)

        assert url is None

    def test_returns_none_when_no_link_header(self) -> None:
        """Returns None if Link header is absent."""
        mock_response = MagicMock()
        mock_response.headers = {}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        url = client._get_next_page_url(mock_response)

        assert url is None

    def test_handles_multiple_links(self) -> None:
        """Extracts next from multiple Link values."""
        mock_response = MagicMock()
        mock_response.headers = {
            "link": '<https://shop/prev>; rel="previous", <https://shop/next>; rel="next"'
        }

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        url = client._get_next_page_url(mock_response)

        assert url == "https://shop/next"

    def test_handles_empty_link_header(self) -> None:
        """Handles empty Link header value."""
        mock_response = MagicMock()
        mock_response.headers = {"link": ""}

        client = ShopifyClient(SHOPIFY_TEST_SHOP, "token")
        url = client._get_next_page_url(mock_response)

        assert url is None

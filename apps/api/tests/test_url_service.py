"""Tests for URL content extraction service.

Tests SSRF protection, HTML parsing, and content extraction.
These are pure unit tests with no database dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.url_service import (
    _html_to_text,
    _validate_url,
    fetch_url_content,
)


class TestValidateUrl:
    """Tests for _validate_url() SSRF protection."""

    def test_accepts_https(self) -> None:
        """HTTPS URLs are accepted."""
        # Mock DNS resolution to return a public IP
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),  # example.com public IP
            ]
            # Should not raise
            _validate_url("https://example.com/page")

    def test_accepts_http(self) -> None:
        """HTTP URLs are accepted."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 0)),
            ]
            _validate_url("http://example.com/page")

    def test_rejects_ftp_scheme(self) -> None:
        """FTP scheme is rejected."""
        with pytest.raises(ValueError, match="Unsupported URL scheme: ftp"):
            _validate_url("ftp://files.example.com/file.txt")

    def test_rejects_file_scheme(self) -> None:
        """File scheme is rejected (path traversal attack)."""
        with pytest.raises(ValueError, match="Unsupported URL scheme: file"):
            _validate_url("file:///etc/passwd")

    def test_rejects_javascript_scheme(self) -> None:
        """JavaScript scheme is rejected."""
        with pytest.raises(ValueError, match="Unsupported URL scheme: javascript"):
            _validate_url("javascript:alert(1)")

    def test_rejects_localhost(self) -> None:
        """URLs resolving to localhost (127.0.0.1) are rejected."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("127.0.0.1", 0)),
            ]
            with pytest.raises(ValueError, match="private/reserved address"):
                _validate_url("http://localhost/admin")

    def test_rejects_loopback_ipv6(self) -> None:
        """URLs resolving to IPv6 loopback (::1) are rejected."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (10, 1, 6, "", ("::1", 0, 0, 0)),
            ]
            with pytest.raises(ValueError, match="private/reserved address"):
                _validate_url("http://ipv6-localhost/")

    def test_rejects_private_ip_10_range(self) -> None:
        """URLs resolving to 10.x.x.x private range are rejected."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("10.0.0.1", 0)),
            ]
            with pytest.raises(ValueError, match="private/reserved address"):
                _validate_url("http://internal-service.local/")

    def test_rejects_private_ip_172_range(self) -> None:
        """URLs resolving to 172.16-31.x.x private range are rejected."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("172.16.0.1", 0)),
            ]
            with pytest.raises(ValueError, match="private/reserved address"):
                _validate_url("http://docker-internal/")

    def test_rejects_private_ip_192_168_range(self) -> None:
        """URLs resolving to 192.168.x.x private range are rejected."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("192.168.1.1", 0)),
            ]
            with pytest.raises(ValueError, match="private/reserved address"):
                _validate_url("http://router.local/")

    def test_rejects_link_local(self) -> None:
        """URLs resolving to link-local (169.254.x.x) are rejected."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (2, 1, 6, "", ("169.254.169.254", 0)),  # AWS metadata endpoint
            ]
            with pytest.raises(ValueError, match="private/reserved address"):
                _validate_url("http://169.254.169.254/latest/meta-data/")

    def test_rejects_unresolvable_host(self) -> None:
        """URLs with unresolvable hostnames are rejected."""
        import socket

        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror(8, "Name or service not known")
            with pytest.raises(ValueError, match="Could not resolve hostname"):
                _validate_url("http://this-domain-does-not-exist-xyz123.com/")

    def test_rejects_url_without_hostname(self) -> None:
        """URLs without a hostname are rejected."""
        with pytest.raises(ValueError, match="URL has no hostname"):
            _validate_url("http:///path/only")

    def test_accepts_public_ip(self) -> None:
        """URLs resolving to public IPs are accepted."""
        with patch("socket.getaddrinfo") as mock_dns:
            # Google's public DNS
            mock_dns.return_value = [
                (2, 1, 6, "", ("8.8.8.8", 0)),
            ]
            # Should not raise
            _validate_url("http://dns.google/")


class TestHtmlToText:
    """Tests for _html_to_text() HTML stripping."""

    def test_extracts_title(self) -> None:
        """Title tag content is extracted."""
        html = "<html><head><title>My Page Title</title></head><body>Content</body></html>"
        text, title = _html_to_text(html)
        assert title == "My Page Title"

    def test_strips_script_tags(self) -> None:
        """Script tags and their content are removed."""
        html = """
        <html>
        <head><script>alert('xss');</script></head>
        <body>
            <p>Safe content</p>
            <script type="text/javascript">
                var malicious = true;
            </script>
        </body>
        </html>
        """
        text, _ = _html_to_text(html)
        assert "alert" not in text
        assert "malicious" not in text
        assert "Safe content" in text

    def test_strips_style_tags(self) -> None:
        """Style tags and their content are removed."""
        html = """
        <html>
        <head><style>.hidden { display: none; }</style></head>
        <body><p>Visible content</p></body>
        </html>
        """
        text, _ = _html_to_text(html)
        assert "hidden" not in text
        assert "display" not in text
        assert "Visible content" in text

    def test_strips_all_html_tags(self) -> None:
        """All HTML tags are removed, leaving only text content."""
        html = "<div><p>First <strong>bold</strong> text</p><a href='/'>Link</a></div>"
        text, _ = _html_to_text(html)
        assert "<" not in text
        assert ">" not in text
        assert "bold" in text
        assert "Link" in text

    def test_collapses_excessive_whitespace(self) -> None:
        """Multiple consecutive newlines are collapsed."""
        html = "<p>First</p>\n\n\n\n\n<p>Second</p>"
        text, _ = _html_to_text(html)
        # Should have at most 2 newlines between paragraphs
        assert "\n\n\n" not in text

    def test_no_title_returns_none(self) -> None:
        """HTML without title tag returns None for title."""
        html = "<html><body><p>No title here</p></body></html>"
        text, title = _html_to_text(html)
        assert title is None
        assert "No title here" in text

    def test_handles_empty_title(self) -> None:
        """Empty title tag returns empty string (stripped)."""
        html = "<html><head><title>   </title></head><body>Content</body></html>"
        _, title = _html_to_text(html)
        # Empty after strip
        assert title == ""


class TestFetchUrlContent:
    """Tests for fetch_url_content() async URL fetching."""

    @pytest.mark.asyncio
    async def test_fetches_html_content(self) -> None:
        """HTML content is fetched and converted to text."""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
        <head><title>Test Page</title></head>
        <body><p>This is the page content.</p></body>
        </html>
        """
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            text, title = await fetch_url_content("https://example.com/page")

        assert "This is the page content" in text
        assert title == "Test Page"

    @pytest.mark.asyncio
    async def test_fetches_plain_text_content(self) -> None:
        """Plain text content is returned as-is."""
        mock_response = MagicMock()
        mock_response.text = "This is plain text content without HTML."
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            text, title = await fetch_url_content("https://example.com/file.txt")

        assert text == "This is plain text content without HTML."
        # When no title extracted, URL is used as fallback
        assert title == "https://example.com/file.txt"

    @pytest.mark.asyncio
    async def test_raises_on_empty_content(self) -> None:
        """ValueError is raised when no text can be extracted."""
        mock_response = MagicMock()
        mock_response.text = "<html><body></body></html>"  # Empty body
        mock_response.headers = {"content-type": "text/html"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ValueError, match="No text content could be extracted"):
                await fetch_url_content("https://example.com/empty")

    @pytest.mark.asyncio
    async def test_validates_url_before_fetch(self) -> None:
        """URL validation happens before making the HTTP request."""
        # Should fail at validation, not at fetch
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            await fetch_url_content("ftp://files.example.com/")

    @pytest.mark.asyncio
    async def test_rejects_ssrf_attempt(self) -> None:
        """SSRF attempts are blocked before HTTP request is made."""
        with patch("socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(2, 1, 6, "", ("127.0.0.1", 0))]

            with pytest.raises(ValueError, match="private/reserved address"):
                await fetch_url_content("http://internal-api.local/secret")

    @pytest.mark.asyncio
    async def test_handles_xml_content_type(self) -> None:
        """XML content is treated like HTML and stripped."""
        mock_response = MagicMock()
        mock_response.text = """<?xml version="1.0"?>
        <root><item>XML Content Here</item></root>
        """
        mock_response.headers = {"content-type": "text/xml"}
        mock_response.raise_for_status = MagicMock()

        with (
            patch("socket.getaddrinfo") as mock_dns,
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            text, _ = await fetch_url_content("https://example.com/feed.xml")

        assert "XML Content Here" in text
        assert "<item>" not in text

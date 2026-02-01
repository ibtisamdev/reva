"""URL content extraction service."""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> tuple[str, str | None]:
    """Strip HTML tags and return plain text + extracted title.

    Returns:
        Tuple of (plain_text, title_or_none).
    """
    # Extract title
    title_match = _TITLE_RE.search(html)
    title = title_match.group(1).strip() if title_match else None

    # Remove script/style blocks
    text = _SCRIPT_STYLE_RE.sub("", html)
    # Remove tags
    text = _TAG_RE.sub("\n", text)
    # Collapse whitespace
    text = _WHITESPACE_RE.sub("\n\n", text).strip()

    return text, title


def _validate_url(url: str) -> None:
    """Validate that a URL is safe to fetch (no SSRF).

    Raises:
        ValueError: If the URL scheme is not http/https or resolves to a private IP.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    # Resolve hostname and check all addresses
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve hostname: {hostname}") from exc

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"URL resolves to a private/reserved address: {ip}")


async def fetch_url_content(url: str) -> tuple[str, str]:
    """Fetch a URL and extract its text content.

    Args:
        url: The URL to fetch.

    Returns:
        Tuple of (extracted_text, page_title).

    Raises:
        httpx.HTTPStatusError: If the response status is not 2xx.
        ValueError: If no text could be extracted or the URL is unsafe.
    """
    _validate_url(url)

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        response = await client.get(url, headers={"User-Agent": "Reva-Bot/1.0"})
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        if "text/html" in content_type or "text/xml" in content_type:
            text, title = _html_to_text(response.text)
        else:
            # Plain text or other text formats
            text = response.text
            title = None

    if not text.strip():
        raise ValueError("No text content could be extracted from the URL.")

    return text, title or url

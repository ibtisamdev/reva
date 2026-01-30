"""Shopify webhook HMAC verification."""

import base64
import hashlib
import hmac


def verify_webhook(data: bytes, hmac_header: str, secret: str) -> bool:
    """Verify a Shopify webhook's HMAC-SHA256 signature.

    Args:
        data: The raw request body bytes.
        hmac_header: The X-Shopify-Hmac-Sha256 header value.
        secret: The Shopify client secret.

    Returns:
        True if the signature is valid.
    """
    computed = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            data,
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    return hmac.compare_digest(computed, hmac_header)

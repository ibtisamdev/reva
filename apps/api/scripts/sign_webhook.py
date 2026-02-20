"""HMAC signing helper for simulating Shopify webhooks.

Reads JSON body from stdin and outputs a base64-encoded HMAC-SHA256 signature
using the SHOPIFY_CLIENT_SECRET from the environment (or .env file).

Usage:
    echo '{"id": 123}' | cd apps/api && uv run python -m scripts.sign_webhook

    # Or pipe from a file:
    cat payload.json | uv run python -m scripts.sign_webhook

    # Full curl example:
    BODY='{"id":99001,"token":"tok_001","email":"test@example.com"}'
    HMAC=$(echo -n "$BODY" | uv run python -m scripts.sign_webhook)
    curl -X POST http://localhost:8000/api/v1/webhooks/shopify/checkouts-create \\
      -H "Content-Type: application/json" \\
      -H "X-Shopify-Hmac-Sha256: $HMAC" \\
      -H "X-Shopify-Shop-Domain: test-recovery.myshopify.com" \\
      -d "$BODY"
"""

import base64
import hashlib
import hmac
import sys

from app.core.config import settings


def sign(body: bytes, secret: str) -> str:
    """Compute base64-encoded HMAC-SHA256 signature."""
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def main() -> None:
    secret = settings.shopify_client_secret
    if not secret:
        print("ERROR: SHOPIFY_CLIENT_SECRET is not set in .env", file=sys.stderr)
        sys.exit(1)

    body = sys.stdin.buffer.read()
    if not body:
        print("ERROR: No input received on stdin", file=sys.stderr)
        sys.exit(1)

    signature = sign(body, secret)
    print(signature, end="")


if __name__ == "__main__":
    main()

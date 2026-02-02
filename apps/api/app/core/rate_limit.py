"""Rate limiting configuration using slowapi."""

from slowapi import Limiter
from starlette.requests import Request


def _get_real_client_ip(request: Request) -> str:
    """Extract the real client IP behind Cloudflare Tunnel / reverse proxy."""
    return (
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "127.0.0.1")
    )


limiter = Limiter(key_func=_get_real_client_ip)

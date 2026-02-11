"""JWT authentication for FastAPI using Better Auth JWKS."""

import asyncio
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

from app.core.config import settings

# HTTP Bearer token security scheme
bearer_scheme = HTTPBearer(auto_error=False)

# JWKS client for fetching public keys from Better Auth
_jwks_client: PyJWKClient | None = None
_jwks_lock = asyncio.Lock()


def get_jwks_client() -> PyJWKClient:
    """Get or create JWKS client."""
    global _jwks_client
    if _jwks_client is None:
        if settings.auth_jwks_url:
            jwks_url = settings.auth_jwks_url
        else:
            jwks_url = f"{settings.auth_url}/api/auth/jwks"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


async def verify_token(token: str) -> dict[str, Any]:
    """Verify JWT token using Better Auth's JWKS.

    Args:
        token: The JWT token to verify

    Returns:
        The decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.auth_url,
            issuer=settings.auth_url,
            options={
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except PyJWKClientError as e:
        # Reset cached client so next request retries fresh
        async with _jwks_lock:
            global _jwks_client
            _jwks_client = None
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Authentication service unavailable. Unable to verify token: {str(e)}",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Get current authenticated user from JWT token.

    This is a FastAPI dependency that extracts and verifies the JWT token
    from the Authorization header.

    Returns:
        The decoded JWT payload containing user information

    Raises:
        HTTPException: If no token provided or token is invalid
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await verify_token(credentials.credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any] | None:
    """Get current user if authenticated, otherwise return None.

    This is useful for endpoints that work for both authenticated and
    anonymous users.

    Returns:
        The decoded JWT payload or None if not authenticated
    """
    if credentials is None:
        return None

    try:
        return await verify_token(credentials.credentials)
    except HTTPException:
        return None


# Type aliases for dependency injection
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
OptionalUser = Annotated[dict[str, Any] | None, Depends(get_optional_user)]

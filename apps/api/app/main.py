"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.v1.router import api_router
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.project_name} v{settings.version}")
    print(f"Environment: {settings.environment}")
    yield
    # Shutdown
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs",
        redoc_url=f"{settings.api_v1_prefix}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Global exception handler to ensure CORS headers are present on 500 errors
    # Without this, unhandled exceptions cause the response to skip CORS middleware,
    # making browsers show "CORS blocked" instead of the actual error
    @app.exception_handler(Exception)
    async def global_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        """Handle unhandled exceptions with proper JSON response."""
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Redirect /docs to versioned docs URL
    @app.get("/docs", include_in_schema=False)
    async def docs_redirect() -> RedirectResponse:
        return RedirectResponse(url=f"{settings.api_v1_prefix}/docs")

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "name": settings.project_name,
            "version": settings.version,
            "docs": f"{settings.api_v1_prefix}/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()

"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Reva API"
    version: str = "0.1.0"

    # Database
    database_url: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/reva"
    )

    # Redis
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # Shopify
    shopify_client_id: str = ""
    shopify_client_secret: str = ""
    shopify_scopes: str = "read_products,read_content"
    shopify_api_version: str = "2025-01"

    # URLs
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # LLM APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Email
    resend_api_key: str = ""

    # Security
    secret_key: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    encryption_key: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"

    # Authentication (Better Auth)
    auth_url: str = "http://localhost:3000"  # Next.js app URL where Better Auth runs
    auth_jwks_url: str = ""  # Internal URL for JWKS fetch (Docker: http://web:3000/api/auth/jwks)

    # Error tracking (GlitchTip/Sentry)
    sentry_dsn: str = ""

    # Database pool
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # CORS — set via ALLOWED_ORIGINS env var as JSON array: '["https://example.com"]'
    allowed_origins: list[str] = [
        "http://localhost:3000",  # Next.js dashboard
        "http://localhost:5173",  # Vite widget dev
    ]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

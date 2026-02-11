"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(plain_client: AsyncClient) -> None:
    """Test root endpoint returns API info."""
    response = await plain_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_liveness(plain_client: AsyncClient) -> None:
    """Test liveness probe endpoint."""
    response = await plain_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"

"""
Integration test for health endpoint.
Verifies the FastAPI app responds with 200 on GET /health.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.app import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that /health returns 200 with {status: ok}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

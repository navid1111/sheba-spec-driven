"""
Integration tests for /metrics endpoint and metrics collection.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from src.api.app import app
from src.lib.metrics import reset_metrics


@pytest.fixture(autouse=True)
def clear_metrics():
    """Clear metrics before each test."""
    reset_metrics()
    yield
    reset_metrics()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format():
    """Test /metrics endpoint returns Prometheus text format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_endpoint_empty_when_no_metrics():
    """Test /metrics endpoint returns empty when no metrics recorded."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
    
    assert response.status_code == 200
    # Empty metrics should return empty string
    assert response.text == '""' or response.text == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_endpoint_exports_after_activity():
    """Test /metrics endpoint exports counters after activity."""
    from src.lib.metrics import get_metrics_collector
    
    # Simulate some activity
    metrics = get_metrics_collector()
    metrics.increment_sends("smartengage", "SMS", "REMINDER", amount=5)
    metrics.increment_opens("smartengage", "SMS", source="app", amount=3)
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
    
    assert response.status_code == 200
    output = response.text.strip('"').replace('\\n', '\n')
    
    # Verify metrics are in output
    assert "ai_messages_sent_total" in output
    assert "user_events_total" in output
    assert "} 5" in output  # sends count
    assert "} 3" in output  # opens count

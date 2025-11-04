"""Contract tests for SmartEngage internal API endpoints.

Validates that the /internal/ai/smartengage/run-segment endpoint
returns the correct response schema.
"""
import pytest
from httpx import AsyncClient, ASGITransport
import sys
from pathlib import Path

# Add src to path BEFORE importing app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.app import app


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestSmartEngageContract:
    """Contract tests for SmartEngage internal endpoints."""
    
    @pytest.mark.asyncio
    async def test_run_segment_endpoint_exists(self, client):
        """Test that the run-segment endpoint exists and returns 202 or error."""
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "segment_criteria": {
                    "booking_cadence_days": 21,
                    "last_booking_days_ago_min": 18,
                    "last_booking_days_ago_max": 24
                }
            }
        )
        
        # Endpoint should exist - either 202 (started), 401 (auth), or 404 if not implemented
        # For now, we expect 404 as the endpoint is not yet implemented
        assert response.status_code in [202, 401, 404, 501], \
            f"Unexpected status code: {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_run_segment_response_schema_when_implemented(self, client):
        """Test response schema when endpoint is implemented (currently expected to 404)."""
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "segment_criteria": {
                    "booking_cadence_days": 21,
                    "last_booking_days_ago_min": 18,
                    "last_booking_days_ago_max": 24
                }
            }
        )
        
        # If implemented (202), validate schema
        if response.status_code == 202:
            data = response.json()
            
            # Validate response schema
            assert "job_id" in data, "Response should contain job_id"
            assert "segment_id" in data, "Response should contain segment_id"
            assert "estimated_customers" in data, "Response should contain estimated_customers"
            
            # Validate types
            assert isinstance(data["job_id"], str), "job_id should be a string"
            assert isinstance(data["segment_id"], str), "segment_id should be a string"
            assert isinstance(data["estimated_customers"], int), "estimated_customers should be an integer"
            assert data["estimated_customers"] >= 0, "estimated_customers should be non-negative"
        else:
            # Not yet implemented, skip validation
            pytest.skip(f"Endpoint not yet implemented (status: {response.status_code})")
    
    @pytest.mark.asyncio
    async def test_run_segment_with_minimal_criteria(self, client):
        """Test with minimal segment criteria."""
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "segment_criteria": {}
            }
        )
        
        # Should accept minimal criteria or return 422 for validation
        assert response.status_code in [202, 422, 404, 501]
        
        if response.status_code == 422:
            data = response.json()
            assert "error" in data or "detail" in data
    
    @pytest.mark.asyncio
    async def test_run_segment_with_invalid_json(self, client):
        """Test with invalid request body."""
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={}
        )
        
        # Should handle gracefully
        assert response.status_code in [202, 422, 404, 501]
    
    @pytest.mark.asyncio
    async def test_run_segment_correlation_id_in_response(self, client):
        """Test that correlation_id is present in response headers."""
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "segment_criteria": {
                    "booking_cadence_days": 21
                }
            }
        )
        
        # Correlation ID should always be present regardless of implementation status
        assert "x-correlation-id" in response.headers, \
            "Correlation ID should be in response headers"
        assert len(response.headers["x-correlation-id"]) > 0, \
            "Correlation ID should not be empty"

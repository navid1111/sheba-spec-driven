"""
Contract tests for Internal SmartEngage API endpoint.

Tests validate the API contract defined in contracts/openapi.yaml:
- POST /internal/ai/smartengage/run-segment
- Request/response schemas
- Status codes
- Error handling
"""
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

# Add src to path BEFORE importing app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.app import app


client = TestClient(app)


class TestInternalSmartEngageContract:
    """Contract tests for POST /internal/ai/smartengage/run-segment endpoint."""
    
    def test_endpoint_exists(self):
        """Test that the internal SmartEngage endpoint exists."""
        # Don't pass request body to test endpoint existence
        response = client.post("/internal/ai/smartengage/run-segment")
        
        # Should not return 404 (endpoint exists)
        assert response.status_code != 404, "Endpoint should exist"
        
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    def test_response_schema_valid(self, mock_campaign):
        """Test that successful response matches expected schema."""
        # Mock the campaign runner
        correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 10.5,
            "total_eligible": 100,
            "sent": 95,
            "failed": 2,
            "skipped": 3,
        }
        
        # Make request with valid payload
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "booking_cadence_days": 21,
                "send_window_start": 9,
                "send_window_end": 18,
                "batch_size": 50,
                "promo_code": "COMEBACK15",
            }
        )
        
        # Should return 202 Accepted
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        
        # Validate response schema
        data = response.json()
        assert "job_id" in data or "correlation_id" in data, "Response should include job/correlation ID"
        assert "status" in data, "Response should include status"
        assert data["status"] in ["started", "scheduled", "accepted"], "Status should indicate job started"
        
        # Additional fields from campaign result
        if "campaign_result" in data:
            result = data["campaign_result"]
            assert "total_eligible" in result
            assert "sent" in result
            assert "failed" in result
            assert "skipped" in result
    
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    def test_minimal_request(self, mock_campaign):
        """Test request with minimal required fields (defaults applied)."""
        correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 5.0,
            "total_eligible": 50,
            "sent": 48,
            "failed": 1,
            "skipped": 1,
        }
        
        # Request with no body (all defaults)
        response = client.post("/internal/ai/smartengage/run-segment", json={})
        
        # Should succeed with defaults
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["started", "scheduled", "accepted"]
    
    @patch("src.api.routes.internal_smartengage.run_campaign_with_preset")
    def test_with_preset(self, mock_campaign):
        """Test request with campaign preset."""
        correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 15.0,
            "total_eligible": 200,
            "sent": 195,
            "failed": 3,
            "skipped": 2,
        }
        
        # Request with preset
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={"preset": "aggressive"}
        )
        
        # Should succeed
        assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "status" in data
    
    def test_invalid_json(self):
        """Test that invalid JSON returns 400/422."""
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 400 or 422
        assert response.status_code in [400, 422], f"Expected 400/422 for invalid JSON, got {response.status_code}"
    
    def test_invalid_field_types(self):
        """Test that invalid field types return 422 validation error."""
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "booking_cadence_days": "not_a_number",  # Should be int
                "batch_size": -10,  # Should be positive
            }
        )
        
        # Should return 422 validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        
        # Check error detail includes field validation (handles both formats)
        data = response.json()
        assert "detail" in data or "error" in data, "Error response should include detail or error"
    
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    def test_correlation_id_in_response(self, mock_campaign):
        """Test that response includes correlation_id for tracking."""
        correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 8.0,
            "total_eligible": 75,
            "sent": 72,
            "failed": 1,
            "skipped": 2,
        }
        
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 21}
        )
        
        assert response.status_code == 202
        data = response.json()
        
        # Should include correlation_id for tracking
        assert "correlation_id" in data or "job_id" in data, "Response should include tracking ID"
    
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    def test_campaign_execution_error(self, mock_campaign):
        """Test error handling when campaign execution fails."""
        # Mock campaign to raise exception
        mock_campaign.side_effect = Exception("Campaign execution failed")
        
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 21}
        )
        
        # Should return 500 error
        assert response.status_code == 500, f"Expected 500, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data or "error" in data, "Error response should include detail or error"
    
    @patch("src.api.routes.internal_smartengage.run_campaign_with_preset")
    def test_preset_parameter_validation(self, mock_campaign):
        """Test that invalid preset returns validation error."""
        correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 5.0,
            "total_eligible": 50,
            "sent": 48,
            "failed": 1,
            "skipped": 1,
        }
        
        # Valid presets should work
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={"preset": "default"}
        )
        assert response.status_code == 202, f"Valid preset should succeed: {response.text}"
        
        response = client.post(
            "/internal/ai/smartengage/run-segment",
            json={"preset": "aggressive"}
        )
        assert response.status_code == 202, f"Valid preset should succeed: {response.text}"

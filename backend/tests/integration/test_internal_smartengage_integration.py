"""
Integration tests for Internal SmartEngage API endpoint.

Tests the full integration flow of triggering SmartEngage campaigns
through the internal API and verifying the results.
"""
import pytest
from httpx import AsyncClient, ASGITransport
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

# Add src to path BEFORE importing app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.app import app


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestInternalSmartEngageIntegration:
    """Integration tests for internal SmartEngage campaign triggering."""
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    async def test_trigger_campaign_with_custom_params(self, mock_campaign, client):
        """Test triggering campaign with custom parameters."""
        # Mock successful campaign execution
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
        
        # Trigger campaign
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "booking_cadence_days": 21,
                "send_window_start": 9,
                "send_window_end": 18,
                "batch_size": 50,
                "promo_code": "COMEBACK15",
            }
        )
        
        # Verify response
        assert response.status_code == 202
        data = response.json()
        
        assert data["status"] == "started"
        assert "correlation_id" in data
        assert "campaign_result" in data
        
        # Verify campaign parameters were passed correctly
        mock_campaign.assert_called_once_with(
            booking_cadence_days=21,
            send_window_start=9,
            send_window_end=18,
            batch_size=50,
            promo_code="COMEBACK15",
        )
        
        # Verify campaign results
        result = data["campaign_result"]
        assert result["total_eligible"] == 100
        assert result["sent"] == 95
        assert result["failed"] == 2
        assert result["skipped"] == 3
        assert result["duration_seconds"] == 10.5
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_campaign_with_preset")
    async def test_trigger_campaign_with_preset(self, mock_preset, client):
        """Test triggering campaign using predefined preset."""
        # Mock successful preset execution
        correlation_id = uuid4()
        mock_preset.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 15.0,
            "total_eligible": 200,
            "sent": 195,
            "failed": 3,
            "skipped": 2,
        }
        
        # Trigger aggressive preset
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"preset": "aggressive"}
        )
        
        # Verify response
        assert response.status_code == 202
        data = response.json()
        
        assert data["status"] == "started"
        assert "correlation_id" in data
        
        # Verify preset was called
        mock_preset.assert_called_once_with("aggressive")
        
        # Verify results
        result = data["campaign_result"]
        assert result["total_eligible"] == 200
        assert result["sent"] == 195
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    async def test_trigger_campaign_with_defaults(self, mock_campaign, client):
        """Test triggering campaign with default parameters."""
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
        
        # Trigger with empty body (all defaults)
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={}
        )
        
        # Verify response
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "started"
        
        # Verify defaults were used
        mock_campaign.assert_called_once_with(
            booking_cadence_days=21,  # default
            send_window_start=9,      # default
            send_window_end=18,       # default
            batch_size=50,            # default
            promo_code=None,          # default
        )
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    async def test_campaign_execution_failure_handling(self, mock_campaign, client):
        """Test error handling when campaign execution fails."""
        # Mock campaign failure
        mock_campaign.side_effect = Exception("Database connection failed")
        
        # Trigger campaign
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 21}
        )
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "error" in data or "detail" in data
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    async def test_correlation_id_tracking(self, mock_campaign, client):
        """Test that correlation ID is properly tracked and returned."""
        expected_correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": expected_correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 5.0,
            "total_eligible": 50,
            "sent": 48,
            "failed": 1,
            "skipped": 1,
        }
        
        # Trigger campaign
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 21}
        )
        
        # Verify correlation ID is returned
        assert response.status_code == 202
        data = response.json()
        assert data["correlation_id"] == str(expected_correlation_id)
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_campaign_with_preset")
    async def test_multiple_presets(self, mock_preset, client):
        """Test that different presets can be triggered."""
        presets = ["default", "aggressive", "gentle", "weekend"]
        
        for preset_name in presets:
            correlation_id = uuid4()
            mock_preset.return_value = {
                "correlation_id": correlation_id,
                "started_at": datetime.now(timezone.utc),
                "finished_at": datetime.now(timezone.utc),
                "duration_seconds": 10.0,
                "total_eligible": 100,
                "sent": 95,
                "failed": 2,
                "skipped": 3,
            }
            
            # Trigger preset
            response = await client.post(
                "/internal/ai/smartengage/run-segment",
                json={"preset": preset_name}
            )
            
            # Should succeed
            assert response.status_code == 202, f"Preset {preset_name} should succeed"
            
            # Verify preset was called
            mock_preset.assert_called_with(preset_name)
            mock_preset.reset_mock()
    
    @pytest.mark.asyncio
    async def test_parameter_validation(self, client):
        """Test that invalid parameters are rejected."""
        # Invalid cadence (too low)
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 5}  # minimum is 7
        )
        assert response.status_code == 422
        
        # Invalid cadence (too high)
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 100}  # maximum is 90
        )
        assert response.status_code == 422
        
        # Invalid batch size (negative)
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"batch_size": -10}
        )
        assert response.status_code == 422
        
        # Invalid batch size (too large)
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"batch_size": 2000}  # maximum is 1000
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    @patch("src.api.routes.internal_smartengage.run_smartengage_campaign")
    async def test_promo_code_handling(self, mock_campaign, client):
        """Test that promo codes are properly passed to campaign."""
        correlation_id = uuid4()
        mock_campaign.return_value = {
            "correlation_id": correlation_id,
            "started_at": datetime.now(timezone.utc),
            "finished_at": datetime.now(timezone.utc),
            "duration_seconds": 8.0,
            "total_eligible": 80,
            "sent": 75,
            "failed": 2,
            "skipped": 3,
        }
        
        # Test with promo code
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={
                "booking_cadence_days": 21,
                "promo_code": "COMEBACK15"
            }
        )
        
        assert response.status_code == 202
        
        # Verify promo code was passed
        call_kwargs = mock_campaign.call_args[1]
        assert call_kwargs["promo_code"] == "COMEBACK15"
        
        # Test without promo code
        mock_campaign.reset_mock()
        response = await client.post(
            "/internal/ai/smartengage/run-segment",
            json={"booking_cadence_days": 21}
        )
        
        assert response.status_code == 202
        
        # Verify no promo code
        call_kwargs = mock_campaign.call_args[1]
        assert call_kwargs["promo_code"] is None

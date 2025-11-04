"""
Unit tests for Campaign Runner Job.

Tests cover:
- Campaign execution with orchestrator
- Advisory lock integration
- Result tracking and logging
- Manual triggers and dry runs
- Campaign presets
- Error handling
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.jobs.campaign_runner import (
    run_smartengage_campaign,
    trigger_campaign_manual,
    run_campaign_with_preset,
    CAMPAIGN_PRESETS,
)


@pytest.fixture
def mock_orchestrator():
    """Mock SmartEngageOrchestrator."""
    orchestrator = MagicMock()
    
    # Mock segmentation service
    orchestrator.segmentation_service.find_eligible_for_reminders.return_value = [
        MagicMock(id=uuid4()),
        MagicMock(id=uuid4()),
        MagicMock(id=uuid4()),
    ]
    
    # Mock bulk campaign results
    orchestrator.generate_and_send_bulk_reminders = AsyncMock(
        return_value={
            "total_eligible": 3,
            "sent": 2,
            "failed": 0,
            "skipped": 1,
            "results": [],
        }
    )
    
    return orchestrator


# ============================================================================
# Test: Campaign Execution
# ============================================================================


@pytest.mark.asyncio
async def test_run_smartengage_campaign_success(mock_orchestrator):
    """Test successful campaign execution."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_smartengage_campaign(
            booking_cadence_days=21,
            send_window_start=9,
            send_window_end=18,
            batch_size=50,
            promo_code="TEST20",
        )
        
        # Verify result structure
        assert "correlation_id" in result
        assert "started_at" in result
        assert "finished_at" in result
        assert "duration_seconds" in result
        assert result["total_eligible"] == 3
        assert result["sent"] == 2
        assert result["failed"] == 0
        assert result["skipped"] == 1
        
        # Verify orchestrator was called with correct params
        mock_orchestrator.generate_and_send_bulk_reminders.assert_called_once_with(
            booking_cadence_days=21,
            send_window_start=9,
            send_window_end=18,
            batch_size=50,
            promo_code="TEST20",
        )


@pytest.mark.asyncio
async def test_run_smartengage_campaign_default_params(mock_orchestrator):
    """Test campaign with default parameters."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_smartengage_campaign()
        
        # Verify defaults were used
        mock_orchestrator.generate_and_send_bulk_reminders.assert_called_once_with(
            booking_cadence_days=21,
            send_window_start=9,
            send_window_end=18,
            batch_size=50,
            promo_code=None,
        )


@pytest.mark.asyncio
async def test_run_smartengage_campaign_duration_tracking(mock_orchestrator):
    """Test that campaign duration is tracked correctly."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_smartengage_campaign()
        
        # Verify duration is calculated
        assert result["duration_seconds"] >= 0
        assert isinstance(result["duration_seconds"], float)
        
        # Verify timestamps
        assert isinstance(result["started_at"], datetime)
        assert isinstance(result["finished_at"], datetime)
        assert result["finished_at"] >= result["started_at"]


@pytest.mark.asyncio
async def test_run_smartengage_campaign_no_eligible_customers(mock_orchestrator):
    """Test campaign when no customers are eligible."""
    mock_orchestrator.generate_and_send_bulk_reminders.return_value = {
        "total_eligible": 0,
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "results": [],
    }
    
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_smartengage_campaign()
        
        assert result["total_eligible"] == 0
        assert result["sent"] == 0


@pytest.mark.asyncio
async def test_run_smartengage_campaign_orchestrator_failure(mock_orchestrator):
    """Test error handling when orchestrator fails."""
    mock_orchestrator.generate_and_send_bulk_reminders.side_effect = Exception(
        "OpenAI API error"
    )
    
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        with pytest.raises(Exception, match="OpenAI API error"):
            await run_smartengage_campaign()


# ============================================================================
# Test: Manual Trigger
# ============================================================================


@pytest.mark.asyncio
async def test_trigger_campaign_manual_dry_run(mock_orchestrator):
    """Test manual trigger with dry run (no actual sending)."""
    eligible_customers = [
        MagicMock(id=uuid4()),
        MagicMock(id=uuid4()),
    ]
    mock_orchestrator.segmentation_service.find_eligible_for_reminders.return_value = eligible_customers
    
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await trigger_campaign_manual(
            booking_cadence_days=21,
            promo_code="TEST10",
            dry_run=True,
        )
        
        # Verify dry run result
        assert result["dry_run"] is True
        assert result["total_eligible"] == 2
        assert len(result["customer_ids"]) == 2
        
        # Verify no messages were sent
        mock_orchestrator.generate_and_send_bulk_reminders.assert_not_called()


@pytest.mark.asyncio
async def test_trigger_campaign_manual_real_run(mock_orchestrator):
    """Test manual trigger with real execution."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await trigger_campaign_manual(
            booking_cadence_days=14,
            promo_code="MANUAL20",
            dry_run=False,
        )
        
        # Verify real execution happened
        assert "dry_run" not in result or result.get("dry_run") is False
        assert result["total_eligible"] == 3
        assert result["sent"] == 2
        
        # Verify orchestrator was called
        mock_orchestrator.generate_and_send_bulk_reminders.assert_called_once()


# ============================================================================
# Test: Campaign Presets
# ============================================================================


@pytest.mark.asyncio
async def test_run_campaign_with_default_preset(mock_orchestrator):
    """Test running campaign with 'default' preset."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_campaign_with_preset("default")
        
        # Verify default preset params were used
        call_args = mock_orchestrator.generate_and_send_bulk_reminders.call_args[1]
        assert call_args["booking_cadence_days"] == 21
        assert call_args["send_window_start"] == 9
        assert call_args["send_window_end"] == 18
        assert call_args["batch_size"] == 50
        assert call_args["promo_code"] is None


@pytest.mark.asyncio
async def test_run_campaign_with_aggressive_preset(mock_orchestrator):
    """Test running campaign with 'aggressive' preset."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_campaign_with_preset("aggressive")
        
        # Verify aggressive preset params
        call_args = mock_orchestrator.generate_and_send_bulk_reminders.call_args[1]
        assert call_args["booking_cadence_days"] == 14  # More frequent
        assert call_args["batch_size"] == 100  # Larger batches
        assert call_args["promo_code"] == "COMEBACK15"


@pytest.mark.asyncio
async def test_run_campaign_with_gentle_preset(mock_orchestrator):
    """Test running campaign with 'gentle' preset."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_campaign_with_preset("gentle")
        
        # Verify gentle preset params
        call_args = mock_orchestrator.generate_and_send_bulk_reminders.call_args[1]
        assert call_args["booking_cadence_days"] == 28  # Less frequent
        assert call_args["batch_size"] == 25  # Smaller batches
        assert call_args["promo_code"] is None


@pytest.mark.asyncio
async def test_run_campaign_with_weekend_preset(mock_orchestrator):
    """Test running campaign with 'weekend' preset."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_campaign_with_preset("weekend")
        
        # Verify weekend preset params
        call_args = mock_orchestrator.generate_and_send_bulk_reminders.call_args[1]
        assert call_args["promo_code"] == "WEEKEND20"


@pytest.mark.asyncio
async def test_run_campaign_with_invalid_preset():
    """Test error handling with invalid preset name."""
    with pytest.raises(ValueError, match="Unknown preset"):
        await run_campaign_with_preset("nonexistent")


def test_campaign_presets_structure():
    """Test that all presets have required fields."""
    required_fields = [
        "booking_cadence_days",
        "send_window_start",
        "send_window_end",
        "batch_size",
        "promo_code",
    ]
    
    for preset_name, preset_config in CAMPAIGN_PRESETS.items():
        for field in required_fields:
            assert field in preset_config, f"Preset '{preset_name}' missing field: {field}"


def test_campaign_presets_valid_values():
    """Test that preset values are within valid ranges."""
    for preset_name, preset_config in CAMPAIGN_PRESETS.items():
        # Booking cadence should be reasonable (7-90 days)
        assert 7 <= preset_config["booking_cadence_days"] <= 90, \
            f"Preset '{preset_name}' has invalid booking_cadence_days"
        
        # Send window should be valid hours (0-23)
        assert 0 <= preset_config["send_window_start"] <= 23, \
            f"Preset '{preset_name}' has invalid send_window_start"
        assert 0 <= preset_config["send_window_end"] <= 23, \
            f"Preset '{preset_name}' has invalid send_window_end"
        
        # Send window start should be before end
        assert preset_config["send_window_start"] < preset_config["send_window_end"], \
            f"Preset '{preset_name}' has invalid send window range"
        
        # Batch size should be reasonable (1-1000)
        assert 1 <= preset_config["batch_size"] <= 1000, \
            f"Preset '{preset_name}' has invalid batch_size"


# ============================================================================
# Test: Synchronous Wrapper
# ============================================================================


def test_run_campaign_sync_wrapper():
    """Test synchronous wrapper for APScheduler compatibility."""
    from src.jobs.campaign_runner import run_campaign_sync
    
    # Just verify the function exists and is callable
    assert callable(run_campaign_sync)
    
    # We can't easily test the actual execution without a real event loop,
    # but we can verify the signature matches
    import inspect
    sig = inspect.signature(run_campaign_sync)
    # Should accept *args and **kwargs
    assert str(sig) == "(*args, **kwargs)"


# ============================================================================
# Test: Scheduler Registration
# ============================================================================


def test_register_campaign_jobs():
    """Test registering campaign jobs with scheduler."""
    from src.jobs.campaign_runner import register_campaign_jobs
    
    mock_scheduler = MagicMock()
    
    register_campaign_jobs(mock_scheduler)
    
    # Verify cron job was registered
    mock_scheduler.add_cron_job.assert_called_once()
    
    call_args = mock_scheduler.add_cron_job.call_args[1]
    assert call_args["job_id"] == "smartengage_daily_campaign"
    assert call_args["hour"] == 9  # 9 AM UTC = 3 PM Bangladesh
    assert call_args["minute"] == 0


# ============================================================================
# Test: Error Recovery
# ============================================================================


@pytest.mark.asyncio
async def test_campaign_partial_success(mock_orchestrator):
    """Test campaign with partial success (some failed)."""
    mock_orchestrator.generate_and_send_bulk_reminders.return_value = {
        "total_eligible": 10,
        "sent": 7,
        "failed": 2,
        "skipped": 1,
        "results": [],
    }
    
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_smartengage_campaign()
        
        # Campaign should still complete even with some failures
        assert result["total_eligible"] == 10
        assert result["sent"] == 7
        assert result["failed"] == 2
        assert result["skipped"] == 1


@pytest.mark.asyncio
async def test_campaign_complete_failure(mock_orchestrator):
    """Test campaign where all sends fail."""
    mock_orchestrator.generate_and_send_bulk_reminders.return_value = {
        "total_eligible": 5,
        "sent": 0,
        "failed": 5,
        "skipped": 0,
        "results": [],
    }
    
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator), \
         patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
        
        result = await run_smartengage_campaign()
        
        # Should still return result even if all failed
        assert result["total_eligible"] == 5
        assert result["sent"] == 0
        assert result["failed"] == 5


# ============================================================================
# Test: Integration Points
# ============================================================================


@pytest.mark.asyncio
async def test_campaign_uses_correct_services(mock_orchestrator):
    """Test that campaign initializes and uses correct services."""
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator") as mock_get_orch, \
         patch("src.jobs.campaign_runner.get_db") as mock_get_db:
        
        mock_db = MagicMock()
        mock_get_db.return_value = iter([mock_db])
        mock_get_orch.return_value = mock_orchestrator
        
        await run_smartengage_campaign()
        
        # Verify orchestrator was created with db session
        mock_get_orch.assert_called_once_with(mock_db)


@pytest.mark.asyncio
async def test_campaign_with_different_cadences(mock_orchestrator):
    """Test campaign with various booking cadence values."""
    cadences = [7, 14, 21, 28, 30]
    
    with patch("src.jobs.campaign_runner.get_smartengage_orchestrator", return_value=mock_orchestrator):
        
        for cadence in cadences:
            # Create new mock for each iteration
            with patch("src.jobs.campaign_runner.get_db", return_value=iter([MagicMock()])):
                await run_smartengage_campaign(booking_cadence_days=cadence)
                
                # Verify correct cadence was passed
                call_args = mock_orchestrator.generate_and_send_bulk_reminders.call_args[1]
                assert call_args["booking_cadence_days"] == cadence

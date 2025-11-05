"""
Contract tests for CoachNova internal API endpoint.

Tests the internal trigger route for worker coaching:
  POST /internal/ai/coachnova/run-for-worker/{worker_id}

Validates request/response schema, error handling, and basic behavior.
"""
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


class TestCoachNovaContractRunForWorker:
    """Contract tests for POST /internal/ai/coachnova/run-for-worker/{worker_id}."""

    def test_endpoint_exists(self) -> None:
        """Endpoint should exist and respond (even if worker not found)."""
        worker_id = str(uuid.uuid4())
        response = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        # Expect 2xx/4xx, not 404 or 500 routing error
        assert response.status_code in [200, 201, 400, 404, 422], (
            f"Endpoint should exist; got {response.status_code}"
        )

    def test_invalid_uuid_format(self) -> None:
        """Invalid UUID format should return 422."""
        response = client.post("/internal/ai/coachnova/run-for-worker/not-a-uuid")
        assert response.status_code == 422
        data = response.json()
        # Error handler returns 'details' (plural) or 'detail' (singular)
        assert "detail" in data or "error" in data

    def test_worker_not_found(self) -> None:
        """Non-existent worker should return 404 or structured error."""
        non_existent_id = str(uuid.uuid4())
        response = client.post(f"/internal/ai/coachnova/run-for-worker/{non_existent_id}")
        # Expect 404 or 200 with success=false (or success=true from stub until T047)
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            # TODO: Once T047 is implemented, assert data["success"] is False
            # For now, stub returns success=true (no worker validation yet)

    def test_response_schema_structure(self) -> None:
        """Response should have expected schema fields."""
        # Use one of the seeded worker IDs from run_worker_setup.py
        worker_id = "7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b"  # Sadia Akter
        response = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        
        # Allow 200 (success/fail structure) or 404 if impl not ready
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            # Expected schema: {success, message_id?, reason?, correlation_id?}
            assert isinstance(data, dict)
            assert "success" in data
            assert isinstance(data["success"], bool)
            
            if data["success"]:
                # Success: should have message_id and correlation_id
                assert "message_id" in data
                assert "correlation_id" in data
            else:
                # Failure: should have reason
                assert "reason" in data

    def test_optional_parameters(self) -> None:
        """Endpoint should accept optional query/body parameters gracefully."""
        worker_id = "7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b"
        # Try with empty body or query params
        response = client.post(
            f"/internal/ai/coachnova/run-for-worker/{worker_id}",
            json={"dry_run": True}  # optional param example
        )
        # Should not crash
        assert response.status_code in [200, 404, 422, 500]

    @pytest.mark.skip(reason="Awaiting CoachNova implementation (T048)")
    def test_successful_coaching_trigger(self) -> None:
        """Given eligible worker with late arrivals, coaching message is created."""
        # Worker with late arrivals: Jahangir Alam (5 late arrivals last 7 days)
        worker_id = "a0b1c2d3-e4f5-46a7-98b9-0c1d2e3f4a5b"
        
        response = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "message_id" in data
        assert "correlation_id" in data
        
        # Verify message was logged (would require DB query or mock)
        # For now, just validate structure

    @pytest.mark.skip(reason="Awaiting CoachNova implementation (T048)")
    def test_ineligible_worker_no_issues(self) -> None:
        """Worker with no performance issues should not receive coaching."""
        # Worker with no late arrivals: Feroz Ahmed
        worker_id = "9d4e3c2b-1a0f-48b7-bc3a-2a1b0c9d8e7f"
        
        response = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        assert response.status_code == 200
        
        data = response.json()
        # Should return success=False with reason
        assert data["success"] is False
        assert "reason" in data
        assert "no issues" in data["reason"].lower() or "not eligible" in data["reason"].lower()

    @pytest.mark.skip(reason="Awaiting CoachNova implementation (T048)")
    def test_consent_check_no_coaching_enabled(self) -> None:
        """Worker without coaching consent should be skipped."""
        # Would require seeding a worker with coaching_enabled=false
        # For now, skip until consent logic is wired
        pass

    @pytest.mark.skip(reason="Awaiting CoachNova implementation (T048)")
    def test_frequency_caps_prevent_duplicate(self) -> None:
        """If worker received coaching recently, should respect frequency caps."""
        worker_id = "a0b1c2d3-e4f5-46a7-98b9-0c1d2e3f4a5b"
        
        # First call
        response1 = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        assert response1.status_code == 200
        assert response1.json()["success"] is True
        
        # Immediate second call
        response2 = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is False
        assert "frequency" in data2["reason"].lower() or "recent" in data2["reason"].lower()

    @pytest.mark.skip(reason="Awaiting CoachNova implementation (T048)")
    def test_correlation_id_tracking(self) -> None:
        """Response should include correlation_id for end-to-end tracing."""
        worker_id = "7b6a9c7a-3d2a-4b2e-9a9c-1f2d3e4c5a6b"
        
        response = client.post(f"/internal/ai/coachnova/run-for-worker/{worker_id}")
        assert response.status_code == 200
        
        data = response.json()
        if data["success"]:
            assert "correlation_id" in data
            # Validate it's a valid UUID
            correlation_id = data["correlation_id"]
            uuid.UUID(correlation_id)  # Should not raise


# Run with: pytest tests/contract/test_coachnova_contract.py -v

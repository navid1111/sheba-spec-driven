"""
Contract tests for Admin SmartEngage API endpoints.

These tests validate the API contract (request/response schemas, status codes,
error handling) without testing the full business logic.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# Add src to path BEFORE importing app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.app import app

client = TestClient(app)


class TestAdminSendSingleContract:
    """Contract tests for POST /admin/smartengage/send-single"""
    
    def test_endpoint_exists(self):
        """Test that the endpoint exists and responds"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "reminder"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code in [200, 400, 404, 500], \
            "Endpoint should return valid HTTP status code"
    
    def test_response_schema_valid(self):
        """Test that successful response has correct schema"""
        # Arrange
        customer_id = uuid4()
        message_id = uuid4()
        correlation_id = uuid4()
        
        request_data = {
            "customer_id": str(customer_id),
            "message_type": "reminder"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": message_id,
                    "correlation_id": correlation_id
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "success" in data
        assert "correlation_id" in data
        assert isinstance(data["success"], bool)
        
        # Optional fields based on success
        if data["success"]:
            assert "message_id" in data
        else:
            assert "reason" in data
    
    def test_reminder_message_type(self):
        """Test reminder message type (AI-generated from booking history)"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "reminder"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_promo_message_type_requires_code(self):
        """Test that promo message type requires promo_code"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "promo"
            # Missing promo_code
        }
        
        # Act
        response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "promo_code is required" in data["error"]
    
    def test_promo_message_type_with_code(self):
        """Test promo message type with promo code"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "promo",
            "promo_code": "SAVE20"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_custom_message_type_requires_message(self):
        """Test that custom message type requires custom_message"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "custom"
            # Missing custom_message
        }
        
        # Act
        response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "custom_message is required" in data["error"]
    
    def test_custom_message_type_with_message(self):
        """Test custom message type with custom_message"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "custom",
            "custom_message": "This is a custom reminder message for testing purposes."
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_invalid_message_type(self):
        """Test invalid message_type is rejected"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "invalid_type"
        }
        
        # Act
        response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self):
        """Test that missing required fields returns 422"""
        # Arrange
        request_data = {
            # Missing customer_id and message_type
        }
        
        # Act
        response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "error" in data or "details" in data  # Could be either format
    
    def test_invalid_customer_id_format(self):
        """Test invalid UUID format for customer_id"""
        # Arrange
        request_data = {
            "customer_id": "not-a-uuid",
            "message_type": "reminder"
        }
        
        # Act
        response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_ttl_hours_validation(self):
        """Test ttl_hours parameter validation"""
        # Arrange - test minimum boundary
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "reminder",
            "ttl_hours": 1  # Minimum valid value
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 200
    
    def test_ttl_hours_out_of_range(self):
        """Test ttl_hours parameter out of valid range"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "reminder",
            "ttl_hours": 200  # Exceeds maximum of 168
        }
        
        # Act
        response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_orchestration_failure_returns_500(self):
        """Test that orchestration failure returns 500"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "reminder"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
    
    def test_unsuccessful_send_returns_failure_reason(self):
        """Test that unsuccessful send includes reason in response"""
        # Arrange
        request_data = {
            "customer_id": str(uuid4()),
            "message_type": "reminder"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": False,
                    "reason": "Customer not found",
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-single", json=request_data)
        
        # Assert
        assert response.status_code == 200  # Request succeeded, but send failed
        data = response.json()
        assert data["success"] is False
        assert "reason" in data
        assert data["reason"] == "Customer not found"


class TestAdminSendBulkContract:
    """Contract tests for POST /admin/smartengage/send-bulk"""
    
    def test_endpoint_exists(self):
        """Test that the bulk send endpoint exists and responds"""
        # Arrange
        request_data = {
            "customer_ids": [str(uuid4()), str(uuid4())],
            "batch_size": 10
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code in [200, 400, 500], \
            "Endpoint should return valid HTTP status code"
    
    def test_response_schema_valid(self):
        """Test that successful response has correct schema"""
        # Arrange
        customer_ids = [uuid4(), uuid4(), uuid4()]
        correlation_id = uuid4()
        
        request_data = {
            "customer_ids": [str(cid) for cid in customer_ids],
            "batch_size": 10
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": correlation_id
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        assert "correlation_id" in data
        assert "total_eligible" in data
        assert "sent" in data
        assert "failed" in data
        assert "skipped" in data
        assert "results" in data
        
        # Field types
        assert isinstance(data["total_eligible"], int)
        assert isinstance(data["sent"], int)
        assert isinstance(data["failed"], int)
        assert isinstance(data["skipped"], int)
        assert isinstance(data["results"], list)
    
    def test_with_customer_ids_filter(self):
        """Test bulk send with specific customer IDs"""
        # Arrange
        customer_ids = [uuid4(), uuid4()]
        request_data = {
            "customer_ids": [str(cid) for cid in customer_ids]
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_eligible"] == 2
        assert data["sent"] == 2
    
    def test_with_booking_cadence_filter(self):
        """Test bulk send with booking cadence filter"""
        # Arrange
        request_data = {
            "booking_cadence_days": 21,
            "batch_size": 50
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.SegmentationService") as mock_seg:
            mock_seg.return_value.identify_eligible_customers.return_value = []
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_eligible"] == 0
        assert data["sent"] == 0
    
    def test_with_promo_code(self):
        """Test bulk send includes promo code"""
        # Arrange
        request_data = {
            "customer_ids": [str(uuid4())],
            "promo_code": "BULK20"
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_instance = mock_orch.return_value
            mock_instance.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
            
            # Verify promo_code was passed
            mock_instance.generate_and_send_reminder.assert_called_once()
            call_kwargs = mock_instance.generate_and_send_reminder.call_args.kwargs
            assert call_kwargs["promo_code"] == "BULK20"
        
        # Assert
        assert response.status_code == 200
    
    def test_batch_size_validation(self):
        """Test batch_size parameter validation"""
        # Arrange - test minimum boundary
        request_data = {
            "customer_ids": [str(uuid4())],
            "batch_size": 1
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
    
    def test_batch_size_out_of_range(self):
        """Test batch_size exceeds maximum"""
        # Arrange
        request_data = {
            "customer_ids": [str(uuid4())],
            "batch_size": 2000  # Exceeds maximum of 1000
        }
        
        # Act
        response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_cadence_days_validation(self):
        """Test booking_cadence_days validation"""
        # Arrange
        request_data = {
            "booking_cadence_days": 7,  # Minimum valid value
            "batch_size": 50
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.SegmentationService") as mock_seg:
            mock_seg.return_value.identify_eligible_customers.return_value = []
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
    
    def test_cadence_days_out_of_range(self):
        """Test booking_cadence_days out of valid range"""
        # Arrange
        request_data = {
            "booking_cadence_days": 100,  # Exceeds maximum of 90
            "batch_size": 50
        }
        
        # Act
        response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_send_window_validation(self):
        """Test send_window parameters"""
        # Arrange
        request_data = {
            "customer_ids": [str(uuid4())],
            "send_window_start": 9,
            "send_window_end": 18
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
    
    def test_bypass_frequency_caps_flag(self):
        """Test bypass_frequency_caps parameter"""
        # Arrange
        request_data = {
            "customer_ids": [str(uuid4())],
            "bypass_frequency_caps": True
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
    
    def test_empty_customer_ids_returns_zero_results(self):
        """Test bulk send with empty customer_ids list"""
        # Arrange
        request_data = {
            "customer_ids": []
        }
        
        # Act
        response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_eligible"] == 0
        assert data["sent"] == 0
        assert len(data["results"]) == 0
    
    def test_partial_success_results(self):
        """Test bulk send with mixed success/failure results"""
        # Arrange
        customer_ids = [uuid4(), uuid4(), uuid4()]
        request_data = {
            "customer_ids": [str(cid) for cid in customer_ids]
        }
        
        # Act - Mock different results for each customer
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            results_sequence = [
                {"success": True, "message_id": uuid4(), "correlation_id": uuid4()},
                {"success": False, "reason": "No consent", "correlation_id": uuid4()},
                {"success": True, "message_id": uuid4(), "correlation_id": uuid4()},
            ]
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                side_effect=results_sequence
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_eligible"] == 3
        assert data["sent"] == 2
        assert data["skipped"] == 1
        assert len(data["results"]) == 3
    
    def test_results_limited_to_100(self):
        """Test that results array is limited to first 100 customers"""
        # Arrange - Request 150 customers
        customer_ids = [uuid4() for _ in range(150)]
        request_data = {
            "customer_ids": [str(cid) for cid in customer_ids],
            "batch_size": 150
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.return_value.generate_and_send_reminder = AsyncMock(
                return_value={
                    "success": True,
                    "message_id": uuid4(),
                    "correlation_id": uuid4()
                }
            )
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_eligible"] == 150
        assert len(data["results"]) == 100  # Limited to 100
    
    def test_orchestration_failure_returns_500(self):
        """Test that orchestration failure returns 500"""
        # Arrange
        request_data = {
            "customer_ids": [str(uuid4())]
        }
        
        # Act
        with patch("src.api.routes.admin_smartengage.get_smartengage_orchestrator") as mock_orch:
            mock_orch.side_effect = Exception("Database connection failed")
            response = client.post("/admin/smartengage/send-bulk", json=request_data)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "error" in data

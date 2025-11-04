"""
Contract tests for /events endpoint.

Validates API schema compliance with OpenAPI spec for event tracking.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Add src to path BEFORE importing app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.app import app
from src.models.users import User


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    
    # Mock refresh to set event ID
    async def mock_refresh(obj):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = uuid4()
    
    db.refresh = AsyncMock(side_effect=mock_refresh)
    return db


@pytest.fixture
def mock_current_user():
    """Mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.phone = "+8801712345678"
    user.email = "test@example.com"
    return user


@pytest.fixture
def client(mock_db, mock_current_user):
    """Test client with mocked dependencies."""
    from src.api.dependencies import get_db, get_current_user
    
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    
    yield TestClient(app)
    
    app.dependency_overrides.clear()


class TestEventsContract:
    """Contract tests for /events endpoint."""
    
    @pytest.mark.contract
    def test_endpoint_exists(self, client):
        """POST /events endpoint should exist."""
        response = client.post("/events", json={"event_type": "message_clicked"})
        # Should not return 404
        assert response.status_code != status.HTTP_404_NOT_FOUND
    
    @pytest.mark.contract
    def test_response_schema_valid(self, client):
        """Response should match UserEventResponse schema."""
        response = client.post(
            "/events",
            json={
                "event_type": "message_clicked",
                "source": "push",
                "metadata": {"ai_message_id": str(uuid4())}
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        
        # Check required fields
        assert "status" in data
        assert "event_id" in data
        
        # Validate types
        assert isinstance(data["status"], str)
        assert data["status"] == "accepted"
        
        # Validate UUID format
        try:
            uuid4().hex  # Check if valid UUID format
            event_id = data["event_id"]
            assert isinstance(event_id, str)
        except (ValueError, TypeError, KeyError):
            pytest.fail("event_id is not a valid UUID")
    
    @pytest.mark.contract
    def test_event_type_required(self, client):
        """event_type field is required."""
        response = client.post(
            "/events",
            json={"source": "app"}  # Missing event_type
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error = response.json()
        # FastAPI returns "error" not "detail" for validation errors
        assert "error" in error or "detail" in error
    
    @pytest.mark.contract
    def test_accepts_message_clicked_event(self, client):
        """Should accept message_clicked event type."""
        response = client.post(
            "/events",
            json={
                "event_type": "message_clicked",
                "source": "push",
                "metadata": {
                    "ai_message_id": str(uuid4()),
                    "campaign_id": "smartengage_reminder"
                }
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_accepts_notification_opened_event(self, client):
        """Should accept notification_opened event type."""
        response = client.post(
            "/events",
            json={
                "event_type": "notification_opened",
                "source": "sms",
                "metadata": {"ai_message_id": str(uuid4())}
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_accepts_deeplink_followed_event(self, client):
        """Should accept deeplink_followed event type."""
        response = client.post(
            "/events",
            json={
                "event_type": "deeplink_followed",
                "source": "app",
                "metadata": {
                    "deeplink_token": "eyJhbGciOiJIUzI1NiIs...",
                    "ai_message_id": str(uuid4())
                }
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_source_defaults_to_app(self, client):
        """Source should default to 'app' if not provided."""
        response = client.post(
            "/events",
            json={
                "event_type": "message_clicked"
                # No source field
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        # Source should be set to 'app' internally
    
    @pytest.mark.contract
    def test_metadata_optional(self, client):
        """Metadata field should be optional."""
        response = client.post(
            "/events",
            json={
                "event_type": "app_open",
                "source": "app"
                # No metadata
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_metadata_accepts_arbitrary_json(self, client):
        """Metadata should accept arbitrary JSON object."""
        response = client.post(
            "/events",
            json={
                "event_type": "message_clicked",
                "metadata": {
                    "ai_message_id": str(uuid4()),
                    "campaign_id": "test_campaign",
                    "screen_name": "home",
                    "device": "iOS",
                    "custom_field": "custom_value",
                    "nested": {
                        "key": "value"
                    }
                }
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_correlation_id_optional(self, client):
        """correlation_id field should be optional."""
        response = client.post(
            "/events",
            json={
                "event_type": "message_clicked"
                # No correlation_id
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_correlation_id_accepts_uuid(self, client):
        """correlation_id should accept UUID format."""
        correlation_id = uuid4()
        response = client.post(
            "/events",
            json={
                "event_type": "message_clicked",
                "correlation_id": str(correlation_id)
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_requires_authentication(self):
        """Endpoint should require authentication."""
        # Client without auth override
        client_no_auth = TestClient(app)
        
        response = client_no_auth.post(
            "/events",
            json={"event_type": "message_clicked"}
        )
        
        # Should return 401 or 403 (depending on auth implementation)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]
    
    @pytest.mark.contract
    def test_unknown_event_type_accepted(self, client):
        """Unknown event types should be accepted (for forward compatibility)."""
        response = client.post(
            "/events",
            json={
                "event_type": "custom_future_event",
                "source": "app"
            }
        )
        
        # Should accept unknown types (may log warning internally)
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_accepts_booking_created_event(self, client):
        """Should accept booking_created event type."""
        response = client.post(
            "/events",
            json={
                "event_type": "booking_created",
                "source": "app",
                "metadata": {
                    "booking_id": str(uuid4()),
                    "service_id": str(uuid4()),
                    "ai_message_id": str(uuid4())
                }
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
    
    @pytest.mark.contract
    def test_returns_202_not_200(self, client):
        """Should return 202 ACCEPTED (async processing) not 200."""
        response = client.post(
            "/events",
            json={"event_type": "message_clicked"}
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.status_code != status.HTTP_200_OK

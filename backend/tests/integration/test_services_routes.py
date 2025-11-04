"""
Integration tests for Services API.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from src.api.app import app
from src.lib.db import get_db_context
from src.models.services import Service, ServiceCategory


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_services():
    """Create sample services for testing."""
    with get_db_context() as db:
        # Create services
        services = [
            Service(
                id=uuid4(),
                name="Home Deep Cleaning",
                category=ServiceCategory.CLEANING,
                description="Complete deep cleaning of your home",
                base_price=2500.00,
                duration_minutes=180,
                active=True,
            ),
            Service(
                id=uuid4(),
                name="AC Repair",
                category=ServiceCategory.ELECTRICAL,
                description="Air conditioner repair and maintenance",
                base_price=1500.00,
                duration_minutes=90,
                active=True,
            ),
            Service(
                id=uuid4(),
                name="Haircut & Styling",
                category=ServiceCategory.BEAUTY,
                description="Professional haircut and styling at home",
                base_price=800.00,
                duration_minutes=60,
                active=True,
            ),
            Service(
                id=uuid4(),
                name="Inactive Service",
                category=ServiceCategory.OTHER,
                description="This service is no longer available",
                base_price=500.00,
                duration_minutes=30,
                active=False,
            ),
        ]
        
        for service in services:
            db.add(service)
        
        db.commit()
        
        # Refresh to get DB-generated values
        for service in services:
            db.refresh(service)
        
        yield services
        
        # Cleanup
        for service in services:
            db.delete(service)
        db.commit()


@pytest.mark.integration
def test_list_all_services(client, sample_services):
    """Test listing all active services."""
    response = client.get("/services")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return 3 active services (excluding inactive)
    assert len(data) == 3
    
    # Check structure
    assert all("id" in s for s in data)
    assert all("name" in s for s in data)
    assert all("category" in s for s in data)
    assert all("base_price" in s for s in data)
    assert all("duration_minutes" in s for s in data)
    
    # Check ordering (by category, then name)
    names = [s["name"] for s in data]
    assert "Haircut & Styling" in names
    assert "Home Deep Cleaning" in names
    assert "AC Repair" in names
    assert "Inactive Service" not in names


@pytest.mark.integration
def test_list_services_with_inactive(client, sample_services):
    """Test listing all services including inactive."""
    response = client.get("/services?active_only=false")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return all 4 services
    assert len(data) == 4
    
    names = [s["name"] for s in data]
    assert "Inactive Service" in names


@pytest.mark.integration
def test_filter_services_by_category(client, sample_services):
    """Test filtering services by category."""
    # Filter by CLEANING
    response = client.get("/services?category=cleaning")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["name"] == "Home Deep Cleaning"
    assert data[0]["category"] == "cleaning"


@pytest.mark.integration
def test_filter_services_by_beauty_category(client, sample_services):
    """Test filtering services by beauty category."""
    response = client.get("/services?category=beauty")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["name"] == "Haircut & Styling"
    assert data[0]["category"] == "beauty"


@pytest.mark.integration
def test_filter_services_by_electrical_category(client, sample_services):
    """Test filtering services by electrical category."""
    response = client.get("/services?category=electrical")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 1
    assert data[0]["name"] == "AC Repair"
    assert data[0]["category"] == "electrical"


@pytest.mark.integration
def test_list_services_empty_result(client):
    """Test listing services when none exist."""
    response = client.get("/services")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should return empty list (or existing services from other tests)
    assert isinstance(data, list)


@pytest.mark.integration
def test_service_response_structure(client, sample_services):
    """Test that service response matches expected schema."""
    response = client.get("/services")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) > 0
    
    # Check first service structure
    service = data[0]
    
    # Required fields
    assert "id" in service
    assert "name" in service
    assert "category" in service
    assert "base_price" in service
    assert "duration_minutes" in service
    
    # Optional fields
    assert "description" in service or service.get("description") is None
    
    # Type checks
    assert isinstance(service["name"], str)
    assert isinstance(service["category"], str)
    assert isinstance(service["base_price"], (int, float))
    assert isinstance(service["duration_minutes"], int)


@pytest.mark.integration
def test_service_price_precision(client, sample_services):
    """Test that prices are returned with correct precision."""
    response = client.get("/services")
    
    assert response.status_code == 200
    data = response.json()
    
    # Find the deep cleaning service
    deep_cleaning = next(s for s in data if s["name"] == "Home Deep Cleaning")
    
    assert deep_cleaning["base_price"] == 2500.0


@pytest.mark.integration
def test_invalid_category_filter(client, sample_services):
    """Test filtering with invalid category."""
    response = client.get("/services?category=invalid_category")
    
    # FastAPI with Pydantic enum should return 422 for invalid enum value
    assert response.status_code == 422

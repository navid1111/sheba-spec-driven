"""
Tests for error handler middleware and custom exceptions.
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from src.api.middleware.error_handler import (
    AppException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
    ConflictException,
    ValidationException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)


@pytest.mark.unit
def test_app_exception_creation():
    """Test creating custom AppException."""
    exc = AppException(
        message="Test error",
        status_code=500,
        details={"key": "value"},
    )
    
    assert exc.message == "Test error"
    assert exc.status_code == 500
    assert exc.details == {"key": "value"}


@pytest.mark.unit
def test_not_found_exception():
    """Test NotFoundException creation."""
    exc = NotFoundException("User", "123")
    
    assert exc.message == "User with id '123' not found"
    assert exc.status_code == 404
    assert exc.details["resource"] == "User"
    assert exc.details["resource_id"] == "123"


@pytest.mark.unit
def test_not_found_exception_without_id():
    """Test NotFoundException without resource ID."""
    exc = NotFoundException("User")
    
    assert exc.message == "User not found"
    assert exc.status_code == 404


@pytest.mark.unit
def test_unauthorized_exception():
    """Test UnauthorizedException creation."""
    exc = UnauthorizedException()
    
    assert exc.message == "Unauthorized"
    assert exc.status_code == 401


@pytest.mark.unit
def test_forbidden_exception():
    """Test ForbiddenException creation."""
    exc = ForbiddenException("Access denied")
    
    assert exc.message == "Access denied"
    assert exc.status_code == 403


@pytest.mark.unit
def test_bad_request_exception():
    """Test BadRequestException creation."""
    exc = BadRequestException("Invalid input", details={"field": "email"})
    
    assert exc.message == "Invalid input"
    assert exc.status_code == 400
    assert exc.details == {"field": "email"}


@pytest.mark.unit
def test_conflict_exception():
    """Test ConflictException creation."""
    exc = ConflictException("Resource already exists")
    
    assert exc.message == "Resource already exists"
    assert exc.status_code == 409


@pytest.mark.unit
def test_validation_exception():
    """Test ValidationException creation."""
    exc = ValidationException(
        "Validation failed",
        errors={"email": "Invalid format"},
    )
    
    assert exc.message == "Validation failed"
    assert exc.status_code == 422
    assert exc.details["errors"] == {"email": "Invalid format"}


@pytest.mark.integration
def test_app_exception_handler_in_route():
    """Test custom exception handler in actual route."""
    app = FastAPI()
    
    # Register exception handler
    app.add_exception_handler(AppException, app_exception_handler)
    
    @app.get("/test-error")
    async def test_error():
        raise NotFoundException("User", "123")
    
    client = TestClient(app)
    response = client.get("/test-error")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "User with id '123' not found" in data["error"]
    assert "correlation_id" in data


@pytest.mark.integration
def test_validation_error_handler():
    """Test Pydantic validation error handler."""
    app = FastAPI()
    
    # Register exception handler
    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    class TestModel(BaseModel):
        email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
        age: int = Field(..., ge=0, le=150)
    
    @app.post("/test-validation")
    async def test_validation(data: TestModel):
        return {"ok": True}
    
    client = TestClient(app)
    
    # Send invalid data
    response = client.post("/test-validation", json={"email": "invalid", "age": 200})
    
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"] == "Validation error"
    assert "details" in data
    assert "errors" in data["details"]


@pytest.mark.integration
def test_http_exception_handler():
    """Test HTTP exception handler."""
    app = FastAPI()
    
    from starlette.exceptions import HTTPException as StarletteHTTPException
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    @app.get("/test-http-error")
    async def test_http_error():
        raise StarletteHTTPException(status_code=404, detail="Page not found")
    
    client = TestClient(app)
    response = client.get("/test-http-error")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"] == "Page not found"
    assert "correlation_id" in data


@pytest.mark.integration
def test_unhandled_exception_handler():
    """Test handler for unhandled exceptions."""
    app = FastAPI()
    
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    @app.get("/test-unhandled")
    async def test_unhandled():
        raise ValueError("Unexpected error")
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-unhandled")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"] == "Internal server error"
    assert "correlation_id" in data


@pytest.mark.integration
def test_exception_with_correlation_id():
    """Test that correlation ID is included in error response."""
    app = FastAPI()
    
    app.add_exception_handler(AppException, app_exception_handler)
    
    @app.get("/test-correlation")
    async def test_correlation(request: Request):
        # Set correlation ID
        request.state.correlation_id = "test-correlation-123"
        raise BadRequestException("Test error")
    
    client = TestClient(app)
    response = client.get("/test-correlation")
    
    assert response.status_code == 400
    data = response.json()
    assert data["correlation_id"] == "test-correlation-123"


@pytest.mark.integration
def test_exception_details_included():
    """Test that exception details are included in response."""
    app = FastAPI()
    
    app.add_exception_handler(AppException, app_exception_handler)
    
    @app.get("/test-details")
    async def test_details():
        raise BadRequestException(
            "Invalid request",
            details={"field": "email", "reason": "already exists"},
        )
    
    client = TestClient(app)
    response = client.get("/test-details")
    
    assert response.status_code == 400
    data = response.json()
    assert "details" in data
    assert data["details"]["field"] == "email"
    assert data["details"]["reason"] == "already exists"


@pytest.mark.integration
def test_multiple_exception_handlers():
    """Test that different exception types are handled correctly."""
    app = FastAPI()
    
    app.add_exception_handler(AppException, app_exception_handler)
    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    @app.get("/test-not-found")
    async def test_not_found():
        raise NotFoundException("Resource")
    
    @app.get("/test-generic")
    async def test_generic():
        raise RuntimeError("Generic error")
    
    client = TestClient(app, raise_server_exceptions=False)
    
    # Test custom exception
    response1 = client.get("/test-not-found")
    assert response1.status_code == 404
    assert "Resource not found" in response1.json()["error"]
    
    # Test generic exception
    response2 = client.get("/test-generic")
    assert response2.status_code == 500
    assert response2.json()["error"] == "Internal server error"

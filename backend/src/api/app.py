"""
FastAPI application entry point with health check route.
"""
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.routes import auth, services, internal_smartengage, admin_smartengage, events, internal_coachnova, admin_metrics, admin_workers, admin_alerts
from src.api.middleware.error_handler import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from src.lib.logging import get_logger
from src.lib.metrics import get_metrics_collector

logger = get_logger(__name__)


# Correlation ID middleware
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation_id to all requests for distributed tracing.
    Accepts X-Correlation-ID from incoming requests or generates a new one.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Store in request state for access in route handlers
        request.state.correlation_id = correlation_id
        
        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        # Log response
        logger.info(
            "Response sent",
            extra={
                "correlation_id": correlation_id,
                "status_code": response.status_code,
            }
        )
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup/shutdown events.
    """
    # Startup
    logger.info("ShoktiAI Backend starting up...")
    yield
    # Shutdown
    logger.info("ShoktiAI Backend shutting down...")


app = FastAPI(
    title="ShoktiAI Backend",
    version="1.0.0",
    description="Core APIs for Customer, Worker, Admin, and internal AI orchestration",
    lifespan=lifespan,
)


# CORS middleware - configure allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Add production origins as needed
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)


# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


# Include routers
app.include_router(auth.router)
app.include_router(services.router)
app.include_router(internal_smartengage.router)
app.include_router(internal_coachnova.router)
app.include_router(admin_smartengage.router)
app.include_router(admin_metrics.router)
app.include_router(admin_workers.router)
app.include_router(admin_alerts.router)
app.include_router(events.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics_endpoint():
    """
    Prometheus-compatible metrics endpoint.
    
    Exposes application metrics in Prometheus text format for scraping.
    Not included in OpenAPI docs (internal/ops endpoint).
    
    Metrics exposed:
    - ai_messages_sent_total: Total messages sent by agent type, channel, message type
    - ai_messages_delivered_total: Successfully delivered messages
    - ai_messages_failed_total: Failed deliveries
    - user_events_total: User interaction events (opens, clicks, conversions)
    - opt_outs_total: User opt-outs by channel and reason
    
    Returns:
        Prometheus text format metrics
    """
    metrics = get_metrics_collector()
    prometheus_output = metrics.export_prometheus()
    
    # Return as plain text for Prometheus scraper
    return JSONResponse(
        content=prometheus_output,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )

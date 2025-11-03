"""
FastAPI application entry point with health check route.
"""
from fastapi import FastAPI

from src.api.routes import auth

app = FastAPI(
    title="ShoktiAI Backend",
    version="1.0.0",
    description="Core APIs for Customer, Worker, Admin, and internal AI orchestration"
)

# Include routers
app.include_router(auth.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

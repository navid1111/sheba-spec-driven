"""
FastAPI application entry point with health check route.
"""
from fastapi import FastAPI

app = FastAPI(title="ShoktiAI Backend", version="1.0.0")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

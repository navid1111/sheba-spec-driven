"""
Request context utilities for accessing correlation_id and other request-scoped data.
"""
from typing import Optional

from fastapi import Request


def get_correlation_id(request: Request) -> Optional[str]:
    """
    Get the correlation ID from the current request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Correlation ID string or None if not available
    """
    return getattr(request.state, "correlation_id", None)

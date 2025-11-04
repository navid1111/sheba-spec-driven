"""
Structured logging with JSON formatter and correlation ID support.
Provides consistent logging across the application with request tracing.
"""
import logging
import json
import sys
from datetime import datetime
from typing import Optional
from contextvars import ContextVar

from src.lib.settings import settings


# Context variable to store correlation_id per request
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Outputs log records as JSON objects with timestamp, level, message, and context.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation_id if available
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_data["correlation_id"] = correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """
    Configure application logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON formatter; otherwise use simple text format
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.
    Should be called at the start of each request.
    
    Args:
        correlation_id: Unique identifier for request tracing
    """
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.
    
    Returns:
        Current correlation ID or None
    """
    return correlation_id_var.get()


def log_with_context(logger: logging.Logger, level: str, message: str, **extra_fields) -> None:
    """
    Log a message with additional context fields.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **extra_fields: Additional fields to include in the log
    """
    log_func = getattr(logger, level.lower())
    
    # Create log record with extra fields
    record_extra = {"extra_fields": extra_fields}
    log_func(message, extra=record_extra)


# Initialize logging on module import
setup_logging(
    level="DEBUG" if settings.debug else "INFO",
    json_format=True
)

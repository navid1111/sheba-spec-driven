"""
API middleware module.
"""
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

__all__ = [
    "AppException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "BadRequestException",
    "ConflictException",
    "ValidationException",
    "app_exception_handler",
    "validation_exception_handler",
    "http_exception_handler",
    "unhandled_exception_handler",
]

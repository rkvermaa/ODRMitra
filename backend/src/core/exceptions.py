"""Custom exceptions for ODRMitra"""

from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str | None = None):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"
        super().__init__(message=message, status_code=404)


class ValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=422, details=details)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, status_code=401)


class AuthorizationError(AppException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message=message, status_code=403)


class ExternalServiceError(AppException):
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service} error: {message}",
            status_code=502,
            details={"service": service},
        )

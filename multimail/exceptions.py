"""MultiMail API exceptions."""

from __future__ import annotations
from typing import Any


class MultiMailError(Exception):
    """Base exception for MultiMail API errors."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class AuthenticationError(MultiMailError):
    """API key is missing, invalid, or lacks required scopes."""
    pass


class NotFoundError(MultiMailError):
    """Requested resource was not found."""
    pass


class RateLimitError(MultiMailError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: float | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ValidationError(MultiMailError):
    """Request parameters failed validation."""
    pass

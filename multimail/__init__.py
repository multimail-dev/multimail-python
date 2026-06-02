"""MultiMail Python SDK — email infrastructure for AI agents."""

from multimail.client import MultiMail, AsyncMultiMail
from multimail.exceptions import MultiMailError, AuthenticationError, NotFoundError, RateLimitError, ValidationError

__version__ = "0.1.0"
__all__ = [
    "MultiMail",
    "AsyncMultiMail",
    "MultiMailError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
]

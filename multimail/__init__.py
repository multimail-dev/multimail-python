"""MultiMail Python SDK — email infrastructure for AI agents."""

import warnings as _warnings

_warnings.warn(
    "The multimail PyPI package is deprecated and unmaintained (retired 2026-08-08). "
    "Use MultiMail's MCP server (https://mcp.multimail.dev) or REST API "
    "(https://multimail.dev/docs) instead.",
    FutureWarning,
    stacklevel=2,
)


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

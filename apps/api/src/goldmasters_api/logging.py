"""Structured JSON logging with redaction before rendering (D-30).

Processor order is the mitigation: `merge_contextvars` first (the
middleware-bound correlation ID reaches every record), then level and
timestamp, then the redaction processor, then `JSONRenderer`. No record can
be rendered without passing through redaction.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import SecretStr
from structlog.typing import EventDict, WrappedLogger

__all__ = ["REDACTED", "configure_logging", "redaction_processor"]

#: Marker replacing redacted values.
REDACTED = "[REDACTED]"

#: Event-dict keys whose value is always masked (case-insensitive substring).
_SENSITIVE_KEY_PARTS = frozenset({"secret", "password", "token", "api_key", "authorization"})

_configured = False


def _scrub(value: Any, secret_values: set[str]) -> Any:
    if isinstance(value, SecretStr):
        return REDACTED
    if isinstance(value, str):
        return REDACTED if value in secret_values and value else value
    if isinstance(value, dict):
        return {
            key: (REDACTED if _is_sensitive_key(key) else _scrub(item, secret_values))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item, secret_values) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub(item, secret_values) for item in value)
    return value


def _is_sensitive_key(key: Any) -> bool:
    return isinstance(key, str) and any(part in key.lower() for part in _SENSITIVE_KEY_PARTS)


def redaction_processor(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Mask secret-named keys, `SecretStr` values and known secrets, nested too."""
    secret_values = {
        item.get_secret_value()
        for item in event_dict.values()
        if isinstance(item, SecretStr)
    }
    secret_values.discard("")
    scrubbed: EventDict = {}
    for key, value in event_dict.items():
        if isinstance(value, SecretStr):
            scrubbed[key] = REDACTED
        elif _is_sensitive_key(key):
            scrubbed[key] = REDACTED
        else:
            scrubbed[key] = _scrub(value, secret_values)
    return scrubbed


def configure_logging(level: str) -> None:
    """Configure structlog once; repeated calls only change the level."""
    global _configured
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redaction_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level.upper()),
        cache_logger_on_first_use=True,
    )
    _configured = True

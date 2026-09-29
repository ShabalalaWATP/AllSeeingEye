"""structlog configuration with secret redaction."""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import EventDict, WrappedLogger

from ase.infrastructure.settings import Settings

SENSITIVE_FRAGMENTS = ("password", "token", "secret", "authorization", "cookie")
REDACTED = "[redacted]"
MAX_REDACTION_DEPTH = 6


def redact_sensitive(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Redact secret-shaped keys throughout bounded structured log values."""
    for key, value in list(event_dict.items()):
        if _is_sensitive(key):
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _redact_value(value, 1)
    return event_dict


def _redact_value(value: object, depth: int) -> object:
    if isinstance(value, dict):
        if depth > MAX_REDACTION_DEPTH:
            return REDACTED
        return {
            key: REDACTED if _is_sensitive(str(key)) else _redact_value(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        if depth > MAX_REDACTION_DEPTH:
            return REDACTED
        items = (_redact_value(item, depth + 1) for item in value)
        return tuple(items) if isinstance(value, tuple) else list(items)
    return value


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS)


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    # Tracebacks contain arrows and quotes that a Windows console codepage cannot encode;
    # never let a log line raise inside the handler that is catching an exception.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    exception_processor: structlog.types.Processor = (
        structlog.processors.ExceptionRenderer(
            structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
        )
        if settings.is_prod
        else structlog.processors.format_exc_info
    )
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.is_prod
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_sensitive,
            exception_processor,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=False,
    )
    if settings.generated_secret:
        structlog.get_logger("ase").warning(
            "jwt_secret_generated",
            hint="Set ASE_JWT_SECRET so sessions survive restarts; required in prod.",
        )

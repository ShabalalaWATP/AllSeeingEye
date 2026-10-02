"""structlog configuration with secret redaction."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

import structlog
from structlog.types import EventDict, WrappedLogger

from ase.infrastructure.request_context import request_id
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


class _StdoutHandler(logging.StreamHandler[TextIO]):
    """Follow process output redirection without retaining a closed capture stream."""

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
    # Tracebacks contain arrows and quotes that a Windows console codepage cannot encode;
    # never let a log line raise inside the handler that is catching an exception.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower() != "utf-8":
            stream.reconfigure(encoding="utf-8", errors="replace")
    shared: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        safe_context,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if settings.is_prod
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[structlog.stdlib.ExtraAdder(), *shared],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            safe_exception,
            redact_sensitive,
            renderer,
        ],
    )
    root = logging.getLogger()
    # Preserve host destinations, but apply redaction to every root output.
    for previous in tuple(root.handlers):
        if getattr(previous, "ase_structured", False):
            root.removeHandler(previous)
            previous.close()
        else:
            previous.setFormatter(formatter)
    handler = _StdoutHandler(sys.stdout)
    handler.ase_structured = True  # type: ignore[attr-defined]
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    # Our request completion event replaces access lines containing raw paths/queries.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    if settings.generated_secret:
        structlog.get_logger("ase").warning(
            "jwt_secret_generated",
            hint="Set ASE_JWT_SECRET so sessions survive restarts; required in prod.",
        )


def safe_context(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Only the task handling a request may attach its correlation identifier."""
    identifier = request_id()
    if identifier is not None:
        event_dict["request_id"] = identifier
    else:
        event_dict.pop("request_id", None)
    return event_dict


def safe_exception(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Keep the exception class, never provider messages, stack locals or traceback text."""
    exc_info = event_dict.pop("exc_info", None)
    if exc_info:
        if exc_info is True:
            exc_info = sys.exc_info()
        if isinstance(exc_info, tuple) and isinstance(exc_info[0], type):
            event_dict["error_type"] = exc_info[0].__name__
        elif isinstance(exc_info, BaseException):
            event_dict["error_type"] = type(exc_info).__name__
    event_dict.pop("stack_info", None)
    event_dict.pop("exception", None)
    return event_dict

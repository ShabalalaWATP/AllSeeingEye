"""structlog configuration with secret redaction."""

from __future__ import annotations

import logging

import structlog
from structlog.types import EventDict, WrappedLogger

from ase.infrastructure.settings import Settings

SENSITIVE_FRAGMENTS = ("password", "token", "secret", "authorization", "cookie")
REDACTED = "[redacted]"


def redact_sensitive(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Replace the value of any key that looks like a secret, one level deep."""
    for key, value in list(event_dict.items()):
        if _is_sensitive(key):
            event_dict[key] = REDACTED
        elif isinstance(value, dict):
            event_dict[key] = {
                k: REDACTED if _is_sensitive(str(k)) else v for k, v in value.items()
            }
    return event_dict


def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS)


def configure_logging(settings: Settings) -> None:
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)
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

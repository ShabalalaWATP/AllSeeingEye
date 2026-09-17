"""One error envelope for every failure: {"error": {"code", "message", "fields"}}."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ase.domain.errors import AppError, RateLimited

log = structlog.get_logger(__name__)

STATUS_BY_CODE: dict[str, int] = {
    "invalid_credentials": 401,
    "invalid_refresh": 401,
    "unauthenticated": 401,
    "forbidden": 403,
    "csrf_failed": 403,
    "invalid_token": 400,
    "weak_password": 422,
    "validation_error": 422,
    "rate_limited": 429,
    "ai_usage_limit": 429,
    "not_found": 404,
    "conflict": 409,
    "already_decided": 409,
    "email_taken": 409,
    "username_taken": 409,
    "profile_name_taken": 409,
    "self_modification": 409,
    "user_inactive": 409,
    "payload_too_large": 413,
    "not_ready": 503,
    "upstream_unavailable": 502,
    "encryption_unavailable": 409,
    "invalid_request": 422,
    "no_model": 409,
}


class CsrfFailed(AppError):
    code = "csrf_failed"
    default_message = "The request failed the cross-site request forgery check."


class NotReady(AppError):
    code = "not_ready"
    default_message = "The service is not ready."


class PayloadTooLarge(AppError):
    code = "payload_too_large"
    default_message = "The request body is too large."


class InvalidQuery(AppError):
    code = "validation_error"
    default_message = "The request is invalid."


class UpstreamUnavailable(AppError):
    code = "upstream_unavailable"
    default_message = "An upstream service did not answer as expected."


def envelope(code: str, message: str, fields: dict[str, str] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if fields:
        error["fields"] = fields
    return {"error": error}


async def handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)  # noqa: S101
    headers = {"Retry-After": str(exc.retry_after)} if isinstance(exc, RateLimited) else None
    return JSONResponse(
        status_code=STATUS_BY_CODE.get(exc.code, 400),
        content=envelope(exc.code, exc.message, exc.fields),
        headers=headers,
    )


async def handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    fields: dict[str, str] = {}
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", ()) if part not in ("body", "query")]
        fields[".".join(location) or "body"] = str(error.get("msg", "invalid"))
    return JSONResponse(
        status_code=422,
        content=envelope("validation_error", "The request is invalid.", fields),
    )


async def handle_http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101
    code = "not_found" if exc.status_code == 404 else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content=envelope(code, str(exc.detail)),
        headers=dict(exc.headers or {}),
    )


async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", error_type=type(exc).__name__)
    return JSONResponse(
        status_code=500,
        content=envelope("internal_error", "Something went wrong on our side."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected)

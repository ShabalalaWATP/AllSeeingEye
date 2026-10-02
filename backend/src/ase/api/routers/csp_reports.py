"""Bounded, anonymous browser CSP telemetry. Never log raw URLs or report bodies."""

from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

import structlog
from fastapi import APIRouter, Request, Response

from ase.api.deps import ContainerDep, ContextDep
from ase.api.errors import PayloadTooLarge
from ase.domain.errors import InvalidRequest, RateLimited

router = APIRouter(tags=["security"])
log = structlog.get_logger(__name__)
MAX_REPORT_BYTES = 16 * 1024
MAX_REPORTS = 8


def _summary(body: object) -> dict[str, str]:
    if not isinstance(body, dict):
        raise InvalidRequest("Invalid CSP report.")
    directive = body.get("effective-directive", body.get("effectiveDirective"))
    blocked = body.get("blocked-uri", body.get("blockedURL"))
    document = body.get("document-uri", body.get("documentURL"))
    if (
        not isinstance(directive, str)
        or not isinstance(blocked, str)
        or not isinstance(document, str)
    ):
        raise InvalidRequest("Invalid CSP report.")
    if not re.fullmatch(r"[a-z-]{1,64}", directive):
        raise InvalidRequest("Invalid CSP directive.")
    try:
        blocked_url, document_url = urlsplit(blocked), urlsplit(document)
        hostname = blocked_url.hostname or ""
    except ValueError:
        raise InvalidRequest("Invalid CSP URL.") from None
    # Only hostnames are useful for allowlist diagnostics. data:/blob:/inline
    # content and userinfo must never reach the log, even for malformed reports.
    host = hostname if blocked_url.scheme in {"http", "https"} else ""
    if host and not re.fullmatch(r"[a-zA-Z0-9.:-]{1,253}", host):
        raise InvalidRequest("Invalid CSP host.")
    path = document_url.path
    if not path.startswith("/") or len(path) > 256 or any(ord(c) < 32 for c in path):
        path = "/"
    return {"directive": directive, "blocked_host": host or "non-network", "document_path": path}


@router.post("/security/csp-reports", status_code=204, include_in_schema=False)
async def report_csp(request: Request, container: ContainerDep, context: ContextDep) -> Response:
    for key, limit in (("csp:global", 120), (f"csp:ip:{context.ip}", 20)):
        retry = container.limiter.hit(key, limit, 60)
        if retry is not None:
            raise RateLimited(retry)
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_REPORT_BYTES:
        raise PayloadTooLarge()
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > MAX_REPORT_BYTES:
            raise PayloadTooLarge()
        data.extend(chunk)
    try:
        value = json.loads(data)
    except (ValueError, RecursionError):
        raise InvalidRequest("Invalid CSP report.") from None
    if isinstance(value, dict) and set(value) == {"csp-report"}:
        summaries = [_summary(value["csp-report"])]
    elif isinstance(value, list) and 1 <= len(value) <= MAX_REPORTS:
        if any(not isinstance(item, dict) or item.get("type") != "csp-violation" for item in value):
            raise InvalidRequest("Invalid CSP report.")
        summaries = [_summary(item.get("body")) for item in value]
    else:
        raise InvalidRequest("Invalid CSP report.")
    for summary in summaries:
        log.info("csp_violation", **summary)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})

"""CSP telemetry rejects abuse and logs only a bounded, secret-free summary."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
import structlog
from httpx import AsyncClient

PATH = "/api/security/csp-reports"
REPORT = {
    "effective-directive": "script-src-elem",
    "blocked-uri": "https://user:password@blocked.example/code.js?token=secret#hidden",
    "document-uri": "https://app.test/research?private=query#fragment",
}


@pytest.mark.parametrize("modern", [False, True])
async def test_one_violation_produces_only_sanitised_summary(
    client: AsyncClient, modern: bool
) -> None:
    payload = (
        [
            {
                "type": "csp-violation",
                "body": {
                    "effectiveDirective": REPORT["effective-directive"],
                    "blockedURL": REPORT["blocked-uri"],
                    "documentURL": REPORT["document-uri"],
                },
            }
        ]
        if modern
        else {"csp-report": REPORT}
    )
    with structlog.testing.capture_logs() as logs:
        response = await client.post(PATH, json=payload)
    assert response.status_code == 204
    entries = [entry for entry in logs if entry["event"] == "csp_violation"]
    assert entries == [
        {
            "event": "csp_violation",
            "log_level": "info",
            "directive": "script-src-elem",
            "blocked_host": "blocked.example",
            "document_path": "/research",
        }
    ]


@pytest.mark.parametrize("chunked", [False, True])
async def test_oversized_reports_are_rejected(client: AsyncClient, chunked: bool) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"x" * 9000
        yield b"x" * 9000

    response = await client.post(PATH, content=chunks() if chunked else b"x" * 18000)
    assert response.status_code == 413


async def test_rate_limit_applies_to_anonymous_reports(client: AsyncClient) -> None:
    statuses = [
        (await client.post(PATH, json={"csp-report": REPORT})).status_code for _ in range(21)
    ]
    assert statuses == [204] * 20 + [429]


@pytest.mark.parametrize(
    "payload",
    [
        [],
        [{}] * 9,
        {"csp-report": {}},
        {"csp-report": {**REPORT, "effective-directive": "script\nforged"}},
        {"csp-report": {**REPORT, "blocked-uri": "https://[bad"}},
    ],
)
async def test_malformed_reports_never_log(client: AsyncClient, payload: object) -> None:
    with structlog.testing.capture_logs() as logs:
        response = await client.post(PATH, content=json.dumps(payload))
    assert response.status_code == 422
    assert not [entry for entry in logs if entry["event"] == "csp_violation"]

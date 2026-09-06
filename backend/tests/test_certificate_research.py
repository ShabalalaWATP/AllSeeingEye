"""Certificate logs are bounded snapshots, not evidence of ownership or live service."""

from dataclasses import replace
from datetime import timedelta
from typing import Any

import httpx
import pytest

from ase.adapters.research_records.certificates import CertificateTransparencyProvider
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, DOMAIN, QUERY, RecordService

KEY = "synthetic-certificate-api-fixture"


def issuance(index: int = 1) -> dict[str, Any]:
    return {
        "id": str(index),
        "tbs_sha256": f"{index:064x}",
        "cert_sha256": f"{index + 100:064x}",
        "dns_names": ["example.com", "other-unrelated.com"],
        "not_before": "2026-01-01T00:00:00Z",
        "not_after": "2027-01-01T00:00:00Z",
        "issuer": {
            "friendly_name": "Synthetic issuer",
            "website": "https://should-not-fetch.invalid",
        },
        "revoked": False,
    }


async def test_exact_host_one_authenticated_request_keeps_validity_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, [issuance()])
    provider = CertificateTransparencyProvider(service.http, CLOCK, KEY)
    result = await provider.collect(DOMAIN)
    assert len(service.requests) == len(service.guarded) == len(result.items) == 1
    request = service.requests[0]
    assert request.url.host == "api.certspotter.com" and request.url.path == "/v1/issuances"
    assert request.url.params["domain"] == "example.com"
    assert request.url.params["include_subdomains"] == "false"
    assert request.url.params["match_wildcards"] == "false"
    assert request.url.params.get_list("expand") == ["dns_names", "issuer"]
    assert "after" not in request.url.params and "cert_der" not in str(request.url)
    assert request.headers["authorization"] == f"Bearer {KEY}"
    event = result.items[0]
    assert event.grade == "F6" and event.published_at == event.observed_at == CLOCK.now()
    assert event.attributes["certificate_not_before"] == "2026-01-01T00:00:00+00:00"
    assert event.attributes["ownership"] == "not established"
    assert event.attributes["active_service"] == "not checked"
    assert event.attributes["reported_revoked"] is False
    assert event.attributes["reported_issuer"] == "Synthetic issuer"
    assert "oldest discovery first" in result.attempts[0].explanation
    assert KEY not in repr(result) and DOMAIN.question not in str(request.url)
    await service.http.aclose()


async def test_missing_key_and_unsafe_subjects_make_no_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch)
    provider = CertificateTransparencyProvider(service.http, CLOCK)
    assert (await provider.collect(DOMAIN)).attempts[0].status is CollectionStatus.UNAVAILABLE
    for subject in (
        "*.example.com",
        "%.example.com",
        "http://example.com",
        "127.0.0.1",
        "com",
        "private.local",
    ):
        result = await provider.collect(replace(DOMAIN, subject=subject))
        assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
    assert (await provider.collect(QUERY)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert not service.requests
    await service.http.aclose()


async def test_idna_subject_matches_only_exact_certificate_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = issuance()
    row["dns_names"] = ["xn--bcher-kva.de"]
    service = RecordService(monkeypatch, [row])
    result = await CertificateTransparencyProvider(service.http, CLOCK, KEY).collect(
        replace(DOMAIN, subject="Bücher.de.")
    )
    assert result.items[0].attributes["domain"] == "xn--bcher-kva.de"
    assert service.requests[0].url.params["domain"] == "xn--bcher-kva.de"
    await service.http.aclose()


@pytest.mark.parametrize(
    "field,value",
    [
        ("tbs_sha256", "invalid"),
        ("cert_sha256", None),
        ("id", None),
        ("id", "x" * 121),
        ("id", "bad\nidentifier"),
        ("not_before", "invalid"),
        ("not_after", None),
        ("not_before", "2026-01-01"),
        ("not_before", "2028-01-01T00:00:00Z"),
        ("not_after", "2026-02-01T00:00:00Z"),
        ("dns_names", "example.com"),
        ("dns_names", ["*.example.com"]),
        ("dns_names", ["sub.example.com"]),
        ("dns_names", ["other.com"]),
        ("dns_names", ["example.com"] * 1001),
    ],
    ids=[
        "tbs",
        "cert",
        "id-missing",
        "id-size",
        "id-control",
        "date-invalid",
        "date-missing",
        "naive-date",
        "reversed-dates",
        "expired",
        "names-shape",
        "wildcard",
        "subdomain",
        "unrelated",
        "names-size",
    ],
)
async def test_invalid_or_out_of_scope_rows_are_excluded(
    monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    row = issuance()
    row[field] = value
    service = RecordService(monkeypatch, [row])
    result = await CertificateTransparencyProvider(service.http, CLOCK, KEY).collect(DOMAIN)
    assert not result.items and result.attempts[0].status is CollectionStatus.EMPTY
    await service.http.aclose()


async def test_page_cap_deduplication_and_unknown_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unknown = issuance()
    unknown.pop("issuer")
    unknown["revoked"] = "false"
    service = RecordService(
        monkeypatch, [None, unknown, unknown, *[issuance(index) for index in range(2, 30)]]
    )
    result = await CertificateTransparencyProvider(service.http, CLOCK, KEY).collect(DOMAIN)
    assert len(result.items) == 20 and len({event.id for event in result.items}) == 20
    assert result.items[0].attributes["reported_issuer"] == "unknown"
    assert result.items[0].attributes["reported_revoked"] is None
    await service.http.aclose()


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
async def test_errors_are_safe_and_not_retried(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    service = RecordService(
        monkeypatch,
        response=httpx.Response(
            status,
            text=f"private body {KEY}",
            headers={"location": "https://other.example/private"},
        ),
    )
    result = await CertificateTransparencyProvider(service.http, CLOCK, KEY).collect(DOMAIN)
    assert result.attempts[0].status is CollectionStatus.FAILED and len(service.requests) == 1
    assert KEY not in repr(result) and "private" not in repr(result)
    await service.http.aclose()


@pytest.mark.parametrize(
    "age,count", [(timedelta(), 5), (timedelta(seconds=2), 75), (timedelta(minutes=2), 100)]
)
async def test_free_plan_rate_windows_are_enforced(
    monkeypatch: pytest.MonkeyPatch, age: timedelta, count: int
) -> None:
    service = RecordService(monkeypatch, [])
    provider = CertificateTransparencyProvider(service.http, CLOCK, KEY)
    provider._requests.extend([CLOCK.now() - age] * count)
    assert (await provider.collect(DOMAIN)).attempts[0].status is CollectionStatus.BUDGET_EXHAUSTED
    assert not service.requests
    provider._requests.clear()
    provider._requests.append(CLOCK.now() - timedelta(hours=1))
    assert (await provider.collect(DOMAIN)).attempts[0].status is CollectionStatus.EMPTY
    await service.http.aclose()


async def test_malformed_response_timeout_and_invalid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch, {"error": "private"})
    provider = CertificateTransparencyProvider(service.http, CLOCK, KEY)
    assert (await provider.collect(DOMAIN)).attempts[0].status is CollectionStatus.FAILED

    async def timeout(*args: object, **kwargs: object) -> None:
        raise TimeoutError("private request")

    monkeypatch.setattr(service.http, "get_json", timeout)
    assert (await provider.collect(DOMAIN)).attempts[0].status is CollectionStatus.TIMED_OUT
    with pytest.raises(ValueError, match="configuration"):
        CertificateTransparencyProvider(service.http, CLOCK, "bad\nkey")
    await service.http.aclose()

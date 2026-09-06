"""DNS and registry observations do not imply ownership or follow referrals."""

from dataclasses import replace
from typing import Any
from urllib.parse import parse_qs

import pytest

from ase.adapters.research_records import DnsResearchProvider, RdapResearchProvider
from ase.adapters.research_records.domains import DNS_TYPES
from ase.adapters.research_records.records import domain_name
from ase.domain.events import Credibility
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, COMPANY, DOMAIN, RecordService, dns_payload


@pytest.mark.parametrize(
    "value",
    [
        None,
        42,
        {},
        [],
        "",
        "localhost",
        "a.local",
        "a.test",
        "127.0.0.1",
        "[::1]",
        "https://example.com",
        "u:p@example.com",
        "example.com/path",
        "example.com?x=1",
        "example.com#fragment",
        "a..com",
        "example.com..",
        "-a.com",
        "a_.com",
        "a.1",
        "a" * 64 + ".com",
        ".".join(["a" * 63] * 5),
        "a.\ud800",
    ],
)
def test_domain_rejects_urls_addresses_and_malformed_names(value: Any) -> None:
    assert domain_name(value) is None


def test_domain_normalises_idna_and_single_absolute_suffix() -> None:
    assert domain_name(" BÜCHER.de. ") == "xn--bcher-kva.de"


@pytest.mark.parametrize("record_type", ["ANY", "TXT", "a", ""])
def test_dns_type_must_be_explicit_and_bounded(
    monkeypatch: pytest.MonkeyPatch,
    record_type: str,
) -> None:
    service = RecordService(monkeypatch)
    with pytest.raises(ValueError, match="Supported DNS types"):
        DnsResearchProvider(service.http, CLOCK, record_type)


async def test_dns_cname_chain_is_one_resolver_request_and_never_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = dns_payload(
        answers=[
            {"name": "edge.other.net", "type": 1, "data": "10.0.0.1"},
            {"name": "example.com.", "type": 5, "data": "edge.other.net."},
            {"name": "unrelated.net", "type": 1, "data": "8.8.8.8"},
            {"name": "example.com", "type": 1, "data": "2001:db8::1"},
            {"name": "example.com", "type": 1, "data": "not an address"},
            {"name": "example.com", "type": 1, "data": "x" * 301},
            {"name": "example.com", "type": 5, "data": {}},
            None,
        ]
    )
    service = RecordService(monkeypatch, data)
    batch = await DnsResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert len(batch.items) == len(service.requests) == len(service.guarded) == 1
    request = service.requests[0]
    assert request.url.host == "dns.google"
    assert parse_qs(request.url.query.decode()) == {
        "name": ["example.com"],
        "type": ["A"],
        "cd": ["false"],
        "edns_client_subnet": ["0.0.0.0/0"],
    }
    assert DOMAIN.question not in str(request.url)
    item = batch.items[0]
    assert item.published_at == CLOCK.now()
    assert item.credibility is Credibility.CANNOT_BE_JUDGED
    assert item.attributes["answer_count"] == 1
    assert item.attributes["resolver_dnssec_authenticated"] is True
    assert "10.0.0.1" in (item.summary or "")
    assert "8.8.8.8" not in (item.summary or "")
    assert "does not identify the owner" in (item.summary or "")
    assert "not independent client verification" in (item.summary or "")
    await service.http.aclose()


@pytest.mark.parametrize(
    ("record_type", "values", "expected"),
    [
        ("AAAA", ["2001:db8::1", "192.0.2.1"], "2001:db8::1"),
        ("NS", ["NS1.EXAMPLE.NET.", 7], "ns1.example.net"),
        (
            "MX",
            ["10 mail.example.net.", "65536 bad.example.net", "bogus", "0 ."],
            "0 .; 10 mail.example.net",
        ),
    ],
)
async def test_dns_supported_record_values(
    monkeypatch: pytest.MonkeyPatch,
    record_type: str,
    values: list[Any],
    expected: str,
) -> None:
    number = DNS_TYPES[record_type]
    data = dns_payload(number, [{"name": "example.com", "type": number, "data": v} for v in values])
    service = RecordService(monkeypatch, data)
    batch = await DnsResearchProvider(service.http, CLOCK, record_type).collect(DOMAIN)
    assert len(batch.items) == 1
    assert expected in (batch.items[0].summary or "")
    assert batch.items[0].source_id == f"research-dns-{record_type.lower()}"
    await service.http.aclose()


async def test_dns_snapshot_caps_answer_count(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = [{"name": "example.com", "type": 1, "data": f"192.0.2.{i}"} for i in range(1, 40)]
    service = RecordService(monkeypatch, dns_payload(answers=answers))
    batch = await DnsResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert len(batch.items) == 1
    assert batch.items[0].attributes["answer_count"] == 20
    await service.http.aclose()


@pytest.mark.parametrize(
    "replacement",
    [
        {"Status": True},
        {"Status": 2},
        {"TC": True},
        {"Question": {}},
        {"Question": [{"name": 9, "type": 1}]},
        {"Question": [{"name": "different.com", "type": 1}]},
        {"Question": [{"name": "example.com", "type": 28}]},
        {"Answer": {}},
    ],
)
async def test_dns_rejects_bad_responses(
    monkeypatch: pytest.MonkeyPatch,
    replacement: dict[str, Any],
) -> None:
    service = RecordService(monkeypatch, dns_payload() | replacement)
    batch = await DnsResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert batch.items == ()
    assert batch.attempts[0].status is CollectionStatus.FAILED
    await service.http.aclose()


@pytest.mark.parametrize("replacement", [{"Status": 3}, {"Answer": []}])
async def test_dns_empty_and_nxdomain_are_not_attribution_evidence(
    monkeypatch: pytest.MonkeyPatch,
    replacement: dict[str, Any],
) -> None:
    service = RecordService(monkeypatch, dns_payload() | replacement)
    batch = await DnsResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert batch.attempts[0].status is CollectionStatus.EMPTY
    await service.http.aclose()


async def test_unsupported_subjects_never_make_http_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RecordService(monkeypatch)
    dns = DnsResearchProvider(service.http, CLOCK)
    rdap = RdapResearchProvider(service.http, CLOCK)
    for provider, query in [
        (dns, COMPANY),
        (dns, replace(DOMAIN, subject="http://127.0.0.1")),
        (rdap, COMPANY),
        (rdap, replace(DOMAIN, subject="example.org")),
        (rdap, replace(DOMAIN, subject="sub.example.com")),
    ]:
        assert not provider.supports(query)
        assert (await provider.collect(query)).attempts[0].status is CollectionStatus.UNSUPPORTED
    assert service.requests == []
    await service.http.aclose()


async def test_rdap_ignores_contacts_and_external_referrals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = {
        "objectClassName": "domain",
        "ldhName": "EXAMPLE.NET",
        "handle": "public-handle",
        "status": ["client transfer prohibited", {}],
        "nameservers": [{"ldhName": "ns1.example.net"}, {"ldhName": 3}, "invalid"],
        "events": [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}, 3],
        "links": [{"href": "http://127.0.0.1/secret", "rel": "related"}],
        "entities": [{"vcardArray": ["vcard", ["private address"]]}],
    }
    service = RecordService(monkeypatch, data)
    batch = await RdapResearchProvider(service.http, CLOCK).collect(
        replace(DOMAIN, subject="example.net")
    )
    assert len(batch.items) == len(service.requests) == 1
    assert str(service.requests[0].url) == "https://rdap.verisign.com/net/v1/domain/example.net"
    item = batch.items[0]
    assert item.attributes["registry_handle"] == "public-handle"
    assert "2020-01-01" in (item.summary or "")
    assert "private address" not in str(batch)
    assert "127.0.0.1" not in str(batch)
    assert "does not establish beneficial ownership" in (item.summary or "")
    assert item.published_at == CLOCK.now()
    await service.http.aclose()


@pytest.mark.parametrize(
    "replacement",
    [
        {"ldhName": "other.com"},
        {"ldhName": []},
        {"objectClassName": "entity"},
        {"events": {}},
        {"nameservers": "invalid"},
        {"status": None},
    ],
)
async def test_rdap_rejects_mismatch_and_bad_fields(
    monkeypatch: pytest.MonkeyPatch,
    replacement: dict[str, Any],
) -> None:
    data = {"objectClassName": "domain", "ldhName": "example.com"} | replacement
    service = RecordService(monkeypatch, data)
    batch = await RdapResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert batch.attempts[0].status is CollectionStatus.FAILED
    await service.http.aclose()


async def test_rdap_minimal_record_and_error_object(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordService(monkeypatch, {"objectClassName": "domain", "ldhName": "example.com"})
    batch = await RdapResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert "not supplied" in (batch.items[0].summary or "")
    await service.http.aclose()
    missing = RecordService(monkeypatch, {"errorCode": 404})
    batch = await RdapResearchProvider(missing.http, CLOCK).collect(DOMAIN)
    assert batch.attempts[0].status is CollectionStatus.EMPTY
    await missing.http.aclose()

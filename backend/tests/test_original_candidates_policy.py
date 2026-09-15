"""Conservative original admission and transport receipt checks, without network access."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.research.original_policy import (
    MAX_ORIGINAL_BYTES,
    OriginalFetchRequest,
    OriginalTransportHop,
    public_address,
    public_origin,
    validate_response,
)
from ase.domain.errors import NotFound
from original_acquisition_support import (
    ADDRESS,
    NOW,
    SOURCE,
    SPEC,
    URL,
    access,
    catalogue,
    event,
    policy,
    response,
)


def test_catalogue_is_scope_bound_and_preserves_admitted_provenance():
    first = catalogue()
    candidate = next(iter(first.candidates.values()))
    assert first.get(candidate.id, access(first.owner_id)) == candidate
    assert candidate.headline == "Original publisher headline"
    assert candidate.issuer == "Original issuer"
    assert candidate.requirement_ids == ("q1",)
    assert candidate.discovered_at == NOW and candidate.published_at is None
    assert candidate.discovery_language == "fr"
    assert candidate.id in catalogue(first.owner_id).candidates
    assert candidate.id not in catalogue().candidates
    with pytest.raises(NotFound):
        first.get(candidate.id, access(uuid4()))
    with pytest.raises(NotFound):
        first.get("model-invented-url", access(first.owner_id))
    with pytest.raises(TypeError):
        first.candidates["new"] = candidate


@pytest.mark.parametrize(
    "changes",
    [
        {"events": (event(),) * 129},
        {"owner_id": "not-a-user"},
        {"team_id": "not-a-team"},
        {"admitted_source_ids": frozenset()},
        {"source_specs": {}},
        {"source_specs": {SOURCE: replace(SPEC, id="different")}},
        {"events": (event(url=None),)},
        {"events": (event(url="x" * 2049),)},
        {"requirement_ids": {}},
        {"requirement_ids": {"admitted-event": ("q1", "q1")}},
        {"requirement_ids": {"admitted-event": ("invalid requirement",)}},
        {"events": (event(observed_at=NOW.replace(tzinfo=None)),)},
        {"events": (event(published_at=NOW.replace(tzinfo=None)),)},
        {"events": (event(), event())},
    ],
)
def test_unadmitted_or_unbounded_candidates_are_rejected(changes):
    with pytest.raises(ValueError):
        catalogue(**changes)


@pytest.mark.parametrize(
    "url",
    [
        "http://publisher.example/report",
        "https://127.0.0.1/report",
        "https://[::1]/report",
        "https://user:secret@publisher.example/report",
        "https://publisher.example:8443/report",
        "https://publisher.example/report#anchor",
        "https://publisher.local/report",
        "https://localhost/report",
        "https://a..example/report",
        "https://publisher.example\\@127.0.0.1/report",
        "https://publisher.example/\nreport",
        "https://publisher.example/é",
        "",
        "https://[invalid-ip]/report",
    ],
)
def test_direct_unsafe_url_is_rejected_before_fetch(url):
    with pytest.raises(ValueError):
        public_origin(url)
    assert not policy().permits(url, NOW)


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "169.254.169.254",
        "224.0.0.1",
        "::1",
        "fc00::1",
        "::ffff:93.184.216.34",
        "2002:5db8:d822::1",
        "not-an-address",
        "64:ff9b::7f00:1",
        "64:ff9b:1::a00:1",
    ],
)
def test_unsafe_resolved_addresses_are_rejected(address):
    assert not public_address(address)


def test_reviewed_policy_limits_origin_path_queries_and_expiry():
    reviewed = policy(allowed_path_prefixes=("/public/",), allowed_query_keys=("id",))
    assert reviewed.permits("https://publisher.example/public/report?id=1", NOW)
    for url in (
        "https://other.example/public/report",
        "https://publisher.example/private/report",
        "https://publisher.example/public/../private/report",
        "https://publisher.example/public/%2e%2e/private/report",
        "https://publisher.example/public/report?token=secret",
        "https://publisher.example/public/report?malformed",
    ):
        assert not reviewed.permits(url, NOW)
    assert not reviewed.permits(URL, reviewed.valid_until)
    assert not reviewed.permits(URL, NOW.replace(tzinfo=None))
    assert public_origin(f"https://{ADDRESS}/report") == f"https://{ADDRESS}"
    assert public_origin("https://[2606:4700:4700::1111]/") == "https://[2606:4700:4700::1111]"
    assert public_origin("https://PUBLISHER.EXAMPLE:443/report") == "https://publisher.example"


@pytest.mark.parametrize(
    "changes",
    [
        {"allowed_origins": ()},
        {"allowed_origins": ["https://publisher.example"]},
        {"allowed_origins": ("https://publisher.example/",)},
        {"reviewed_at": NOW.replace(tzinfo=None)},
        {"valid_until": NOW + timedelta(days=8)},
        {"retention_days": 31},
        {"retention_days": True},
        {"max_bytes": MAX_ORIGINAL_BYTES + 1},
        {"max_redirects": 3},
        {"timeout_seconds": 21},
        {"allowed_path_prefixes": ("/public",)},
        {"allowed_query_keys": ("unsafe key",)},
        {"allowed_query_keys": ["id"]},
        {"allowed_path_prefixes": ["/"]},
    ],
)
def test_unbounded_policy_cannot_be_constructed(changes):
    with pytest.raises(ValueError):
        policy(**changes)


def _validate(result):
    reviewed = policy()
    request = OriginalFetchRequest(URL, reviewed, reviewed.max_bytes, 2, 20)
    return validate_response(result, request, reviewed, NOW)


def test_complete_direct_and_redirect_receipts_are_required():
    assert _validate(response()) is None
    final = "https://publisher.example/corrected.txt"
    hops = (
        OriginalTransportHop(URL, (ADDRESS,), ADDRESS, 302, "/corrected.txt"),
        OriginalTransportHop(final, (ADDRESS,), ADDRESS, 200),
    )
    assert _validate(response(canonical_url=final, hops=hops)) is None
    assert (
        _validate(
            response(canonical_url=final, hops=(replace(hops[0], redirect_location=None), hops[1]))
        )
        == "transport_receipt_invalid"
    )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"hops": ()}, "transport_receipt_invalid"),
        ({"requested_url": "https://publisher.example/other"}, "transport_receipt_invalid"),
        ({"canonical_url": "https://publisher.example/other"}, "transport_receipt_invalid"),
        ({"hops": (OriginalTransportHop(URL, (), ADDRESS, 200),)}, "destination_not_permitted"),
        (
            {"hops": (OriginalTransportHop(URL, (ADDRESS, "127.0.0.1"), ADDRESS, 200),)},
            "destination_not_permitted",
        ),
        (
            {"hops": (OriginalTransportHop(URL, (ADDRESS,), "1.1.1.1", 200),)},
            "destination_not_permitted",
        ),
        (
            {"hops": (OriginalTransportHop(URL, (ADDRESS,), ADDRESS, 403),)},
            "http_status_not_permitted",
        ),
        ({"content_encoding": "gzip"}, "compressed_response_not_permitted"),
        ({"body": b""}, "body_limit_or_size_mismatch"),
        ({"body": b"x" * (MAX_ORIGINAL_BYTES + 1)}, "body_limit_or_size_mismatch"),
        ({"wire_body_bytes": 100}, "body_limit_or_size_mismatch"),
        ({"media_type": "text/html"}, "unsupported_media_type"),
        ({"last_modified_at": NOW.replace(tzinfo=None)}, "transport_receipt_invalid"),
        ({"etag": "unsafe\r\nheader"}, "transport_receipt_invalid"),
    ],
)
def test_incomplete_or_unsafe_transport_receipt_fails_closed(changes, reason):
    assert _validate(response(**changes)) == reason


def test_private_redirect_and_redirect_budget_overflow_fail_closed():
    private = "https://127.0.0.1/secret"
    hops = (
        OriginalTransportHop(URL, (ADDRESS,), ADDRESS, 302, private),
        OriginalTransportHop(private, ("127.0.0.1",), "127.0.0.1", 200),
    )
    assert _validate(response(canonical_url=private, hops=hops)) == "destination_not_permitted"
    assert _validate(response(hops=(response().hops[0],) * 4)) == "transport_receipt_invalid"

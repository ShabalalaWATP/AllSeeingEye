"""Saved context keeps its original method and timestamps, including absent legacy metadata."""

import json
from dataclasses import replace
from datetime import timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.reports import SqlReportRepository
from ase.api.schemas_reports import ReportVersionOut
from ase.container import Container
from ase.domain.report_records import analysis_to_dict
from ase.domain.research_context import build_research_context
from ase.domain.research_context_records import context_from_dict, context_to_dict
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_documents_helpers import document_records
from test_research_context import attrs, item


def frozen_context():
    first = item(
        attributes=attrs(
            cik="0000000123",
            ticker="ABC",
            original_publisher="Publisher",
            original_account_url="https://account.test",
            current_snapshot=False,
        ),
        independence_key="parent",
    )
    second = item(
        "E2", independence_key="parent", published_at=first.published_at.replace(tzinfo=None)
    )
    return replace(build_research_context((first, second)), method_version="historic-policy-v0")


def test_saved_context_roundtrip_preserves_offsets_naive_dates_and_policy_without_projection():
    context = frozen_context()
    first = context.timeline[0]
    shifted = first.captured_at.astimezone(timezone(timedelta(hours=5, minutes=30)))
    context = replace(
        context, timeline=(replace(first, captured_at=shifted), *context.timeline[1:])
    )
    payload = json.loads(json.dumps(context_to_dict(context)))
    decoded = context_from_dict(payload)
    assert decoded == context
    assert decoded.timeline[0].captured_at.utcoffset() == timedelta(hours=5, minutes=30)
    assert decoded.timeline[1].published_at.tzinfo is None
    assert decoded.method_version == "historic-policy-v0"
    assert context_from_dict(None) is None and context_to_dict(None) is None


def test_legacy_version_keeps_context_absent_in_analysis_and_api():
    _, version = document_records()
    assert version.research_context is None
    assert "research_context" not in (analysis_to_dict(version) or {})
    assert ReportVersionOut.from_version(version).research_context is None
    # Context alone is sufficient to persist optional metadata.
    version = replace(
        version,
        direction=None,
        advocacy=None,
        period_from=None,
        assessment=None,
        research=None,
        citation_checks=None,
        research_context=frozen_context(),
    )
    assert analysis_to_dict(version)["research_context"] == context_to_dict(
        version.research_context
    )


@pytest.mark.parametrize(
    "path,value",
    [
        (("method_version",), True),
        (("method_version",), ""),
        (("method_version",), "x" * 65),
        (("timeline",), "bad"),
        (("timeline",), [None] * 201),
        (("timeline", 0, "captured_at"), "2026-09-06"),
        (("timeline", 0, "captured_at"), "invalidTdate"),
        (("timeline", 0, "captured_at"), 123),
        (("timeline", 0, "title"), "x" * 2001),
        (("timeline", 0, "current_snapshot"), 1),
        (("identity_candidates", 0, "status"), "confirmed"),
        (("identity_candidates", 0, "evidence_label"), "E999"),
        (("source_chains", 0, "evidence_label"), "E999"),
        (("source_relationships", 0, "evidence_labels"), ["E1"]),
        (("source_relationships", 0, "evidence_labels"), ["E1", "E999"]),
        (("source_relationships", 0, "evidence_labels"), ["E1", "E1"]),
        (("timeline", 0, "temporal_attributes", 0, "value"), {"nested": "bad"}),
    ],
)
def test_malformed_saved_context_is_rejected_without_coercion(path, value):
    payload = context_to_dict(frozen_context())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        context_from_dict(payload)


def test_unknown_missing_and_duplicate_fields_are_rejected_and_encoder_validates():
    payload = context_to_dict(frozen_context())
    with pytest.raises(ValueError, match="fields"):
        context_from_dict({**payload, "invented": True})
    with pytest.raises(ValueError, match="fields"):
        context_from_dict({})
    payload["timeline"].append(payload["timeline"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        context_from_dict(payload)
    with pytest.raises(ValueError, match="text"):
        context_to_dict(replace(frozen_context(), method_version=""))


async def test_sql_and_api_preserve_saved_context_and_legacy_absence(
    container: Container,
    client: AsyncClient,
    user: User,
):
    record, first = document_records(user.id)
    context = frozen_context()
    second = replace(first, id=uuid4(), number=2, research_context=context)
    record.latest_version = 2
    async with container.session_factory() as session:
        repository = SqlReportRepository(session)
        await repository.add(record, first)
        await repository.add_version(record, second)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    url = f"/api/reports/{record.id}"
    old = await client.get(url + "?version=1", headers=bearer(token))
    new = await client.get(url + "?version=2", headers=bearer(token))
    assert old.status_code == new.status_code == 200
    assert old.json()["version"]["research_context"] is None
    assert new.json()["version"]["research_context"]["method_version"] == "historic-policy-v0"
    async with container.session_factory() as session:
        saved = await SqlReportRepository(session).get_version(record.id, 2)
        assert saved is not None and saved.research_context == context

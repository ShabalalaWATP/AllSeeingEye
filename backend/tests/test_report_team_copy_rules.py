"""Team copies keep the promised content and rebind or omit identity-dependent references."""

import json
from dataclasses import replace
from uuid import uuid4

from ase.domain.report_records import analysis_to_dict, evidence_to_list
from ase.domain.report_team_copy import (
    TeamCopyOmission,
    copy_for_team,
    plan_team_copy,
    report_content_sha256,
)
from ase.domain.source_assessment_capture import source_assessment_from_analysis
from ase.domain.source_assessment_report import capture_identity
from feeds_helpers import NOW
from team_copy_helpers import PRIVATE_LABEL, private_version


def _copy(record, version):
    team_id, report_id, version_id = uuid4(), uuid4(), uuid4()
    copied_record, copied = copy_for_team(
        record,
        version,
        report_id=report_id,
        version_id=version_id,
        team_id=team_id,
        copied_by=record.created_by,
        now=NOW,
    )
    return team_id, copied_record, copied


def test_promised_content_is_semantically_equal_under_new_identities() -> None:
    record, version = private_version(uuid4())
    team_id, copied_record, copied = _copy(record, version)
    # Intentionally new identities in the team's scope.
    assert copied_record.id != record.id and copied.id != version.id
    assert copied.report_id == copied_record.id and copied.number == 1
    assert copied_record.team_id == team_id and copied_record.latest_version == 1
    assert copied_record.created_by == record.created_by
    # The promised analytical content, evidence bytes and content hashes are unchanged.
    assert copied.body == version.body
    assert copied.findings == version.findings
    assert evidence_to_list(copied.evidence) == evidence_to_list(version.evidence)
    assert [item.content_hash for item in copied.evidence] == [
        item.content_hash for item in version.evidence
    ]
    assert copied.quality == version.quality
    assert copied.assessment == version.assessment
    assert copied.canonical_requirements == version.canonical_requirements
    assert copied.body.diagrams == version.body.diagrams
    assert copied.markdown == version.markdown
    assert copied.status == version.status and copied_record.status == version.status
    assert report_content_sha256(copied) == report_content_sha256(version)


def test_source_assessment_is_rebound_to_the_new_version_with_equal_values() -> None:
    record, version = private_version(uuid4())
    _, _, copied = _copy(record, version)
    original, rebound = version.source_assessment, copied.source_assessment
    assert original is not None and rebound is not None
    assert original.projection is not None and rebound.projection is not None
    assert rebound.status == "captured" and rebound.report_version_id == copied.id
    assert rebound.frozen_at == original.frozen_at
    assert [row.digest for row in rebound.projection.evidence] == [
        row.digest for row in original.projection.evidence
    ]
    assert {row.capture_id for row in rebound.projection.evidence} == {
        capture_identity(copied.id, row.digest) for row in original.projection.evidence
    }
    assert sorted(
        (row.source_id, row.subject, row.reliability, row.credibility)
        for row in rebound.projection.assessments
    ) == sorted(
        (row.source_id, row.subject, row.reliability, row.credibility)
        for row in original.projection.assessments
    )
    # The frozen binding validates against the copy, as on every later read.
    stored = json.loads(json.dumps(analysis_to_dict(copied)))
    assert stored["source_assessment"]["report_version_id"] == str(copied.id)
    restored = source_assessment_from_analysis(
        stored, report_version_id=copied.id, body=copied.body, evidence=copied.evidence
    )
    assert restored == rebound


def test_private_references_are_omitted_and_listed() -> None:
    record, version = private_version(uuid4())
    _, copied_record, copied = _copy(record, version)
    plan = plan_team_copy(record, version)
    assert copied.brief_id is None and copied.brief_revision is None
    assert copied.claim_generation is None
    assert copied.research is not None
    receipt = copied.research.original_followup[0]
    assert receipt.passage_ref is None and receipt.status == "unavailable"
    assert receipt.reason == "omitted_from_team_copy"
    assert set(copied_record.scope) == {"origin", "question", "report_language"}
    assert set(plan.omissions) == {
        TeamCopyOmission.RESEARCH_BRIEF,
        TeamCopyOmission.CLAIM_GENERATION,
        TeamCopyOmission.ORIGINAL_PASSAGES,
        TeamCopyOmission.SCOPE_REFERENCES,
    }
    assert plan.omitted_scope_keys == (
        "parent_report_id",
        "parent_version",
        "plan",
        "research_input",
        "unrecognised_future_key",
    )


def test_plan_lists_private_input_evidence_for_explicit_disclosure() -> None:
    record, version = private_version(uuid4())
    plan = plan_team_copy(record, version)
    assert [row.label for row in plan.private_inputs] == [PRIVATE_LABEL]
    assert plan.private_inputs[0].source_id == "research_import"
    public_record, public_version = private_version(uuid4(), private_input=False)
    assert plan_team_copy(public_record, public_version).private_inputs == ()


def test_unbindable_source_assessment_is_omitted_not_presented_as_preserved() -> None:
    record, version = private_version(uuid4())
    capture = version.source_assessment
    assert capture is not None and capture.projection is not None
    # Bypass validation to model a stored projection that no longer rebinds.
    object.__setattr__(capture.projection, "evidence", capture.projection.evidence[:-1])
    _, _, copied = _copy(record, version)
    assert copied.source_assessment is not None
    assert copied.source_assessment.status == "unavailable"
    assert copied.source_assessment.projection is None
    assert TeamCopyOmission.SOURCE_ASSESSMENT in plan_team_copy(record, version).omissions


def test_unavailable_receipts_keep_their_reason_under_the_new_version() -> None:
    record, version = private_version(uuid4())
    capture = version.source_assessment
    assert capture is not None
    unavailable = replace(capture, status="unavailable", projection=None, reason="Unbound draft.")
    _, _, copied = _copy(record, replace(version, source_assessment=unavailable))
    assert copied.source_assessment is not None
    assert copied.source_assessment.reason == "Unbound draft."
    assert copied.source_assessment.report_version_id == copied.id

"""The last report boundary validates the body after post-draft edits."""

from dataclasses import replace

import pytest

from ase.application.reports.drafting import Draft
from ase.application.reports.production_types import Totals
from ase.application.reports.production_version import build_version
from ase.application.reports.selection import Selection
from ase.domain.reports import ReportStatus
from production_integration_helpers import production_job
from report_documents_helpers import document_records


async def _version(container, user, body, *, automated=False, previous=None):
    _, sample = document_records(user.id)
    job = production_job(user, container.cipher)
    job = replace(job, request=replace(job.request, automation=automated), previous=previous)
    return await build_version(
        job,
        Draft(body=sample.body),
        body,
        Selection(sample.evidence, 0, len(sample.evidence)),
        Totals(),
        direction=None,
        receipt=None,
        advocacy=None,
        challenge=None,
        url_resolver=None,
        progress=None,
    )


async def test_final_mutation_cannot_bypass_yardstick_for_direct_run(container, user):
    _, sample = document_records(user.id)
    tampered = replace(
        sample.body,
        key_judgements=(
            replace(
                sample.body.key_judgements[0],
                statement="We assess there is a 100% chance of escalation.",
            ),
            *sample.body.key_judgements[1:],
        ),
    )

    version = await _version(container, user, tampered)

    assert version.status is ReportStatus.NEEDS_REVIEW
    assert any(row.rule == "yardstick" and row.location == "KJ1" for row in version.findings)
    assert version.body.key_judgements[0].statement == tampered.key_judgements[0].statement


async def test_same_final_boundary_applies_to_scheduled_edition(container, user):
    _, sample = document_records(user.id)
    tampered = replace(
        sample.body,
        key_judgements=(
            replace(sample.body.key_judgements[0], confidence_statement="Because."),
            *sample.body.key_judgements[1:],
        ),
    )

    version = await _version(container, user, tampered, automated=True)

    assert version.status is ReportStatus.NEEDS_REVIEW
    assert any(row.rule == "confidence" and row.location == "KJ1" for row in version.findings)


async def test_resumed_follow_up_keeps_change_requirement_at_final_boundary(container, user):
    _, sample = document_records(user.id)

    version = await _version(container, user, sample.body, previous=sample)

    assert version.number == 2
    assert version.status is ReportStatus.NEEDS_REVIEW
    assert any(row.rule == "change" and row.location == "KJ1" for row in version.findings)


@pytest.mark.parametrize(
    "statement",
    (
        "There is a 100% probability of escalation.",
        "Escalation is very likely according to this assessment.",
    ),
)
async def test_assessment_prose_cannot_hide_forbidden_chance(container, user, statement):
    _, sample = document_records(user.id)
    body = replace(
        sample.body,
        assessment=(
            replace(
                sample.body.assessment[0],
                text=statement,
            ),
            *sample.body.assessment[1:],
        ),
    )

    version = await _version(container, user, body)

    assert version.status is ReportStatus.NEEDS_REVIEW
    assert any(
        row.rule == "yardstick" and row.location == "assessment[0]" for row in version.findings
    )


async def test_attributed_statistic_is_not_numeric_probability(container, user):
    _, sample = document_records(user.id)
    first = sample.body.reporting[0]
    reporting = replace(
        first,
        items=(
            replace(first.items[0], text="The source reported inflation of 6% in August."),
            *first.items[1:],
        ),
    )
    body = replace(sample.body, reporting=(reporting, *sample.body.reporting[1:]))

    version = await _version(container, user, body)

    assert not any(
        row.rule == "yardstick" and row.location.startswith("reporting.")
        for row in version.findings
    )

"""Synthetic exact report/capture bindings for A01 projection boundary tests."""

from dataclasses import replace
from uuid import UUID

from ase.application.reports.source_assessment_projection import (
    build_source_assessment_projection,
    prepare_source_assessment_targets,
)
from ase.domain.reports import ReportBody
from evidence_matrix_helpers import item, judgement
from source_assessment_helpers import NOW, assertion, source

VERSION = UUID("00000000-0000-4000-8000-000000000001")
SUBJECT = "population-statistics"
EVIDENCE = (replace(item("E1", "A1"), source_id="statistics-office"),)
BODY = ReportBody(key_judgements=(judgement("E1"),))


def targets(body=BODY, evidence=EVIDENCE, version=VERSION, subjects=None):
    return prepare_source_assessment_targets(
        version,
        body,
        evidence,
        subjects=subjects or {row.id: SUBJECT for row in body.key_judgements},
    )


def projection(*, rated=True, **changes):
    prepared = targets()
    scope = prepared.evidence[0].capture_id, prepared.claims[0].claim_id
    return build_source_assessment_projection(
        prepared,
        frozen_at=NOW,
        source_histories={("statistics-office", SUBJECT): (source(),)} if rated else None,
        assertion_histories={scope: (assertion(evidence_id=scope[0], claim_id=scope[1]),)}
        if rated
        else None,
        **changes,
    )

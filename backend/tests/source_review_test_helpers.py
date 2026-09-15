"""Synthetic source-review HTTP setup and exact frozen report fixtures."""

from dataclasses import replace
from datetime import timedelta

from ase.api.routers.source_reviews import router
from ase.application.reports.source_assessment_projection import capture_unassessed_report_sources
from report_documents_helpers import document_records
from source_projection_helpers import BODY, EVIDENCE


async def seed_reviews(app, container, user, *, body=BODY, evidence=EVIDENCE, team_id=None):
    if not any(getattr(route, "path", "").endswith("/source-reviews") for route in app.routes):
        app.include_router(router, prefix="/api")
    container.clock.advance(timedelta(days=14))
    record, version = document_records(user.id)
    record = replace(record, team_id=team_id)
    version = replace(version, body=body, evidence=evidence)
    version.source_assessment = capture_unassessed_report_sources(
        version.id, body, evidence, frozen_at=container.clock.now()
    )
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version, f"/api/reports/{record.id}/versions/1"


def review_payload(**changes):
    return {
        "label": "E1",
        "judgement_id": BODY.key_judgements[0].id,
        "subject": "population-statistics",
        "kind": "reliability",
        "reliability": "A",
        "basis": "Reviewer checked the published methodology and correction history.",
        "expertise_basis": "Relevant statistical methodology and documented competence.",
        **changes,
    }

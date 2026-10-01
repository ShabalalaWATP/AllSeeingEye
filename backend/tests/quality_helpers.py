"""Synthetic report jobs for the administrator research-quality scorecard."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from ase.adapters.persistence.report_job_codec import payload_columns
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.container import Container


def job_payload(
    template: str | None = "intsum", depth: str | None = "quick", model: str | None = "test-model"
) -> dict[str, Any]:
    frozen: dict[str, Any] = {"scope": {"research_mode": depth} if depth else {}}
    if template is not None:
        frozen["template_id"] = template
    return {
        "schema_version": 1,
        "input": frozen,
        "summary": {"model": model} if model else {},
    }


async def insert_job(
    container: Container,
    owner_id: UUID,
    at: datetime,
    *,
    status: str,
    team_id: UUID | None = None,
    version_id: UUID | None = None,
    error: str | None = None,
    title: str = "Synthetic job title",
    **payload: Any,
) -> UUID:
    job_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            ReportJobRow(
                id=job_id,
                brief_id=None,
                brief_revision=None,
                request_key=uuid4(),
                owner_id=owner_id,
                team_id=team_id,
                title=title,
                status=status,
                stage="synthetic",
                created_at=at,
                updated_at=at,
                revision=1,
                lease_token=None,
                lease_until=None,
                report_id=uuid4(),
                version_id=version_id or uuid4(),
                error=error,
                **payload_columns(job_payload(**payload)),
            )
        )
        await session.commit()
    return job_id

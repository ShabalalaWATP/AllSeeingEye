"""Authenticated read-only access to the current application assessment policy."""

from fastapi import APIRouter

from ase.api.deps import CurrentUser
from ase.api.schemas_report_assessment import ReportMethodologyOut
from ase.domain.doctrine import YARDSTICK
from ase.domain.evidence_matrix import evidence_policy_metadata

router = APIRouter(tags=["reports"])


@router.get("/report-methodology")
async def report_methodology(user: CurrentUser) -> ReportMethodologyOut:
    return ReportMethodologyOut.model_validate(
        {
            **evidence_policy_metadata(),
            "probability_yardstick": YARDSTICK,
        }
    )

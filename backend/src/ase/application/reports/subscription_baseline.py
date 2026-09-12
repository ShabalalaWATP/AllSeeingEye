"""Read the exact previous subscription edition inside the current report scope."""

from ase.application.access import AccessPolicy
from ase.application.ports.reports import ReportRepository
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportStatus
from ase.domain.users import User


async def load_subscription_baseline(
    access: AccessPolicy, reports: ReportRepository, actor: User, request: ReportRequest
) -> ReportVersion | None:
    if request.subscription_previous_report_id is None:
        return None
    if not request.automation or request.parent_report_id is not None:
        raise InvalidRequest("Subscription baselines require a scheduled research run.")
    context = await access.background(actor.id, request.team_id)
    record = await reports.get(request.subscription_previous_report_id)
    if record is None:
        # A deliberately deleted report is not silently reconstructed. Retained hashes
        # can still avoid repeats and the drafting guidance discloses the missing edition.
        return None
    context.require_same_scope(actor.id, request.team_id, record.created_by, record.team_id)
    version = await reports.get_version(record.id, 1)
    return version if version is not None and version.status is not ReportStatus.FAILED else None

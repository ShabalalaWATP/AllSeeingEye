"""Administrator research-quality scorecard over existing administrator report access.

Administrators may already read every report (`AccessContext.require_read`), so the
population grants no new right. The scorecard still releases counts and codes only:
no titles, report identifiers, prose, finding messages or reviewer text.
"""

from datetime import timedelta

from ase.application.access import AccessPolicy
from ase.application.policy import require_admin
from ase.application.ports.llm import LlmProfileRepository
from ase.application.ports.research_quality import ResearchQualityReader
from ase.application.ports.services import Clock
from ase.application.reports.templates import TEMPLATES
from ase.domain.errors import InvalidRequest
from ase.domain.research_quality import (
    MAX_QUALITY_JOBS,
    MAX_QUALITY_VERSIONS,
    QUALITY_WINDOWS,
    ResearchQualityScorecard,
    build_scorecard,
)
from ase.domain.users import User

REMOVED_CONNECTION = "Connection no longer configured"


class ResearchQualityService:
    def __init__(
        self,
        reader: ResearchQualityReader,
        profiles: LlmProfileRepository,
        access: AccessPolicy,
        clock: Clock,
    ) -> None:
        self._reader = reader
        self._profiles = profiles
        self._access = access
        self._clock = clock

    async def scorecard(self, actor: User, window_days: int) -> ResearchQualityScorecard:
        if window_days not in QUALITY_WINDOWS:
            raise InvalidRequest("Choose a 7, 30, 90 or 365 day window.")
        access = await self._access.context(actor)
        require_admin(access.actor)
        now = self._clock.now()
        since = now - timedelta(days=window_days)
        versions = await self._reader.versions(access.visibility, since, MAX_QUALITY_VERSIONS)
        jobs = await self._reader.jobs(access.visibility, since, MAX_QUALITY_JOBS)
        names = {str(profile.id): profile.name for profile in await self._profiles.list_all()}
        connections = {row.connection for row in versions[1] if row.connection}
        return build_scorecard(
            generated_at=now,
            window_days=window_days,
            since=since,
            versions=versions,
            jobs=jobs,
            template_labels={key: row.title for key, row in TEMPLATES.items()},
            connection_labels={key: names.get(key, REMOVED_CONNECTION) for key in connections},
        )

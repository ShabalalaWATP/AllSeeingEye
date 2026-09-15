"""Original acquisition selects a scoped admitted result ID, never an arbitrary generated URL."""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from ase.application.access import AccessContext
from ase.domain.errors import NotFound
from ase.domain.events import Event
from ase.domain.research_brief_values import stable_id
from ase.domain.sources import SourceSpec

MAX_ORIGINAL_CANDIDATES = 128


@dataclass(frozen=True, slots=True)
class AdmittedOriginalCandidate:
    id: str
    owner_id: UUID
    team_id: UUID | None
    event_id: str
    source_id: str
    source_name: str
    issuer: str
    requested_url: str = field(repr=False)
    headline: str
    discovered_at: datetime
    published_at: datetime | None
    discovery_language: str
    requirement_ids: tuple[str, ...]


class OriginalCandidateCatalogue:
    """Only composition with an already admitted collection may construct this catalogue.

    Admission is not implied by an Event's existence. Pass the currently authorised source
    IDs and planner-approved requirement mapping after scope/privacy checks. Generated web
    synthesis text and model-proposed URLs are deliberately not constructor inputs.
    """

    def __init__(
        self,
        events: tuple[Event, ...],
        *,
        owner_id: UUID,
        team_id: UUID | None,
        admitted_source_ids: frozenset[str],
        source_specs: Mapping[str, SourceSpec],
        requirement_ids: Mapping[str, tuple[str, ...]],
    ) -> None:
        if (
            len(events) > MAX_ORIGINAL_CANDIDATES
            or not isinstance(owner_id, UUID)
            or (team_id is not None and not isinstance(team_id, UUID))
        ):
            raise ValueError("Original candidate catalogue exceeds its admission bounds")
        candidates: dict[str, AdmittedOriginalCandidate] = {}
        for event in events:
            ids = requirement_ids.get(event.id, ())
            if (
                event.source_id not in admitted_source_ids
                or event.source_id not in source_specs
                or not isinstance(event.url, str)
                or not 1 <= len(event.url) <= 2048
                or not 1 <= len(ids) <= 12
                or len(set(ids)) != len(ids)
                or event.observed_at.utcoffset() is None
                or (event.published_at is not None and event.published_at.utcoffset() is None)
            ):
                raise ValueError("Original candidates require admitted provenance and requirements")
            for requirement_id in ids:
                stable_id(requirement_id, "original.requirement_id")
            spec = source_specs[event.source_id]
            if spec.id != event.source_id:
                raise ValueError(
                    "Original source identity does not match its registered provenance"
                )
            key = hashlib.sha256(
                "\x1f".join(
                    (
                        str(owner_id),
                        str(team_id),
                        event.source_id,
                        event.id,
                        event.url,
                        event.content_hash,
                        *ids,
                    )
                ).encode()
            ).hexdigest()
            if key in candidates:
                raise ValueError("Duplicate original candidate")
            candidates[key] = AdmittedOriginalCandidate(
                key,
                owner_id,
                team_id,
                event.id,
                event.source_id,
                spec.name,
                spec.organisation,
                event.url,
                event.title[:300],
                event.observed_at,
                event.published_at,
                event.language,
                ids,
            )
        self.owner_id, self.team_id = owner_id, team_id
        self.candidates = MappingProxyType(candidates)

    def get(self, candidate_id: str, access: AccessContext) -> AdmittedOriginalCandidate:
        access.require_read(self.owner_id, self.team_id)
        candidate = self.candidates.get(candidate_id)
        if candidate is None:
            raise NotFound("Original candidate not found")
        return candidate

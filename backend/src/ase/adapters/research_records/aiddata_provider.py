"""Private local project research with bounded workers and explicit historical scope."""

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path

from ase.adapters.research_records.aiddata_records import SOURCE_ID, AidDataRecord
from ase.adapters.research_records.aiddata_search import CatalogueResults, search_catalogue
from ase.adapters.research_records.records import receipt
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.project import project_to_dict
from ase.domain.project_lookup import project_lookup
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery


class AidDataProvider:
    supports_planned_terms = True

    id = SOURCE_ID
    name = "AidData Chinese development projects"
    temporal_scope = (
        "Historical commitment-year overlap, at most 30 years. Partial-year matches are possible, "
        "not exact dates. Missing commitment years are excluded."
    )
    spatial_scope = (
        "Intersection with retained project polygons, including boundary contact. "
        "Invalid or unsplit seam geometry is rejected. This does not establish site activity."
    )

    def __init__(self, path: Path | None, clock: Clock, iso3_to_iso2: Mapping[str, str]) -> None:
        self._path, self._clock = path, clock
        self._iso3_to_iso2 = dict(iso3_to_iso2)
        self._iso2_to_iso3 = {value: key for key, value in iso3_to_iso2.items()}
        self._slots = asyncio.Semaphore(2)

    def supports(self, query: ResearchQuery) -> bool:
        try:
            project_lookup(query.terms)
        except ValueError:
            return False
        return (
            query.focus is ResearchFocus.GENERAL
            and query.effective_time_basis is EvidenceTimeBasis.RECORDED
            and self.id in (query.source_ids or ())
            and len(query.country_isos) <= 1
            and (query.country_iso is None or query.country_iso in self._iso2_to_iso3)
        )

    def supports_area(self, query: ResearchQuery) -> bool:
        return query.area is not None and self.supports(query)

    def _finished(self, task: asyncio.Task[CatalogueResults]) -> None:
        # Cancellation of the HTTP caller does not release capacity while its thread still runs.
        self._slots.release()
        if not task.cancelled():
            task.exception()

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select this source with the recorded-time policy and supported country/terms.",
            )
        if self._path is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "No local project catalogue is configured. No download was attempted.",
            )
        project_id, terms = project_lookup(query.terms)
        await self._slots.acquire()
        task = asyncio.create_task(
            asyncio.to_thread(
                search_catalogue,
                self._path,
                terms=terms,
                project_id=project_id,
                since=query.since,
                until=query.until,
                area=query.area,
                recipient_iso3=self._iso2_to_iso3.get(query.country_iso)
                if query.country_iso
                else None,
            )
        )
        task.add_done_callback(self._finished)
        try:
            result = await asyncio.shield(task)
            events = tuple(self._event(record) for record in result.records)
        except (ValueError, OSError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "The local project catalogue is unavailable or invalid; no evidence released.",
            )
        notice = (
            f"Imported catalogue contains {result.catalogue_count} projects; completeness and "
            "source authenticity are not verified. No query was sent to an external provider. "
            f"Catalogue manifest SHA-256: {result.manifest_sha256}. "
            "Source-reported commitments, project status and derived geometry are "
            "not verified outcomes. "
            + ("Results are truncated by the record/byte limit. " if result.truncated else "")
        )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if events else CollectionStatus.EMPTY,
            notice,
            events,
        )

    def _event(self, record: AidDataRecord) -> Event:
        project = record.project
        amount = record.amount_constant_usd_2021
        summary = (
            f"{record.title[:1000]}. Source-reported status: {project.reported_status}. "
            f"Commitment year: {project.commitment_year or 'unknown'}; exact date unknown. "
            f"Reported amount: {amount if amount is not None else 'unknown'} in constant 2021 USD. "
            "A commitment is not a payment and reported completion is not current verification."
        )
        return Event(
            id=event_id(self.id, f"{project.release_id}:{project.project_id}"),
            source_id=self.id,
            category=Category.ECONOMIC,
            subtype="development_project",
            title=record.title[:300],
            summary=summary[:2000],
            url=record.source_url,
            published_at=None,
            observed_at=self._clock.now(),
            reliability=Reliability.F,
            country_iso=self._iso3_to_iso2.get(project.recipient_iso3),
            grade_rationale="Imported historical project assertions remain unassessed.",
            project=project,
            geometry=record.geometry,
            attributes=freeze_attributes(
                {
                    "aiddata_amount_constant_usd_2021": amount,
                    "amount_source_field": "Amount.(Constant.USD.2021)",
                    "sector": record.sector,
                    "record_kind": "historical_development_project",
                    "title_truncated": len(record.title) > 300,
                    "source_authenticity": "Operator-supplied file; authenticity unverified",
                }
            ),
            content_hash=content_hash(
                project.source_sha256,
                record.title,
                summary,
                json.dumps(project_to_dict(project), sort_keys=True),
                record.geometry.sha256 if record.geometry else None,
                amount,
            ),
        )

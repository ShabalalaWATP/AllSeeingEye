"""One bounded spatial catalogue request, retaining source geometry and observation times."""

import json
from datetime import datetime

from ase.application.ports.footprints import FootprintProvider
from ase.domain.events import (
    Category,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.evidence_geometry import EvidenceGeometry, geometry_to_dict
from ase.domain.footprints import Footprint, FootprintQuery
from ase.domain.observation import ObservationMetadata, observation_to_dict
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchQuery,
)

SOURCE_ID = "research-copernicus-footprints"


def footprint_query(query: ResearchQuery) -> FootprintQuery | None:
    if query.focus is not ResearchFocus.GENERAL or query.area is None:
        return None
    bounds = query.area.rectangle_bounds
    if bounds is None:
        return None
    try:
        # Disclosure is authorised by the report origin boundary before collection.
        # Constructing a capability preview does not call the provider.
        return FootprintQuery(bounds, query.since, query.until, True)
    except ValueError:
        return None


def scene_event(scene: Footprint, retrieved_at: datetime) -> Event:
    geometry = scene.source_geometry
    if not isinstance(geometry, EvidenceGeometry):
        raise ValueError("Catalogue record lacks retained original geometry")
    observation = ObservationMetadata(
        acquired_at=scene.captured_at,
        collection_id=scene.collection,
        item_id=scene.id,
        scene_cloud_cover=scene.cloud_cover,
        limitations="Catalogue scene metadata only. No imagery was downloaded or inspected. "
        "Scene cloud cover does not establish visibility of the selected area.",
    )
    title = f"Sentinel-2 catalogue scene {scene.id}"
    summary = (
        f"Scene acquired at {scene.captured_at.isoformat()}. "
        "Original footprint describes catalogue scene coverage, not an event or usable imagery."
    )
    attributes = freeze_attributes({"licence": scene.licence, "licence_url": scene.licence_url})
    digest = content_hash(
        title,
        summary,
        scene.source_url,
        scene.licence,
        scene.licence_url,
        json.dumps(geometry_to_dict(geometry), sort_keys=True, ensure_ascii=False, allow_nan=False),
        json.dumps(
            observation_to_dict(observation), sort_keys=True, ensure_ascii=False, allow_nan=False
        ),
    )
    return Event(
        id=event_id(SOURCE_ID, f"{scene.collection}:{scene.id}"),
        source_id=SOURCE_ID,
        category=Category.SPACE,
        subtype="catalogue_scene",
        title=title,
        summary=summary,
        url=scene.source_url,
        published_at=None,
        observed_at=retrieved_at,
        reliability=Reliability.F,
        grade_rationale="Unassessed catalogue source and claim; imagery has not been inspected.",
        geometry=geometry,
        observation=observation,
        attributes=attributes,
        content_hash=digest,
    )


class CopernicusResearchProvider:
    id = SOURCE_ID
    name = "Copernicus Sentinel-2 catalogue"
    temporal_scope = (
        "Acquisition interval, at most 14 days; one page of at most 20 catalogue scenes."
    )
    spatial_scope = (
        "Native catalogue bounding-box search, at most 10 degrees per side, without wrapping. "
        "Only an exact single rectangle is supported. Scene coverage is not an event location. "
        "Question terms and language variants do not filter this spatial catalogue query."
    )

    def __init__(self, catalogue: FootprintProvider) -> None:
        self._catalogue = catalogue

    def supports(self, query: ResearchQuery) -> bool:
        return footprint_query(query) is not None

    def supports_area(self, query: ResearchQuery) -> bool:
        return self.supports(query)

    def _receipt(self, status: CollectionStatus, count: int, explanation: str) -> CollectionAttempt:
        return CollectionAttempt(self.id, self.name, status, count, explanation[:1000])

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        requested = footprint_query(query)
        if requested is None:
            return ResearchBatch(
                attempts=(
                    self._receipt(
                        CollectionStatus.UNSUPPORTED,
                        0,
                        self.spatial_scope + " " + self.temporal_scope,
                    ),
                )
            )
        result = await self._catalogue.search(requested)
        if result.status == "unavailable":
            return ResearchBatch(
                attempts=(
                    self._receipt(
                        CollectionStatus.UNAVAILABLE,
                        0,
                        result.limitations,
                    ),
                )
            )
        try:
            if len(result.features) > 20:
                raise ValueError("Catalogue result exceeds its admitted bound")
            events = tuple(scene_event(scene, result.queried_at) for scene in result.features)
        except (TypeError, ValueError, OverflowError):
            return ResearchBatch(
                attempts=(
                    self._receipt(
                        CollectionStatus.UNAVAILABLE,
                        0,
                        "Catalogue returned unsupported original geometry or observation metadata. "
                        "No coverage was established.",
                    ),
                )
            )
        explanation = (
            "Additional catalogue pages were not followed; this result is truncated. "
            if result.truncated
            else ""
        ) + result.limitations
        return ResearchBatch(
            events,
            (
                self._receipt(
                    CollectionStatus.COMPLETED if events else CollectionStatus.EMPTY,
                    len(events),
                    explanation,
                ),
            ),
        )

"""Read the packaged infrastructure registers for one scope, only when the question asks.

This provider spends no request and contacts nobody: every dataset is already shipped
with the application and already drawn on the map. It is eligible only under the
reviewed trigger table in `ase.domain.area_assets`, so an election, a court ruling, a
sanctions designation or a cyber advisory naming no place reads no map data at all.
When it declines, the receipt says which check refused it.
"""

from __future__ import annotations

from functools import partial

from ase.adapters.geo.asset_registers import scan_registers
from ase.adapters.geo.scope_geography import ResolvedScope, from_area, from_countries
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.area_assets import (
    NO_TRIGGER_REASON,
    AssetClass,
    asset_triggers,
    trigger_text,
)
from ase.domain.area_inventory import RECORD_CAVEAT, RegisterEntry
from ase.domain.events import (
    Category,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchQuery,
)

SOURCE_ID = "research-asset-register"

_CATEGORIES = {
    AssetClass.DATA_CENTRES: Category.CYBER,
    AssetClass.SUBMARINE_CABLES: Category.CYBER,
    AssetClass.ENERGY_SITES: Category.ECONOMIC,
    AssetClass.SEMICONDUCTOR_SITES: Category.ECONOMIC,
    AssetClass.NUCLEAR_FACILITIES: Category.ECONOMIC,
    AssetClass.GROUND_STATIONS: Category.SPACE,
}
SCANNABLE = frozenset(_CATEGORIES)
LIMITATIONS = (
    "Packaged public registers only: data centres, energy sites, semiconductor sites, "
    "nuclear facilities, satellite ground stations and mapped submarine cable segments. "
    "Each result is a count plus at most six named records, never a catalogue dump. "
    + RECORD_CAVEAT
)
NO_GEOGRAPHY_REASON = (
    "The request carries no geography this application can resolve from packaged data: "
    "no drawn or saved area, and no country code with a packaged outline. No place name "
    "was geocoded and no coordinates were invented."
)


def _triggered(query: ResearchQuery) -> frozenset[AssetClass]:
    """Which registers this question actually asks about, under the reviewed table."""
    text = trigger_text(query.question, query.subject, " ".join(query.terms))
    named = frozenset(
        asset for asset in SCANNABLE if asset.value in {row.name for row in asset_triggers(text)}
    )
    if named:
        return named
    # Drawing an outline is itself a request about the ground inside it, so a drawn or
    # saved area is the one case where no phrase is needed. A country code is not.
    return SCANNABLE if query.area is not None else frozenset()


class AssetRegisterProvider:
    id = SOURCE_ID
    name = "Packaged infrastructure registers"
    temporal_scope = (
        "No interval applies. Each register is a dated snapshot shipped with the "
        "application; the research interval does not filter it and nothing here is an "
        "observation made during the period."
    )
    spatial_scope = (
        "A drawn or saved area matches by exact position inside the outline; a country "
        "scope matches point registers on the dataset's own declared country field. "
        "Mapped cable routes always match by exact intersection with the outline. " + LIMITATIONS
    )

    def supports(self, query: ResearchQuery) -> bool:
        """Cheap: no register is read and no outline is built to answer this."""
        return (
            query.focus is ResearchFocus.GENERAL
            and (query.area is not None or bool(query.country_isos))
            and bool(_triggered(query))
        )

    def supports_area(self, query: ResearchQuery) -> bool:
        return self.supports(query)

    def _receipt(
        self, status: CollectionStatus, explanation: str, items: tuple[Event, ...] = ()
    ) -> ResearchBatch:
        return ResearchBatch(
            items,
            (CollectionAttempt(self.id, self.name, status, len(items), explanation[:1000]),),
        )

    def _scope(self, query: ResearchQuery) -> ResolvedScope | None:
        if query.area is not None:
            return from_area(query.area)
        return from_countries(query.country_isos) if query.country_isos else None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if query.focus is not ResearchFocus.GENERAL:
            return self._receipt(CollectionStatus.UNSUPPORTED, self.spatial_scope)
        classes = _triggered(query)
        if not classes:
            return self._receipt(CollectionStatus.UNSUPPORTED, NO_TRIGGER_REASON)
        if query.area is None and not query.country_isos:
            return self._receipt(CollectionStatus.UNSUPPORTED, NO_GEOGRAPHY_REASON)
        try:
            scope = await joined_thread_call(partial(self._scope, query))
        except ValueError:
            return self._receipt(
                CollectionStatus.UNSUPPORTED,
                "The requested outline topology is unsupported. No envelope was substituted.",
            )
        if scope is None:
            return self._receipt(CollectionStatus.UNSUPPORTED, NO_GEOGRAPHY_REASON)
        isos = () if query.area is not None else query.country_isos
        entries = await joined_thread_call(
            partial(scan_registers, classes, scope, country_isos=isos)
        )
        items = tuple(self._event(entry, scope, query) for entry in entries)
        considered = ", ".join(sorted(asset.value for asset in classes))
        detail = (
            f"Registers considered: {considered}. Scope: {scope.scope.describe()} "
            + " ".join(entry.provenance() for entry in entries)
            + f" {LIMITATIONS}"
        )
        return self._receipt(
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY, detail, items
        )

    def _event(self, entry: RegisterEntry, scope: ResolvedScope, query: ResearchQuery) -> Event:
        asset = AssetClass(entry.asset_class)
        identity = f"{entry.asset_class}:{scope.scope.digest}"
        return Event(
            id=event_id(self.id, identity),
            source_id=self.id,
            category=_CATEGORIES[asset],
            subtype="register_summary",
            title=entry.title(),
            summary=entry.describe(),
            published_at=None,
            observed_at=query.until,
            reliability=Reliability.F,
            grade_rationale=(
                "A packaged public register, not an assessed publisher. The record count is "
                "exact for this dataset and scope; the dataset itself is incomplete."
            ),
            # No point and no geometry: a register summary is not a located observation.
            country_iso=query.country_isos[0] if len(query.country_isos) == 1 else None,
            tags=frozenset({"infrastructure_register", entry.asset_class}),
            attributes=freeze_attributes(
                {
                    "record_kind": "infrastructure_register_summary",
                    "asset_class": entry.asset_class,
                    "dataset_id": entry.dataset_id,
                    "records_in_scope": entry.count,
                    "records_named": len(entry.listed),
                    "snapshot_date": entry.as_of,
                    "matched_by": entry.matched_by,
                    "scope_basis": scope.scope.basis,
                    "scope_limitation": scope.scope.limitation,
                    "attribution": entry.attribution,
                    "licence_url": entry.licence_url,
                    "collection_capability": self.id,
                }
            ),
            content_hash=content_hash(
                identity, str(entry.count), entry.as_of, *(row.name for row in entry.listed)
            ),
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            spatial_scope=self.spatial_scope,
            temporal_scope=self.temporal_scope,
        )

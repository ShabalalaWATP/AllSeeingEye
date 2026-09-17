"""Ukraine tracker datasets and reference imports, from the container's cached snapshots.

Snapshot dates, attribution and licences come from the packaged files the tracker and
reference services already load. The frontline providers are fetched only when the
Ukraine page asks and only when the operator has recorded the terms they rest on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from ase.adapters.feeds import ukraine_frontline as frontline
from ase.adapters.geo import ukraine_oblasts_import, ukraine_reference_import
from ase.application.source_assets import SourceAsset, delivery_detail
from ase.application.source_inventory import ConnectionState, SourceRequirement
from ase.container.source_asset_maps import SNAPSHOT, asset

if TYPE_CHECKING:
    from ase.container import Container

UKRAINE = "Ukraine and occupied territory."
WIKIDATA_HOME = "https://www.wikidata.org/"


def _origin(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}/"


def _frontline(
    key: str,
    name: str,
    organisation: str,
    description: str,
    terms: str,
    url: str,
    enabled: bool,
    setting: str,
    enable_note: str,
    cooldown: str,
) -> SourceAsset:
    requirement = SourceRequirement(
        "toggle",
        enabled,
        "environment",
        setting,
        f"Enabled on the server; refreshed at most every {cooldown}." if enabled else enable_note,
        optional=True,
    )
    return SourceAsset(
        id=key,
        name=name,
        family="ukraine_dataset",
        delivery="request_service",
        organisation=organisation,
        description=description,
        licence_note=terms,
        homepage=_origin(url),
        coverage_note=UKRAINE,
        refresh_note=f"Fetched when the Ukraine page asks, at most every {cooldown}.",
        state=ConnectionState.ON_DEMAND if enabled else ConnectionState.DISABLED_BY_ENVIRONMENT,
        detail=delivery_detail("request_service")
        if enabled
        else "Off until the operator records the terms this provider rests on.",
        requirement=requirement,
    )


def ukraine_assets(container: Container) -> list[SourceAsset]:
    settings = container.settings
    control = container.ukraine_control
    outlines = container.ukraine_outlines
    losses = container.ukraine_confirmed
    harm = container.ukraine_civilian_harm
    reference = container.ukraine_reference
    return [
        asset(
            "ukraine:viina_control",
            "VIINA territorial control",
            "ukraine_dataset",
            SNAPSHOT,
            "Harvard University (VIINA 2.0)",
            "Settlement-level control status and recent changes on the Ukraine page.",
            f"{control.attribution} Licence: {control.licence}." if control else "ODbL 1.0.",
            control.source_url if control else None,
            UKRAINE,
            "Refresh with ase import-ukraine-control.",
            command="ase import-ukraine-control",
            present=control is not None,
            as_of=control.assessment_date.isoformat() if control else None,
            records=len(control.settlements) if control else None,
        ),
        asset(
            "ukraine:oblast_outlines",
            "Oblast outlines",
            "ukraine_dataset",
            SNAPSHOT,
            "geoBoundaries",
            "First-level administrative boundaries for Ukraine.",
            ukraine_oblasts_import.ATTRIBUTION,
            "https://www.geoboundaries.org/",
            UKRAINE,
            "Refresh with ase import-ukraine-oblasts.",
            command="ase import-ukraine-oblasts",
            present=bool(outlines),
            records=len(outlines),
        ),
        asset(
            "ukraine:oryx_losses",
            "Visually confirmed equipment losses",
            "ukraine_dataset",
            SNAPSHOT,
            "Oryx, via the leedrake5 daily mirror",
            "Destroyed, damaged, abandoned and captured equipment for both sides.",
            f"{losses.attribution} Licence: {losses.licence}." if losses else "",
            losses.source_url if losses else None,
            "Russian and Ukrainian equipment.",
            "Refresh with ase import-ukraine-losses.",
            command="ase import-ukraine-losses",
            present=losses is not None,
            as_of=losses.recorded_on.isoformat() if losses else None,
            records=len(losses.days) if losses else None,
        ),
        asset(
            "ukraine:hrmmu_casualties",
            "Civilian casualty reports",
            "ukraine_dataset",
            SNAPSHOT,
            "UN Human Rights Monitoring Mission in Ukraine (OHCHR)",
            "Monthly verified civilian casualty figures, shown beside curated references.",
            "No licence is recorded; figures are cited with attribution to "
            f"{harm.attribution if harm else 'OHCHR'}.",
            harm.source_url if harm else None,
            UKRAINE,
            "Refresh with ase import-ukraine-casualties.",
            command="ase import-ukraine-casualties",
            present=harm is not None,
            as_of=harm.retrieved_at.date().isoformat() if harm else None,
            records=len(harm.months) if harm else None,
        ),
        asset(
            "ukraine:reference_catalogue",
            "Equipment, forces and timeline notes",
            "ukraine_dataset",
            SNAPSHOT,
            "Curated notes resolved through Wikidata and Wikimedia Commons",
            "Equipment notes, force structure and the war timeline with dated sources.",
            reference.source_note if reference else ukraine_reference_import.SOURCE_NOTE,
            WIKIDATA_HOME,
            "Both sides of the war since 2014.",
            "Refresh with ase import-ukraine-reference.",
            command="ase import-ukraine-reference",
            present=reference is not None,
            as_of=reference.retrieved_at.date().isoformat() if reference else None,
            records=(
                len(reference.equipment) + len(reference.forces) + len(reference.events)
                if reference
                else None
            ),
        ),
        _frontline(
            "ukraine:deepstate",
            "DeepStateMap frontline",
            "DeepStateMap.live",
            "Occupied and liberated area polygons; preferred over OCHA when both are on.",
            frontline.DEEPSTATE_TERMS,
            frontline.DEEPSTATE_URL,
            settings.ukraine_deepstate_access == "granted",
            "ASE_UKRAINE_DEEPSTATE_ACCESS",
            "Set ASE_UKRAINE_DEEPSTATE_ACCESS=granted only after DeepStateMap grants API use.",
            "6 hours",
        ),
        _frontline(
            "ukraine:ocha_frontline",
            "OCHA humanitarian frontline",
            "UN OCHA",
            "Humanitarian front line layer credited to ISW and CTP.",
            frontline.OCHA_TERMS,
            frontline.OCHA_URL,
            settings.ukraine_ocha_humanitarian,
            "ASE_UKRAINE_OCHA_HUMANITARIAN",
            "Set ASE_UKRAINE_OCHA_HUMANITARIAN=true if humanitarian-purpose use is suitable.",
            "7 days",
        ),
        _frontline(
            "ukraine:warspotting",
            "WarSpotting geolocated losses",
            "WarSpotting",
            "Geolocated, visually confirmed Russian equipment losses, latest recorded entries.",
            frontline.SPOTTED_TERMS,
            frontline.WARSPOTTING_URL,
            settings.ukraine_warspotting,
            "ASE_UKRAINE_WARSPOTTING",
            "Set ASE_UKRAINE_WARSPOTTING=true after reviewing WarSpotting's terms.",
            "6 hours",
        ),
    ]


def reference_assets(container: Container) -> list[SourceAsset]:
    figures = container.figure_catalogue
    entities = container.reference_catalogue
    provenance = next(
        (entry.provenance for table in entities.entries.values() for entry in table.values()),
        "Packaged reference notes",
    )
    return [
        asset(
            "reference:public_figures",
            "Public figures",
            "reference_dataset",
            SNAPSHOT,
            "Wikidata",
            "Heads of state, ministers and other office holders with portraits.",
            figures.source_note,
            WIKIDATA_HOME,
            "Worldwide; selected offices only.",
            "Refresh with ase import-public-figures.",
            command="ase import-public-figures",
            as_of=figures.retrieved_at.date().isoformat(),
            records=len(figures.figures),
        ),
        asset(
            "reference:entities",
            "Ship and aircraft reference",
            "reference_dataset",
            SNAPSHOT,
            "Wikidata and curated ICAO type notes",
            "Named vessels, aircraft and aircraft types that enrich live tracks.",
            provenance,
            WIKIDATA_HOME,
            "Worldwide; notable entities only.",
            "Refresh with ase import-reference.",
            command="ase import-reference",
            as_of=entities.retrieved_at.date().isoformat(),
            records=sum(len(table) for table in entities.entries.values()),
        ),
        asset(
            "reference:conflicts",
            "Conflict and tension areas",
            "reference_dataset",
            SNAPSHOT,
            "The All Seeing Eye editorial list",
            "Curated wars and tension areas with deliberately generous bounding boxes.",
            "Editorial list maintained in the repository.",
            None,
            "Worldwide; selected areas only.",
            "Updated with the application.",
            # This repository returns an in-memory tuple, not a SQLAlchemy query.
            # nosemgrep: python.sqlalchemy.performance.performance-improvements.len-all-count
            records=len(container.conflicts.all()),
        ),
    ]

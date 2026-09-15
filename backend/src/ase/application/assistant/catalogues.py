"""Metadata-only cached cameras and local infrastructure for bounded map answers."""

from collections.abc import Mapping
from typing import Any

from ase.application.assistant.doctrine_references import DOCTRINE_REFERENCES
from ase.application.assistant.intent import QuestionIntent
from ase.application.assistant.sources import safe_source_url
from ase.application.cameras import CameraCatalogueService
from ase.domain.assistant import AssistantQuestion, AssistantSource
from ase.domain.errors import InvalidRequest
from ase.domain.events import Point
from ase.domain.evidence import injection_flags
from ase.domain.users import User

CATALOGUE_LIMIT = 100


def doctrine_sources(question: AssistantQuestion, intent: QuestionIntent) -> list[AssistantSource]:
    """Expose short, attributed public methodology records only for doctrine questions."""
    if question.selected or not any(
        topic in ("doctrine", "phia", "yardstick") for topic in intent.topics
    ):
        return []
    if question.bbox or question.time_range or intent.time_range:
        return []
    rows = []
    for reference in DOCTRINE_REFERENCES:
        identifier = reference.identifier
        if "phia" in intent.topics and not identifier.startswith("phia"):
            continue
        if "yardstick" in intent.topics and identifier != "phia-uncertainty-2025":
            continue
        source = AssistantSource(
            id="",
            kind="doctrine",
            record_id=identifier,
            source_id=f"doctrine:{identifier}",
            title=reference.title,
            url=reference.url,
            published_at=None,
            observed_at=None,
            point=None,
            grade=None,
            summary=reference.summary,
            details=(
                f"Edition: {reference.edition}; version: {reference.version or 'not verified'}. "
                f"Publication date ({reference.date_basis}): {reference.publication_date}.",
                f"Reference checked {reference.retrieved_on.isoformat()}; "
                f"verification scope: {reference.verification_scope}; "
                f"catalogue publisher: {reference.catalogue_publisher}.",
                reference.access_note,
                f"Short public excerpt ({reference.excerpt.locator}): {reference.excerpt.text}",
                reference.excerpt.reuse_basis,
                "Methodology reference, not event evidence.",
            ),
            publisher=reference.publisher,
        )
        if intent.accepts("doctrine", source):
            rows.append(source)
    return rows


def _infrastructure_url(row: Mapping[str, Any]) -> str | None:
    url = safe_source_url(row.get("source_url") or row.get("website") or row.get("wikipedia"))
    if url is not None:
        return url
    links = row.get("links")
    if not isinstance(links, list):
        return None
    return next(
        (
            allowed
            for link in links[:8]
            if isinstance(link, dict) and (allowed := safe_source_url(link.get("url")))
        ),
        None,
    )


def cached_cameras(
    service: CameraCatalogueService, actor: User, question: AssistantQuestion
) -> tuple[list[AssistantSource], bool, tuple[str, ...]]:
    selected = question.selected
    if selected is not None and selected.kind != "camera":
        return [], False, ()
    catalogue = service.snapshot(
        actor,
        bbox=question.bbox,
        selected_id=selected.id if selected else None,
    )
    if selected and len(catalogue.cameras) > 1:
        raise InvalidRequest("This camera identifier is ambiguous. Select another map item.")
    rows = [
        AssistantSource(
            "",
            "camera",
            camera.id,
            f"camera:{camera.provider}",
            camera.title[:300],
            safe_source_url(camera.source_url),
            None,
            None,
            Point(camera.longitude, camera.latitude),
            None,
            "Public camera facility metadata. No image or stream was viewed or analysed.",
            (
                f"Provider: {camera.provider}; attribution: {camera.attribution[:200]}.",
                f"Coordinate precision: {camera.coordinate_precision}.",
                "Provider-declared image capture time: "
                + (camera.captured_at.isoformat() if camera.captured_at else "unknown")
                + ".",
                "Capture time is provider metadata, not proof of current live imagery.",
            ),
        )
        for camera in catalogue.cameras
        if not injection_flags(camera.title, camera.attribution)
    ]
    unloaded = sum(
        provider.status in ("not_loaded", "unavailable") for provider in catalogue.providers
    )
    notes = (
        "Cached CCTV metadata only; no images, streams or provider refreshes.",
        f"{unloaded} camera providers are not loaded or unavailable in the local cache.",
    )
    return rows, len(catalogue.cameras) >= CATALOGUE_LIMIT, notes


def infrastructure_sources(
    snapshot: Mapping[str, Any], question: AssistantQuestion
) -> tuple[list[AssistantSource], bool, tuple[str, ...]]:
    selected = question.selected
    if selected is not None and selected.kind != "infrastructure":
        return [], False, ()
    groups: list[list[AssistantSource]] = []
    seen: dict[str, int] = {}
    for field, label, limit in (
        ("cables", "Undersea cable", 3000),
        ("ground_stations", "Satellite ground station", 100),
        ("nuclear_facilities", "Nuclear power facility", 1000),
        ("data_centres", "Data centre", 1500),
        ("energy_sites", "Energy site", 3200),
        ("semiconductor_sites", "Semiconductor site", 500),
    ):
        group = []
        for row in snapshot.get(field, ())[:limit]:
            identifier = str(row["id"])
            seen[identifier] = seen.get(identifier, 0) + 1
            if selected and selected.id != identifier:
                continue
            point = (
                Point(float(row["longitude"]), float(row["latitude"]))
                if "longitude" in row and "latitude" in row
                else None
            )
            if question.bbox is not None and (point is None or not question.bbox.contains(point)):
                continue
            title = str(row["name"])[:300]
            note = str(row.get("note") or row.get("significance") or row.get("description") or "")[
                :600
            ]
            if injection_flags(title, note):
                continue
            country = str(row.get("country", ""))[:100]
            url = _infrastructure_url(row)
            snapshot_key = (
                "nuclear_snapshot_date"
                if field == "nuclear_facilities"
                else "data_centre_snapshot_date"
                if field == "data_centres"
                else "site_snapshot_date"
                if field in ("energy_sites", "semiconductor_sites")
                else "snapshot_date"
            )
            group.append(
                AssistantSource(
                    "",
                    "infrastructure",
                    identifier,
                    f"infrastructure:{field}",
                    title,
                    url,
                    None,
                    None,
                    point,
                    None,
                    note,
                    (
                        f"Catalogue: {label}; historical public inventory, status unverified.",
                        f"Snapshot: {str(snapshot.get(snapshot_key, 'unknown'))[:32]}.",
                        f"Country label: {country or 'unknown'}.",
                        f"Coordinate precision: {str(row.get('precision', 'unknown'))[:60]}.",
                        "Cable routes and facility coordinates may be approximate; "
                        "catalogue presence does not establish current operation.",
                    ),
                    country if len(country) == 2 and country.isalpha() else None,
                )
            )
        groups.append(group)
    if selected and seen.get(selected.id, 0) > 1:
        raise InvalidRequest(
            "This infrastructure identifier is ambiguous. Select another map item."
        )
    # Distinct object kinds can share external identifiers; omit ambiguous links globally too.
    groups = [[row for row in group if seen[row.record_id] == 1] for group in groups]
    rows = []
    for offset in range(CATALOGUE_LIMIT):
        for group in groups:
            if offset < len(group):
                rows.append(group[offset])
            if len(rows) >= CATALOGUE_LIMIT:
                break
        if len(rows) >= CATALOGUE_LIMIT:
            break
    return (
        rows,
        sum(map(len, groups)) > len(rows),
        (
            "Historical public infrastructure inventory; operational status is unverified.",
            "Viewport infrastructure matches point facilities only; cable lines are omitted."
            if question.bbox
            else "Cable metadata does not establish a precise incident location.",
        ),
    )

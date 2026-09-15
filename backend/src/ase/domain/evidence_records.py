"""Frozen evidence JSON shared by report persistence and assessment bindings."""

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any

from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import (
    evidence_attributes_from_list,
    evidence_attributes_to_list,
)
from ase.domain.evidence_geometry import geometry_from_dict, geometry_to_dict
from ase.domain.observation import observation_from_dict, observation_to_dict
from ase.domain.project import project_from_dict, project_to_dict
from ase.domain.source_provenance_records import (
    dates_from_list,
    provenance_to_dict,
    transformations_from_list,
)
from ase.domain.source_rating_records import source_rating_from_dict, source_rating_to_dict


def evidence_to_list(items: tuple[EvidenceItem, ...]) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        data = asdict(item)
        data["published_at"] = item.published_at.isoformat() if item.published_at else None
        data["captured_at"] = item.captured_at.isoformat()
        data["observed_at"] = item.observed_at.isoformat() if item.observed_at else None
        data["flags"] = list(item.flags)
        data["source_rating"] = source_rating_to_dict(item.source_rating)
        data["attributes"] = evidence_attributes_to_list(item.attributes)
        # Omit absent additions: saved map revisions hash the historical wire shape.
        data.pop("transformations")
        data.pop("source_dates")
        if item.transformations:
            data["transformations"] = [provenance_to_dict(row) for row in item.transformations]
        if item.source_dates:
            data["source_dates"] = [provenance_to_dict(row) for row in item.source_dates]
        data.pop("geometry")
        data.pop("observation")
        data.pop("project")
        if item.project is not None:
            data["project"] = project_to_dict(item.project)
        if item.geometry is not None:
            data["geometry"] = geometry_to_dict(item.geometry)
        if item.observation is not None:
            data["observation"] = observation_to_dict(item.observation)
        rows.append(data)
    return rows


def evidence_from_list(rows: list[Mapping[str, Any]]) -> tuple[EvidenceItem, ...]:
    return tuple(
        EvidenceItem(
            label=str(row["label"]),
            event_id=str(row["event_id"]),
            source_id=str(row["source_id"]),
            source_name=str(row["source_name"]),
            independence_key=str(row["independence_key"]),
            category=str(row["category"]),
            title=str(row["title"]),
            summary=row.get("summary"),
            url=row.get("url"),
            published_at=datetime.fromisoformat(str(row["published_at"]))
            if row.get("published_at") is not None
            else None,
            captured_at=datetime.fromisoformat(str(row["captured_at"])),
            grade=str(row["grade"]),
            reliability=str(row["reliability"]),
            credibility=int(row["credibility"]),
            grade_rationale=str(row.get("grade_rationale", "")),
            lon=row.get("lon"),
            lat=row.get("lat"),
            country_iso=row.get("country_iso"),
            content_hash=str(row.get("content_hash", "")),
            instrument=bool(row.get("instrument", False)),
            flags=tuple(str(flag) for flag in row.get("flags", [])),
            archive_url=row.get("archive_url"),
            title_en=row.get("title_en"),
            language=row.get("language"),
            geo_confidence=row.get("geo_confidence"),
            observed_at=(
                datetime.fromisoformat(str(row["observed_at"])) if row.get("observed_at") else None
            ),
            story_id=row.get("story_id"),
            source_rating=source_rating_from_dict(row.get("source_rating")),
            attributes=evidence_attributes_from_list(row.get("attributes")),
            geometry=geometry_from_dict(row.get("geometry")),
            observation=observation_from_dict(row.get("observation")),
            project=project_from_dict(row.get("project")),
            transformations=transformations_from_list(row.get("transformations", ())),
            source_dates=dates_from_list(row.get("source_dates", ())),
        )
        for row in rows
    )

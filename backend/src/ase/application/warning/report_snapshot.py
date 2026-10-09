"""Capture only cited report evidence, with bounded explicit versioned codecs."""

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from ase.application.report_jobs.codec_boundary import boundary, json_copy
from ase.application.report_jobs.collection_records import evidence_from_json
from ase.application.reports.alert_origin import origin_from_dict, origin_to_dict
from ase.domain.alert_reports import AlertReportOrigin, AlertReportSnapshot
from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.evidence_records import evidence_to_list
from ase.domain.grading import SourceProfile
from ase.domain.project import project_to_dict
from ase.domain.warning import Alert, Firing, Indicator


def snapshot_to_dict(snapshot: AlertReportSnapshot) -> dict[str, Any]:
    return boundary(
        json_copy(
            {
                "version": 1,
                "origin": origin_to_dict(snapshot.origin),
                "evidence": evidence_to_list(snapshot.evidence),
            }
        ),
        {"version", "origin", "evidence"},
    )


def snapshot_from_dict(value: Any) -> AlertReportSnapshot:
    value = boundary(value, {"version", "origin", "evidence"})
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("Unsupported alert report snapshot version")
    origin = origin_from_dict(value["origin"])
    if origin is None:
        raise ValueError("Missing alert report origin")
    return AlertReportSnapshot(origin, evidence_from_json(value["evidence"]))


def capture_report(
    rule: Indicator, alert: Alert, firing: Firing, profiles: Mapping[str, SourceProfile]
) -> AlertReportSnapshot:
    if rule.research_area is not None:
        raise ValueError("Exact-shape rules do not support automatic reports")
    origin = AlertReportOrigin(
        alert.id,
        rule.id,
        rule.updated_at,
        rule.created_by,
        rule.team_id,
        rule.countries,
        rule.bbox,
        rule.categories,
        rule.keywords,
        rule.severity_floor,
        max(alert.fired_at - rule.window, rule.resumed_at or alert.fired_at - rule.window),
        alert.fired_at + timedelta(microseconds=1),
        alert.count,
        alert.event_ids,
    )
    evidence = []
    for index, event in enumerate(firing.evidence, 1):
        profile = profiles.get(event.source_id)
        flags = injection_flags(
            event.title,
            event.title_en,
            event.summary,
            *(str(value) for value in project_to_dict(event.project).values())
            if event.project is not None
            else (),
        )
        evidence.append(
            EvidenceItem.from_event(
                f"E{index}",
                event,
                alert.fired_at,
                source_name=profile.name if profile else event.source_id,
                independence_key=profile.independence_key if profile else event.source_id,
                instrument=profile.instrument if profile else False,
                source_rating=profile.rating if profile else None,
                flags=flags,
            )
        )
    snapshot = AlertReportSnapshot(origin, tuple(evidence))
    # Check the same strict size/type boundary before the alert transaction.
    return snapshot_from_dict(snapshot_to_dict(snapshot))

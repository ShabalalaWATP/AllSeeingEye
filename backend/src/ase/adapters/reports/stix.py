"""Deterministic STIX 2.1 from frozen evidence only, without inference or network I/O."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from ase.adapters.reports.evidence_package import MAX_EVIDENCE, MAX_PACKAGE_BYTES, _json
from ase.domain.errors import InvalidRequest
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.stix import StixTlp

MARKING_IDS = {
    StixTlp.GREEN: "marking-definition--34098fce-860f-48ae-8e50-ebd3cc5e41da",
    StixTlp.AMBER: "marking-definition--f88d31f6-486f-44da-b317-01333bde0b82",
    StixTlp.RED: "marking-definition--5e57c739-391a-4eb3-b6be-7d15ca92d5ed",
}
MAX_STIX_OBJECTS = 3000
CVE = re.compile(r"\bCVE-\d{4}-\d{4,19}\b", re.IGNORECASE)
ACTOR_URL = re.compile(r"https://attack\.mitre\.org/groups/(G\d{4})/?$")
_CANONICAL_HEADER = re.compile(
    r"\A(?P<title># [^\r\n]*\r?\n\r?\n)Report "
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    r" \\\| version [1-9][0-9]*(?P<separator>\r?\n\r?\n)"
)


def _export_markdown(record: ReportRecord, version: ReportVersion) -> str:
    """Rebind only the generated identity wrapper when frozen content has been copied.

    Team copies retain stored Markdown verbatim. Their STIX description must identify
    the authorised copy, without repeating the personal source's generated header.
    Narrative, explicit citations and legacy Markdown remain unchanged.
    """
    match = _CANONICAL_HEADER.match(version.markdown)
    if match is None:
        return version.markdown
    return (
        f"{match['title']}Report {record.id} \\| version {version.number}{match['separator']}"
        + version.markdown[match.end() :]
    )


def identifier(kind: str, value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{kind}--{uuid5(NAMESPACE_URL, 'https://ase.local/stix/content/' + digest)}"


def stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise InvalidRequest("Frozen STIX dates must include a timezone.")
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def safe_url(value: str | None) -> str | None:
    try:
        parsed = urlsplit(value or "")
        if (
            parsed.scheme in ("https", "http")
            and parsed.hostname
            and not (parsed.username or parsed.password)
        ):
            return value
    except ValueError:
        pass
    return None


class FrozenStixRenderer:
    def render(self, record: ReportRecord, version: ReportVersion, tlp: StixTlp) -> bytes:
        evidence = tuple(item for item in version.evidence if item.category == "cyber")
        if version.report_id != record.id or not evidence or len(version.evidence) > MAX_EVIDENCE:
            raise InvalidRequest(
                "STIX requires a matching frozen version with bounded cyber evidence."
            )
        minimum = len(version.markdown.encode("utf-8")) + sum(
            len(item.title.encode("utf-8")) + len((item.summary or "").encode("utf-8"))
            for item in evidence
        )
        if minimum > MAX_PACKAGE_BYTES:
            raise InvalidRequest("STIX input exceeds the 8 MiB limit.")
        markdown = _export_markdown(record, version)
        marking_id = MARKING_IDS[tlp]
        marking = {
            "type": "marking-definition",
            "spec_version": "2.1",
            "id": marking_id,
            "created": "2017-01-20T00:00:00.000Z",
            "name": f"TLP:{tlp.value.upper()}",
            "definition_type": "tlp",
            "definition": {"tlp": tlp.value},
        }
        timestamp = stamp(version.created_at)
        report_id = identifier("report", [str(version.id), markdown, marking_id])
        common: dict[str, Any] = {
            "spec_version": "2.1",
            "created": timestamp,
            "modified": timestamp,
            "object_marking_refs": [marking_id],
        }
        objects: dict[str, dict[str, Any]] = {}

        def add(obj: dict[str, Any]) -> None:
            if len(objects) >= MAX_STIX_OBJECTS and obj["id"] not in objects:
                raise InvalidRequest("STIX export exceeds 3,000 evidence objects.")
            objects[obj["id"]] = obj

        references: list[dict[str, str]] = []
        for item in evidence:
            attributes = {row.key: row.value for row in item.attributes}
            url = safe_url(item.url)
            reference = {
                "source_name": item.source_name,
                "description": f"Frozen evidence {item.label}; source grade {item.grade}.",
            }
            if url:
                reference["url"] = url
            references.append(reference)
            note = {
                **common,
                "type": "note",
                "abstract": item.title,
                "content": (
                    f"{item.summary or item.title}\n\nCaptured evidence {item.label}, "
                    f"source {item.source_id}, content SHA-256 {item.content_hash}. "
                    "The source grade is not a STIX confidence score."
                ),
                "object_refs": [report_id],
                "external_references": [reference],
            }
            note["id"] = identifier("note", [item.content_hash, note])
            add(note)
            # Explicit CVE identifiers in retained titles, excerpts or structured CVE fields only.
            text = f"{item.title}\n{item.summary or ''}\n{attributes.get('cve', '')}"
            for cve in sorted({match.upper() for match in CVE.findall(text)}):
                vulnerability = {
                    **common,
                    "type": "vulnerability",
                    "name": cve,
                    "external_references": [{"source_name": "cve", "external_id": cve}],
                }
                vulnerability["id"] = identifier("vulnerability", vulnerability)
                add(vulnerability)
            # A canonical frozen MITRE group reference is not an attribution to this incident.
            group = ACTOR_URL.fullmatch(url or "")
            if group:
                group_id = group.group(1)
                actor = {
                    **common,
                    "type": "intrusion-set",
                    "name": group_id,
                    "description": (
                        "ATT&CK group referenced by frozen evidence. This export does not "
                        "establish incident attribution or equivalence of actor names."
                    ),
                    "external_references": [
                        {"source_name": "mitre-attack", "external_id": group_id, "url": url}
                    ],
                }
                actor["id"] = identifier("intrusion-set", actor)
                add(actor)
        report = {
            **common,
            "type": "report",
            "id": report_id,
            "name": markdown.splitlines()[0].lstrip("# ")[:300]
            if markdown
            else f"ASE report version {version.number}",
            "description": (
                f"Frozen ASE report version {version.number}. Status: {version.status.value}. "
                f"Selected {marking['name']} applies to this export; source rights still "
                f"apply.\n\n{markdown}"
            ),
            "published": timestamp,
            "report_types": ["threat-report"],
            "object_refs": sorted(objects),
            "external_references": references,
        }
        ordered = [marking, report, *(objects[key] for key in sorted(objects))]
        return _json({"type": "bundle", "id": identifier("bundle", ordered), "objects": ordered})

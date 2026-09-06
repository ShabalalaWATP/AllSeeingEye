"""Local designation candidates with explicit snapshot age and coverage limitations."""

from dataclasses import replace
from unicodedata import normalize

from ase.adapters.research_records.designation_snapshot import (
    SOURCE_URLS,
    Authority,
    DesignationSnapshot,
)
from ase.adapters.research_records.records import MAX_RESULTS, receipt, record_event
from ase.application.ports import Clock
from ase.domain.events import Category, Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery


def _match_key(value: str) -> str:
    return " ".join(normalize("NFC", value).casefold().split())


class DesignationProvider:
    temporal_scope = (
        "Explicitly imported snapshot date, not a live list or historical reconstruction."
    )

    def __init__(
        self, snapshot: DesignationSnapshot | None, clock: Clock, authority: Authority
    ) -> None:
        if authority not in SOURCE_URLS or (snapshot and snapshot.authority != authority):
            raise ValueError("Designation authority does not match snapshot")
        self._snapshot, self._clock, self.authority = snapshot, clock, authority
        self.id = f"research-designations-{authority}"
        self.name = (
            "UK Sanctions List imported snapshot"
            if authority == "uksl"
            else "OFAC SDN imported snapshot"
        )

    def supports(self, query: ResearchQuery) -> bool:
        subject = (query.subject or "").strip()
        return (
            query.focus in {ResearchFocus.GENERAL, ResearchFocus.COMPANY}
            and bool(subject)
            and (
                self.id in (query.source_ids or ())
                or subject.upper().startswith("UKSL:" if self.authority == "uksl" else "OFAC:")
            )
            and (
                ":" not in subject
                or subject.upper().startswith("UKSL:" if self.authority == "uksl" else "OFAC:")
            )
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply an exact full name candidate or the authority's UKSL:/OFAC: record ID.",
            )
        snapshot = self._snapshot
        if snapshot is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "No designation snapshot is explicitly configured. "
                "No download or screening was performed.",
            )
        subject = (query.subject or "").strip()
        prefix = "UKSL:" if self.authority == "uksl" else "OFAC:"
        by_id = subject.upper().startswith(prefix)
        identity = subject[len(prefix) :].strip().upper() if by_id else ""
        key = _match_key(subject)
        items = []
        seen: set[str] = set()
        for row in snapshot.records:
            matched = (
                row.authority_id.upper() == identity
                if by_id
                else key
                in {
                    _match_key(row.name),
                    _match_key(row.native_name),
                }
            )
            if not matched or row.authority_id in seen:
                continue
            seen.add(row.authority_id)
            event = record_event(
                self.id,
                f"{snapshot.version}:{row.authority_id}",
                f"Imported designation candidate: {row.name}",
                f"The operator-supplied {self.authority} snapshot {snapshot.version} "
                f"dated {snapshot.published_at.isoformat()} contains record {row.authority_id}, "
                f"name {row.name}, programme/regime {row.programme or 'not supplied'}. "
                "This is a record/name candidate, not verified identity, proof of guilt "
                "or a current legal determination.",
                SOURCE_URLS[self.authority],
                self._clock.now(),
                category=Category.ECONOMIC,
                published=snapshot.published_at,
                attributes={
                    "authority_record_id": row.authority_id,
                    "reported_name": row.name,
                    "reported_native_name": row.native_name,
                    "reported_name_type": row.name_type,
                    "reported_kind": row.kind,
                    "reported_programme": row.programme,
                    "reported_designated_on": row.designated_on,
                    "reported_updated_on": row.updated_on,
                    "snapshot_version": snapshot.version,
                    "snapshot_published_at": snapshot.published_at.isoformat(),
                    "source_sha256": snapshot.source_sha256,
                    "declared_licence": snapshot.licence,
                    "record_kind": "imported_designation_candidate",
                    "record_issuer": self.authority,
                    "identity_match": "authority_record_id_only"
                    if by_id
                    else "exact_name_candidate_only",
                    "authenticity": "operator-supplied file; hash is not source authentication",
                    "timestamp_basis": "declared snapshot publication date, not designation date",
                },
            )
            items.append(
                replace(
                    event,
                    reliability=Reliability.F,
                    grade_rationale="Imported authority assertions and identity remain unassessed.",
                )
            )
            if len(items) >= MAX_RESULTS:
                break
        limitations = (
            f"Operator-supplied {snapshot.version} snapshot "
            f"dated {snapshot.published_at.isoformat()}; "
            "at most 20 unique record candidates. Hashes identify bytes, not authenticity. "
            "No live refresh, fuzzy identity resolution or ownership-rule screening was performed. "
            "A match is not proof of identity or guilt; "
            "absence is not clearance or proof of no designation. "
        )
        if self.authority == "ofac_sdn":
            limitations += (
                "OFAC primary SDN CSV only; separate aliases, addresses, "
                "comments and other lists are not covered."
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            limitations,
            items,
        )

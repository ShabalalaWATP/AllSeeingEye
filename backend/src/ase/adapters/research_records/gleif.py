"""Exact LEI snapshots and declared accounting-consolidation parent relationships.

Official API documentation: https://api.gleif.org/docs
Data semantics: https://www.gleif.org/en/lei-data/access-and-use-lei-data
Only constructed allowlisted endpoints are requested; response links are never followed.
"""

import json
import re
from dataclasses import replace
from typing import Any, Literal

from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research_records.record_metadata import bounded_json
from ase.adapters.research_records.records import collect_json, receipt, record_event, text
from ase.adapters.research_records.registry_lookup import RegistryLookupCapability
from ase.application.ports import Clock
from ase.domain.events import Category, Event, Reliability
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

ORIGIN = "https://api.gleif.org/api/v1/lei-records"
LIMITATIONS = (
    "Current GLEIF Golden Copy context, not a historical snapshot for the requested dates. "
    "One exact LEI request; no name resolution, parent traversal or documents fetched. "
    "Reported parent relationships describe accounting consolidation, not independently verified "
    "beneficial ownership. Missing or excepted relationships do not prove that no parent exists. "
    "Shared names or addresses never establish an ownership relationship."
)


def lei_number(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip().upper()
    if candidate.startswith("LEI:"):
        candidate = candidate[4:].strip()
    # Exact identifiers only. The service must echo this LEI before a record is accepted.
    return candidate if re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", candidate) else None


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Invalid GLEIF record object")
    return value


def _unassessed(event: Event) -> Event:
    return replace(
        event,
        reliability=Reliability.F,
        grade_rationale="GLEIF registry assertions and subject identity remain unassessed.",
    )


class GleifProfileProvider(RegistryLookupCapability):
    registry_namespaces = ("lei",)
    id = "research-gleif-profile"
    name = "GLEIF legal entity profile"
    temporal_scope = "Current GLEIF snapshot, not historical-window evidence or complete history."

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http, self._clock = http, clock

    def supports(self, query: ResearchQuery) -> bool:
        return query.focus is ResearchFocus.COMPANY and lei_number(query.subject) is not None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        identity = lei_number(query.subject)
        if not self.supports(query) or identity is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply an exact LEI, optionally prefixed LEI:; no name resolution was made.",
            )
        return await collect_json(
            self._http,
            self.id,
            self.name,
            f"{ORIGIN}/{identity}",
            lambda payload: self._parse(payload, identity),
            LIMITATIONS,
        )

    def _parse(self, payload: dict[str, Any], identity: str) -> list[Event]:
        if payload.get("data") is None:
            return []
        data = _object(payload.get("data"))
        attributes = _object(data.get("attributes"))
        if (
            data.get("type") != "lei-records"
            or data.get("id") != identity
            or attributes.get("lei") != identity
        ):
            raise ValueError("Mismatched LEI")
        entity, registration = (
            _object(attributes.get("entity")),
            _object(attributes.get("registration")),
        )
        legal_name = _object(entity.get("legalName"))
        name = text(legal_name.get("name"), 200)
        if not name:
            raise ValueError("Missing legal name")
        status = text(entity.get("status"), 50)
        return [
            _unassessed(
                record_event(
                    self.id,
                    identity,
                    f"LEI profile: {name}",
                    f"GLEIF reports {name}, LEI {identity}, entity status {status}. "
                    f"Registration status {text(registration.get('status'), 50)}; "
                    f"last reported update {text(registration.get('lastUpdateDate'), 40)}. "
                    "The identifier matches this register record, "
                    "not an independently verified intended subject.",
                    f"{ORIGIN}/{identity}",
                    self._clock.now(),
                    category=Category.ECONOMIC,
                    attributes={
                        "lei": identity,
                        "legal_name": name,
                        "legal_name_language": text(legal_name.get("language"), 16),
                        "reported_entity_status": status,
                        "reported_jurisdiction": text(entity.get("jurisdiction"), 80),
                        "reported_registration_number": text(entity.get("registeredAs"), 120),
                        "reported_registration_status": text(registration.get("status"), 80),
                        "reported_last_update": text(registration.get("lastUpdateDate"), 40),
                        "reported_next_renewal": text(registration.get("nextRenewalDate"), 40),
                        "record_kind": "current_registry_snapshot",
                        "record_issuer": "GLEIF",
                        "identity_match": "requested_lei_only",
                        "timestamp_basis": "collection time; registry dates retained separately",
                    },
                )
            )
        ]


class GleifParentProvider(RegistryLookupCapability):
    registry_namespaces = ("lei",)
    temporal_scope = (
        "Current reported parent context; relationship periods are not snapshot history."
    )

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        kind: Literal["direct", "ultimate"] = "direct",
    ) -> None:
        if kind not in {"direct", "ultimate"}:
            raise ValueError("Unsupported GLEIF parent relationship")
        self._http, self._clock, self.kind = http, clock, kind
        self.id = f"research-gleif-{kind}-parent"
        self.name = f"GLEIF reported {kind} parent"

    def supports(self, query: ResearchQuery) -> bool:
        return query.focus is ResearchFocus.COMPANY and lei_number(query.subject) is not None

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        identity = lei_number(query.subject)
        if not self.supports(query) or identity is None:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Supply an exact LEI; names and addresses are never resolved to parent edges.",
            )
        url = f"{ORIGIN}/{identity}/{self.kind}-parent-relationship"
        return await collect_json(
            self._http,
            self.id,
            self.name,
            url,
            lambda payload: self._parse(payload, identity, url),
            LIMITATIONS,
        )

    def _parse(self, payload: dict[str, Any], identity: str, url: str) -> list[Event]:
        if payload.get("data") is None:
            return []
        data = _object(payload.get("data"))
        if data.get("type") != "relationship-records":
            raise ValueError("No usable parent relationship record")
        attributes = _object(data.get("attributes"))
        relationship = _object(attributes.get("relationship"))
        start, end = _object(relationship.get("startNode")), _object(relationship.get("endNode"))
        expected = (
            "IS_DIRECTLY_CONSOLIDATED_BY"
            if self.kind == "direct"
            else "IS_ULTIMATELY_CONSOLIDATED_BY"
        )
        parent = lei_number(end.get("id"))
        if (
            start.get("id") != identity
            or start.get("type") != "LEI"
            or end.get("type") != "LEI"
            or parent is None
            or relationship.get("type") != expected
        ):
            raise ValueError("Mismatched parent relationship")
        registration = _object(attributes.get("registration"))
        raw_periods = relationship.get("periods", [])
        if not isinstance(raw_periods, list):
            raise ValueError("Invalid relationship periods")
        periods = [
            {key: text(period.get(key), 50) for key in ("type", "startDate", "endDate")}
            for period in raw_periods[:20]
            if isinstance(period, dict)
        ]
        periods_json, periods_omitted = bounded_json(periods)
        # Count both the entry ceiling/malformed rows and the JSON character ceiling.
        periods_omitted += len(raw_periods) - len(periods)
        status = text(relationship.get("status"), 50)
        return [
            _unassessed(
                record_event(
                    self.id,
                    f"{identity}:{self.kind}:{parent}",
                    f"Reported {self.kind} parent of LEI {identity}",
                    f"GLEIF reports {identity} {expected} {parent}; relationship status {status}. "
                    f"Reported periods: {json.dumps(periods, ensure_ascii=False)}. "
                    "This is a reported accounting-consolidation relationship, "
                    "not independent verification of beneficial ownership.",
                    url,
                    self._clock.now(),
                    category=Category.ECONOMIC,
                    attributes={
                        "child_lei": identity,
                        "parent_lei": parent,
                        "reported_relationship_type": expected,
                        "reported_relationship_status": status,
                        "reported_periods": periods_json,
                        "reported_periods_omitted": periods_omitted,
                        "reported_valid_from": text(attributes.get("validFrom"), 40),
                        "reported_valid_to": text(attributes.get("validTo"), 40),
                        "reported_last_update": text(registration.get("lastUpdateDate"), 40),
                        "reported_registration_status": text(registration.get("status"), 50),
                        "reported_corroboration_level": text(
                            registration.get("corroborationLevel"), 80
                        ),
                        "reported_corroboration_documents": text(
                            registration.get("corroborationDocuments"), 120
                        ),
                        "reported_corroboration_reference": text(
                            registration.get("corroborationReference"), 300
                        ),
                        "record_kind": "reported_accounting_consolidation",
                        "record_issuer": "GLEIF",
                        "identity_match": "requested_child_lei_only",
                        "timestamp_basis": "collection time; periods retained separately",
                    },
                )
            )
        ]

"""Small, immutable v2 challenge checkpoints beside the historical v1 packet."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Literal, cast

from ase.application.report_jobs.codec_boundary import boundary, encoded, json_copy
from ase.application.report_jobs.collection_records import (
    evidence_from_json,
    query_to_dict,
    receipt_from_json,
)
from ase.application.reports.challenge_expansion_selection import ADDITION_LIMITS, FINAL_LIMITS
from ase.application.reports.production_checkpoint import ProductionSnapshot
from ase.domain.evidence import EvidenceItem
from ase.domain.report_records import evidence_to_list
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt, research_to_dict

VERSION = "ase-challenge-expansion-v1"
_HASH = re.compile(r"[0-9a-f]{64}\Z")
Status = Literal["ready", "unavailable", "not_applicable"]
PacketStatus = Literal["attempted", "unavailable", "interrupted", "not_applicable"]


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def parent_digest(snapshot: ProductionSnapshot) -> str:
    """Pin the exact v1 selection and scope, not a process-local object identity."""
    return digest(
        {
            "evidence": evidence_to_list(snapshot.selection.items),
            "query": query_to_dict(snapshot.query),
        }
    )


def query_digest(query: ResearchQuery) -> str:
    return digest(query_to_dict(query))


@dataclass(frozen=True, slots=True)
class ExpansionPlan:
    parent: str
    query: str
    target_id: str | None
    terms: tuple[str, ...]
    source_ids: tuple[str, ...]
    status: Status
    version: str = VERSION

    @property
    def fingerprint(self) -> str:
        return digest(plan_to_dict(self))


@dataclass(frozen=True, slots=True)
class ExpansionPacket:
    parent: str
    plan_fingerprint: str
    added: tuple[EvidenceItem, ...]
    receipt: ResearchReceipt | None
    status: PacketStatus
    reason: str
    version: str = VERSION

    @property
    def fingerprint(self) -> str:
        return digest(packet_to_dict(self))


def plan_to_dict(plan: ExpansionPlan) -> dict[str, Any]:
    value = cast(
        "dict[str, Any]",
        json_copy(
            {
                "version": plan.version,
                "parent": plan.parent,
                "query": plan.query,
                "target_id": plan.target_id,
                "terms": plan.terms,
                "source_ids": plan.source_ids,
                "status": plan.status,
            }
        ),
    )
    plan_from_dict(value)
    return value


def plan_from_dict(data: Any) -> ExpansionPlan:
    value = boundary(
        data, {"version", "parent", "query", "target_id", "terms", "source_ids", "status"}
    )
    target = value["target_id"]
    terms, sources = value["terms"], value["source_ids"]
    if (
        value["version"] != VERSION
        or not all(
            type(value[key]) is str and _HASH.fullmatch(value[key]) for key in ("parent", "query")
        )
        or (target is not None and (type(target) is not str or not 1 <= len(target) <= 120))
        or type(terms) is not list
        or len(terms) > 12
        or any(type(term) is not str or not 1 <= len(term.strip()) <= 300 for term in terms)
        or len(terms) != len(set(terms))
        or type(sources) is not list
        or len(sources) > 6
        or any(type(source) is not str or not 1 <= len(source) <= 120 for source in sources)
        or len(sources) != len(set(sources))
        or value["status"] not in {"ready", "unavailable", "not_applicable"}
        or (value["status"] == "ready" and (target is None or not terms or not sources))
    ):
        raise ValueError("Invalid frozen challenge task plan")
    return ExpansionPlan(
        value["parent"], value["query"], target, tuple(terms), tuple(sources), value["status"]
    )


def packet_to_dict(packet: ExpansionPacket) -> dict[str, Any]:
    value = cast(
        "dict[str, Any]",
        json_copy(
            {
                "version": packet.version,
                "parent": packet.parent,
                "plan_fingerprint": packet.plan_fingerprint,
                "added": evidence_to_list(packet.added),
                "receipt": research_to_dict(packet.receipt) if packet.receipt else None,
                "status": packet.status,
                "reason": packet.reason,
            }
        ),
    )
    packet_from_dict(value)
    return value


def packet_from_dict(data: Any) -> ExpansionPacket:
    value = boundary(
        data, {"version", "parent", "plan_fingerprint", "added", "receipt", "status", "reason"}
    )
    if (
        value["version"] != VERSION
        or not all(
            type(value[key]) is str and _HASH.fullmatch(value[key])
            for key in ("parent", "plan_fingerprint")
        )
        or type(value["added"]) is not list
        or len(value["added"]) > 12
        or value["status"] not in {"attempted", "unavailable", "interrupted", "not_applicable"}
        or type(value["reason"]) is not str
        or len(value["reason"]) > 400
    ):
        raise ValueError("Invalid frozen challenge expansion")
    added = evidence_from_json(value["added"])
    receipt = receipt_from_json(value["receipt"])
    if value["status"] == "attempted" and receipt is None:
        raise ValueError("Attempted challenge needs a source receipt")
    return ExpansionPacket(
        value["parent"],
        value["plan_fingerprint"],
        added,
        receipt,
        value["status"],
        value["reason"],
    )


def validate_lineage(
    packet: ExpansionPacket, plan: ExpansionPlan, snapshot: ProductionSnapshot
) -> None:
    """A v2 packet may only append distinct, consecutively labelled selected records.

    Document, media and follow-up selections can already exceed the challenge final limit.
    That limit only bounds appended records, so an empty packet remains valid lineage.
    """
    query = snapshot.query
    if query is None:
        raise ValueError("Challenge expansion requires a frozen research query")
    original = snapshot.selection.items
    allowed = min(ADDITION_LIMITS[query.mode], max(0, FINAL_LIMITS[query.mode] - len(original)))
    first_label = (
        max((int(row.label[1:]) for row in original if row.label[1:].isdigit()), default=0) + 1
    )
    if (
        packet.parent != plan.parent
        or packet.parent != parent_digest(snapshot)
        or packet.plan_fingerprint != plan.fingerprint
        or plan.query != query_digest(query)
        or len(packet.added) > allowed
        or tuple(row.label for row in packet.added)
        != tuple(f"E{first_label + index}" for index in range(len(packet.added)))
        or {row.event_id for row in packet.added} & {row.event_id for row in original}
        or (packet.added and packet.status != "attempted")
    ):
        raise ValueError("Challenge packet breaks frozen evidence lineage")

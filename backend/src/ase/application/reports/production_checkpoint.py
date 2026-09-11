"""The immutable collection boundary retained before resumable drafting starts."""

from dataclasses import dataclass
from typing import Any, Protocol

from ase.application.ports.section_checkpoints import SectionCheckpoints
from ase.application.report_jobs.codec_boundary import boundary, count, json_copy
from ase.application.report_jobs.collection_records import (
    direction_from_json,
    evidence_from_json,
    query_from_dict,
    query_to_dict,
    receipt_from_json,
    totals_from_dict,
    totals_to_dict,
)
from ase.application.reports.production_types import Totals
from ase.application.reports.selection import Selection
from ase.domain.direction import Direction, direction_to_dict
from ase.domain.report_records import evidence_to_list
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt, research_to_dict


@dataclass(frozen=True, slots=True)
class ProductionSnapshot:
    selection: Selection
    direction: Direction | None
    receipt: ResearchReceipt | None
    query: ResearchQuery | None
    totals: Totals


class ProductionCheckpoints(Protocol):
    async def load_collection(self) -> ProductionSnapshot | None: ...
    async def save_collection(self, snapshot: ProductionSnapshot) -> None: ...

    @property
    def section_checkpoints(self) -> SectionCheckpoints: ...


def collection_to_dict(snapshot: ProductionSnapshot) -> dict[str, Any]:
    value: dict[str, Any] = json_copy(
        {
            "schema_version": 1,
            "selection": {
                "items": evidence_to_list(snapshot.selection.items),
                "flagged": snapshot.selection.flagged,
                "considered": snapshot.selection.considered,
            },
            "direction": direction_to_dict(snapshot.direction) if snapshot.direction else None,
            "receipt": research_to_dict(snapshot.receipt) if snapshot.receipt else None,
            "query": query_to_dict(snapshot.query),
            "totals": totals_to_dict(snapshot.totals),
        }
    )
    collection_from_dict(value)
    return value


def collection_from_dict(data: Any) -> ProductionSnapshot:
    try:
        return _collection_from_dict(data)
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Malformed frozen collection checkpoint") from exc


def _collection_from_dict(data: Any) -> ProductionSnapshot:
    value = boundary(
        data, {"schema_version", "selection", "direction", "receipt", "query", "totals"}
    )
    selected = value["selection"]
    if type(selected) is not dict or set(selected) != {"items", "flagged", "considered"}:
        raise ValueError("Invalid frozen evidence selection")
    items = evidence_from_json(selected["items"])
    considered = count(selected["considered"], 100_000)
    flagged = count(selected["flagged"], considered)
    if considered < len(items):
        raise ValueError("Invalid frozen evidence selection counts")
    return ProductionSnapshot(
        Selection(items, flagged, considered),
        direction_from_json(value["direction"]),
        receipt_from_json(value["receipt"]),
        query_from_dict(value["query"]),
        totals_from_dict(value["totals"]),
    )

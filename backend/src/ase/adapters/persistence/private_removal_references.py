"""Bounded exact-path checks of immutable saved references outside a removal.

Free text containing an identifier is not a dependency. Unreadable structured
snapshots fail closed. The global scan has explicit row and encoded-byte ceilings;
reaching either requires resolving the inventory, never an unchecked purge.
"""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncScalarResult, AsyncSession

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.private_removal_selection import RemovalInventory

MAX_REFERENCE_ROWS = 5_000
MAX_REFERENCE_BYTES = 64 * 1024 * 1024


def _object(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if type(value) is not dict:
        raise ValueError("Invalid structured reference")
    return value


def _id(value: Any, removed: set[UUID]) -> bool:
    if value is None:
        return False
    if not isinstance(value, (str, UUID)):
        raise ValueError("Invalid reference identifier")
    return UUID(str(value)) in removed


def scope_reference(scope: Any, removed: set[UUID]) -> bool:
    value = _object(scope)
    if any(
        _id(value.get(key), removed)
        for key in (
            "parent_report_id",
            "origin_report_id",
            "subscription_previous_report_id",
            "map_view_id",
            "map_revision_id",
            "plan_id",
            "plan",
            "aoi_id",
        )
    ):
        return True
    for key, fields in (
        ("research_reuse", ("report_id",)),
        ("map_origin", ("report_id", "report_version_id", "view_id", "revision_id")),
        ("collection_plan_revision", ("id",)),
    ):
        nested = _object(value.get(key))
        if any(_id(nested.get(field), removed) for field in fields):
            return True
    return False


def snapshot_reference(value: Any, removed: set[UUID]) -> bool:
    snapshot = _object(value)
    if scope_reference(snapshot.get("scope"), removed):
        return True
    for key, fields in (
        ("brief_ref", ("id", "parent_report_id")),
        ("brief_reference", ("id",)),
        ("subscription_context", ("report_id",)),
    ):
        nested = _object(snapshot.get(key))
        if any(_id(nested.get(field), removed) for field in fields):
            return True
    inputs = snapshot.get("private_inputs", [])
    if type(inputs) is not list:
        raise ValueError("Invalid private-input reference list")
    for raw_item in inputs:
        if type(raw_item) is not dict:
            raise ValueError("Invalid private-input reference")
        item = _object(raw_item)
        if item.get("kind") == "durable_report" and any(
            _id(item.get(key), removed) for key in ("report_id", "report_version_id")
        ):
            return True
    return False


def _linked(name: str, raw: Any, removed: set[UUID]) -> bool:
    value = json.loads(raw) if isinstance(raw, str) else raw
    if name == "assistant_conversations":
        return conversation_reference(value, removed)
    if name == "source_review_revisions":
        target = _object(_object(value).get("target"))
        return any(_id(target.get(key), removed) for key in ("report_id", "report_version_id"))
    if name == "reports":
        return scope_reference(value, removed)
    if name == "report_jobs":
        return snapshot_reference(_object(value).get("input"), removed)
    if name == "schedules":
        options = _object(value)
        return _id(options.get("baseline_report_id"), removed) or snapshot_reference(
            options, removed
        )
    return (
        ledger_reference(value, removed)
        if name == "report_ledger_entries"
        else snapshot_reference(value, removed)
    )


def ledger_reference(value: Any, removed: set[UUID]) -> bool:
    entry = _object(value)
    if _id(entry.get("report_version_id"), removed):
        return True
    # Forecast decisions can cite a later report, independently of the ledger's
    # anchor. These immutable references are not represented by SQL foreign keys.
    for key in ("evidence", "supporting", "contrary"):
        passages = entry.get(key, [])
        if type(passages) is not list:
            raise ValueError("Invalid ledger passage references")
        if any(_id(_object(passage).get("report_version_id"), removed) for passage in passages):
            return True
    for passage in (
        entry.get("passage"),
        entry.get("source_reference"),
        _object(entry.get("observation")).get("passage"),
    ):
        if _id(_object(passage).get("report_version_id"), removed):
            return True
    return False


def conversation_reference(value: Any, removed: set[UUID]) -> bool:
    turns = _object(value).get("turns", [])
    if not isinstance(turns, list):
        raise ValueError("Invalid conversation")
    for raw_turn in turns:
        turn = _object(raw_turn)
        report = _object(turn.get("report"))
        answer_report = _object(_object(turn.get("answer")).get("report"))
        if (
            _id(report.get("id"), removed)
            or _id(answer_report.get("id"), removed)
            or _id(answer_report.get("version_id"), removed)
        ):
            return True
    return False


async def structured_guards(session: AsyncSession, inventory: RemovalInventory) -> None:
    removed: set[UUID] = set()
    for name in (
        "reports",
        "report_versions",
        "research_brief_revisions",
        "map_views",
        "map_view_revisions",
        "aois",
        "collection_plans",
    ):
        selection = inventory.selections.get(name)
        if selection:
            removed.update(key[0] for key in selection.keys)
    if not removed:
        return
    rows_seen = bytes_seen = 0
    sources = (
        ("reports", "scope"),
        ("report_jobs", "payload"),
        ("research_brief_revisions", "payload"),
        ("subscription_revisions", "request_snapshot"),
        ("schedules", "research_options"),
        ("report_versions", "analysis"),
        ("assistant_conversations", "transcript"),
        ("source_review_revisions", "payload"),
        ("report_ledger_entries", "payload"),
    )
    for name, column in sources:
        table = Base.metadata.tables[name]
        query = (
            select(table.c[column])
            .order_by(*table.primary_key.columns)
            .limit(MAX_REFERENCE_ROWS + 1)
        )
        selected = inventory.selections.get(name)
        if selected:
            query = query.where(~selected.captured())
        result: AsyncScalarResult[Any] = await session.stream_scalars(
            query.execution_options(yield_per=5)
        )
        try:
            async for raw in result:
                rows_seen += 1
                encoded = raw if isinstance(raw, str) else json.dumps(raw)
                bytes_seen += len(encoded.encode())
                if rows_seen > MAX_REFERENCE_ROWS or bytes_seen > MAX_REFERENCE_BYTES:
                    inventory.blockers.add("reference_inventory_incomplete")
                    return
                try:
                    if _linked(name, raw, removed):
                        inventory.blockers.add("retained_structured_reference")
                except (TypeError, ValueError, RecursionError):
                    inventory.blockers.add("unverifiable_structured_reference")
        finally:
            await result.close()

"""Explicit removal selections and bounded, content-free preview identities.

Every row is inventoried before deletion. Captured primary keys avoid relying on
cascades or subqueries whose parents have already disappeared. Unknown incoming
foreign keys block removal rather than silently expanding its scope.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, Table, and_, delete, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.private_removal_authorship import authorship_blocker

MAX_ROWS = 10_000
MAX_BYTES = 256 * 1024 * 1024


def scalar(value: Any) -> Any:
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    if isinstance(value, bytes):
        return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    raise TypeError("Unsupported inventory value")


@dataclass
class Selection:
    table: Table
    predicate: ColumnElement[bool]
    keys: list[tuple[Any, ...]] = field(default_factory=list)

    def captured(self) -> ColumnElement[bool]:
        return tuple_(*self.table.primary_key.columns).in_(self.keys)


class RemovalInventory:
    def __init__(self) -> None:
        self.selections: dict[str, Selection] = {}
        self.blockers: set[str] = set()
        self.digest = hashlib.sha256()
        self.rows = 0
        self.bytes = 0

    def add(self, name: str, predicate: ColumnElement[bool]) -> None:
        if name in self.selections:
            self.selections[name].predicate |= predicate
        else:
            self.selections[name] = Selection(Base.metadata.tables[name], predicate)

    def child(self, name: str, column: str, parent: str, parent_key: str = "id") -> None:
        selected = self.selections.get(parent)
        if selected is not None:
            table = Base.metadata.tables[name]
            self.add(
                name,
                table.c[column].in_(select(selected.table.c[parent_key]).where(selected.predicate)),
            )

    async def capture(self, session: AsyncSession, owner: UUID) -> None:
        for name, selected in sorted(self.selections.items()):
            table = selected.table
            result = await session.stream(
                select(table)
                .where(selected.predicate)
                .order_by(*table.primary_key.columns)
                .limit(MAX_ROWS + 1)
                .execution_options(yield_per=10)
            )
            try:
                async for row in result.mappings():
                    self.rows += 1
                    encoded = json.dumps(
                        dict(row),
                        default=scalar,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode()
                    self.bytes += len(encoded) + sum(
                        len(value) for value in row.values() if isinstance(value, bytes)
                    )
                    if self.rows > MAX_ROWS or self.bytes > MAX_BYTES:
                        self.blockers.add("removal_inventory_limit_use_smaller_scopes")
                        return
                    selected.keys.append(tuple(row[column.name] for column in table.primary_key))
                    self.digest.update(name.encode() + b"\0" + encoded + b"\n")
                    blocker = authorship_blocker(name, dict(row), owner)
                    if blocker:
                        self.blockers.add(blocker)
                    if row.get("team_id") is not None and name not in {
                        "team_memberships",
                        "team_board_read_cursors",
                        "team_board_mentions",
                    }:
                        self.blockers.add("shared_team_record")
                    # Child annotations belong to their author, even on a private report.
                    for column in (
                        "owner_id",
                        "user_id",
                        "created_by",
                        "reviewer_id",
                        "uploader_id",
                    ):
                        if column in row and row[column] != owner:
                            self.blockers.add("other_person_record")
            finally:
                await result.close()

    async def check_foreign_references(self, session: AsyncSession) -> None:
        for table in Base.metadata.sorted_tables:
            for constraint in table.foreign_key_constraints:
                parent = self.selections.get(constraint.referred_table.name)
                if parent is None or not parent.keys:
                    continue
                # Composite references must match one parent row, not independent columns.
                parent_alias = parent.table.alias()
                condition = and_(
                    *(
                        element.parent == parent_alias.c[element.column.name]
                        for element in constraint.elements
                    )
                )
                linked: ColumnElement[bool] = (
                    select(1)
                    .select_from(parent_alias)
                    .where(tuple_(*parent_alias.primary_key).in_(parent.keys), condition)
                    .correlate(table)
                    .exists()
                )
                selected = self.selections.get(table.name)
                if selected is not None:
                    linked &= ~selected.captured()
                if await session.scalar(select(1).select_from(table).where(linked).limit(1)):
                    self.blockers.add("retained_foreign_key_dependency")

    def counts(self) -> dict[str, int]:
        return {
            name: len(selection.keys)
            for name, selection in sorted(self.selections.items())
            if selection.keys
        }

    async def delete(self, session: AsyncSession) -> None:
        # All included self-references disappear together; clear nullable pointers
        # explicitly so both FK-on and FK-off SQLite have the same behaviour.
        selected = self.selections.get("selected_index_records")
        if selected is not None and selected.keys:
            await session.execute(
                selected.table.update().where(selected.captured()).values(corrects_id=None)
            )
        for table in reversed(Base.metadata.sorted_tables):
            selected = self.selections.get(table.name)
            if selected is None:
                continue
            # Keep parameter lists below SQLite's portable bound for composite keys.
            for start in range(0, len(selected.keys), 100):
                predicate = tuple_(*table.primary_key.columns).in_(
                    selected.keys[start : start + 100]
                )
                await session.execute(delete(table).where(predicate))

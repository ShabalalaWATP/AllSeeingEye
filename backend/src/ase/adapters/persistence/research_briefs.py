"""Insert-only, scoped Research Brief revision storage with canonical payload checks."""

from __future__ import annotations

import hashlib
import hmac
import json
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.application.research.brief_codec import brief_from_dict, brief_to_dict
from ase.domain.errors import Conflict, Forbidden
from ase.domain.research_brief import MAX_BRIEF_BYTES, ResearchBrief
from ase.domain.research_brief_values import BriefValidationError


def _canonical_payload(brief: ResearchBrief) -> tuple[str, str, int]:
    value = brief_to_dict(brief)
    # The strict codec must be able to recover exactly what this revision will store.
    if brief_from_dict(value) != brief:
        raise BriefValidationError("brief", "Research Brief cannot round-trip without loss")
    payload = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_BRIEF_BYTES:
        raise BriefValidationError("brief", "Research Brief exceeds its checkpoint size budget")
    return payload, hashlib.sha256(encoded).hexdigest(), len(encoded)


def _decode(row: ResearchBriefRevisionRow) -> ResearchBrief:
    encoded = row.payload.encode("utf-8")
    if (
        not 2 <= len(encoded) <= MAX_BRIEF_BYTES
        or len(encoded) != row.payload_bytes
        or not hmac.compare_digest(hashlib.sha256(encoded).hexdigest(), row.payload_sha256)
    ):
        raise Conflict("Stored Research Brief integrity check failed.")
    try:
        value = json.loads(row.payload)
        if type(value) is not dict:
            raise ValueError("Brief payload must be an object")
        canonical = json.dumps(
            value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        if canonical != row.payload:
            raise ValueError("Brief payload is not canonical")
        brief = brief_from_dict(value)
    except (BriefValidationError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise Conflict("Stored Research Brief validation failed.") from exc
    identity = brief.identity
    if (
        identity.id != row.brief_id
        or identity.revision != row.revision
        or identity.owner_id != row.owner_id
        or identity.team_id != row.team_id
        or identity.title != row.title
        or identity.schema_version != row.schema_version
        or identity.origin != row.origin
        or identity.published != row.published
        or identity.created_at != row.created_at
        or identity.revised_at != row.revised_at
    ):
        raise Conflict("Stored Research Brief identity check failed.")
    return brief


def _scope(actor_id: UUID, authorised_team_ids: tuple[UUID, ...]) -> ColumnElement[bool]:
    if (
        not isinstance(actor_id, UUID)
        or not isinstance(authorised_team_ids, tuple)
        or any(not isinstance(team_id, UUID) for team_id in authorised_team_ids)
    ):
        raise ValueError("Use an authenticated actor and authorised team identifiers.")
    if authorised_team_ids:
        return or_(
            ResearchBriefRevisionRow.owner_id == actor_id,
            ResearchBriefRevisionRow.team_id.in_(authorised_team_ids),
        )
    return ResearchBriefRevisionRow.owner_id == actor_id


class SqlResearchBriefRepository:
    """The caller owns the transaction and supplies verified team memberships."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_revision(
        self,
        brief: ResearchBrief,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
    ) -> ResearchBrief:
        _scope(actor_id, authorised_team_ids)
        identity = brief.identity
        if identity.owner_id != actor_id or (
            identity.team_id is not None and identity.team_id not in authorised_team_ids
        ):
            raise Forbidden("Research Brief owner or team is not authorised.")
        if identity.revision > 1:
            previous = await self.session.get(
                ResearchBriefRevisionRow, (identity.id, identity.revision - 1)
            )
            if previous is None:
                raise Conflict("Research Brief revision history or scope does not match.")
            prior_identity = _decode(previous).identity
            if (
                prior_identity.owner_id != identity.owner_id
                or prior_identity.team_id != identity.team_id
                or prior_identity.created_at != identity.created_at
                or prior_identity.origin != identity.origin
                or prior_identity.revised_at >= identity.revised_at
            ):
                raise Conflict("Research Brief revision history or scope does not match.")
        payload, digest, size = _canonical_payload(brief)
        values = {
            "brief_id": identity.id,
            "revision": identity.revision,
            "owner_id": identity.owner_id,
            "team_id": identity.team_id,
            "title": identity.title,
            "schema_version": identity.schema_version,
            "origin": identity.origin,
            "published": identity.published,
            "created_at": identity.created_at,
            "revised_at": identity.revised_at,
            "payload": payload,
            "payload_sha256": digest,
            "payload_bytes": size,
        }
        dialect = self.session.get_bind().dialect.name
        if dialect == "sqlite":
            await self.session.execute(
                sqlite_insert(ResearchBriefRevisionRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["brief_id", "revision"])
            )
        elif dialect == "postgresql":
            await self.session.execute(
                pg_insert(ResearchBriefRevisionRow)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["brief_id", "revision"])
            )
        else:
            raise RuntimeError("Research Brief storage requires SQLite or PostgreSQL.")
        stored = await self.session.get(
            ResearchBriefRevisionRow, (identity.id, identity.revision), populate_existing=True
        )
        if stored is None or stored.payload_sha256 != digest or stored.payload != payload:
            raise Conflict("A different immutable Research Brief revision already exists.")
        return _decode(stored)

    async def get_revision(
        self,
        brief_id: UUID,
        revision: int,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
    ) -> ResearchBrief | None:
        row = await self.session.scalar(
            select(ResearchBriefRevisionRow)
            .where(
                and_(
                    ResearchBriefRevisionRow.brief_id == brief_id,
                    ResearchBriefRevisionRow.revision == revision,
                    _scope(actor_id, authorised_team_ids),
                )
            )
            .execution_options(populate_existing=True)
        )
        return _decode(row) if row is not None else None

    async def latest_revision(
        self,
        brief_id: UUID,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
    ) -> ResearchBrief | None:
        row = await self.session.scalar(
            select(ResearchBriefRevisionRow)
            .where(
                ResearchBriefRevisionRow.brief_id == brief_id,
                _scope(actor_id, authorised_team_ids),
            )
            .order_by(ResearchBriefRevisionRow.revision.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        return _decode(row) if row is not None else None

"""A single SQL visibility predicate, applied before limits and counts by each repository."""

from uuid import UUID

from sqlalchemy import ColumnElement, and_, exists, or_, true
from sqlalchemy.orm import InstrumentedAttribute

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.teams import TeamMembershipRow, TeamRow
from ase.domain.access import Visibility


def visibility_predicate(
    created_by: InstrumentedAttribute[UUID] | InstrumentedAttribute[UUID | None],
    team_id: InstrumentedAttribute[UUID | None],
    visibility: Visibility,
) -> ColumnElement[bool]:
    if visibility.administrator:
        return true()
    return or_(
        and_(team_id.is_(None), created_by == visibility.user_id),
        team_id.in_(visibility.team_ids),
    )


def background_predicate(
    created_by: InstrumentedAttribute[UUID] | InstrumentedAttribute[UUID | None],
    team_id: InstrumentedAttribute[UUID | None],
) -> ColumnElement[bool]:
    """Background collection requires an active owner and current active-team membership."""
    active_owner = exists().where(UserRow.id == created_by, UserRow.is_active.is_(True))
    active_membership = exists().where(
        TeamMembershipRow.user_id == created_by,
        TeamMembershipRow.team_id == team_id,
        TeamRow.id == TeamMembershipRow.team_id,
        TeamRow.is_active.is_(True),
    )
    return and_(active_owner, or_(team_id.is_(None), active_membership))

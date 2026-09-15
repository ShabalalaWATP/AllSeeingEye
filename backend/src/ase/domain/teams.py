"""Team identity and explicit memberships, independent of global account roles."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from ase.domain.users import Role


class MembershipRole(StrEnum):
    MEMBER = "member"
    MANAGER = "manager"


@dataclass(slots=True)
class Team:
    id: UUID
    name: str
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    description: str | None = None


@dataclass(frozen=True, slots=True)
class TeamMembership:
    team_id: UUID
    user_id: UUID
    role: MembershipRole
    joined_at: datetime


@dataclass(frozen=True, slots=True)
class TeamMember:
    """The intentionally limited identity information exposed in an authorised roster."""

    user_id: UUID
    display_name: str
    account_role: Role
    is_active: bool
    role: MembershipRole
    joined_at: datetime
    # Directory handle only. Login email is never part of a team roster.
    username: str | None = None

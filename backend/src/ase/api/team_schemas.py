"""Bounded team inputs and deliberately limited roster outputs."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from ase.domain.teams import MembershipRole
from ase.domain.users import Role

TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class TeamIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: TeamName


class TeamUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: TeamName | None = None
    is_active: bool | None = None


class MemberIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=320)
    role: MembershipRole = MembershipRole.MEMBER


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class TeamsOut(BaseModel):
    items: list[TeamOut]


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    email: str
    display_name: str
    account_role: Role
    is_active: bool
    role: MembershipRole
    joined_at: datetime


class TeamDetailOut(BaseModel):
    team: TeamOut
    members: list[MemberOut]


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    team_id: UUID
    user_id: UUID
    role: MembershipRole
    joined_at: datetime

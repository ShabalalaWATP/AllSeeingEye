"""Authorisation rules, checked in the application layer regardless of the route."""

from __future__ import annotations

from uuid import UUID

from ase.domain.errors import Forbidden, SelfModification
from ase.domain.users import User


def require_admin(actor: User) -> None:
    if not actor.is_admin:
        raise Forbidden()


def forbid_self_modification(actor: User, target_id: UUID) -> None:
    if actor.id == target_id:
        raise SelfModification()

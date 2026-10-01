"""Bell change frames reach only their recipients or current readers, and carry no content."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ase.api.stream_bell import bell_payload
from ase.application.access import AccessContext
from ase.application.ports.feeds import BusMessage
from ase.domain.bell import BELL_CHANGED
from ase.domain.teams import MembershipRole
from ase.domain.users import Role, User

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def _user(role: Role = Role.USER) -> User:
    return User(
        id=uuid4(),
        email="reader@example.com",
        display_name="Reader",
        role=role,
        is_active=True,
        password_hash=None,
        failed_login_count=0,
        last_failed_at=None,
        locked_until=None,
        created_at=NOW,
        last_login_at=None,
    )


async def test_targeted_bell_changes_reach_only_named_accounts_without_reading_access() -> None:
    reader, other = _user(), _user()
    reads = 0

    async def access() -> AccessContext | None:
        nonlocal reads
        reads += 1
        return None

    message = BusMessage(BELL_CHANGED, {"user_ids": frozenset({reader.id})})
    assert await bell_payload(message, reader.id, access) == {}
    assert await bell_payload(message, other.id, access) is None
    assert reads == 0


async def test_scoped_bell_changes_re_read_access_before_release() -> None:
    reader = _user()
    team = uuid4()
    member = AccessContext(reader, {}, {team: MembershipRole.MEMBER})
    current: AccessContext | None = member

    async def access() -> AccessContext | None:
        return current

    shared = BusMessage(BELL_CHANGED, {"scope": (uuid4(), team)})
    private = BusMessage(BELL_CHANGED, {"scope": (uuid4(), None)})
    own = BusMessage(BELL_CHANGED, {"scope": (reader.id, None)})
    assert await bell_payload(shared, reader.id, access) == {}
    assert await bell_payload(private, reader.id, access) is None
    assert await bell_payload(own, reader.id, access) == {}
    current = AccessContext(reader, {}, {})
    assert await bell_payload(shared, reader.id, access) is None
    current = None
    assert await bell_payload(own, reader.id, access) is None
    malformed = BusMessage(BELL_CHANGED, {"scope": "everyone"})
    assert await bell_payload(malformed, reader.id, access) is None

"""Authorise a content-free bell change frame for one open stream.

A frame says only that the reader's bell may have changed. The browser then refetches
through the fenced bell endpoints, which re-check access, so no title, snippet or count
travels on the stream. Targeted signals name recipients; scoped signals re-read access
like alerts and apply the bell's own scope, so a queued frame never borrows authority
from before an access change.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from ase.application.access import AccessContext
from ase.application.bell.scope import in_bell_scope
from ase.application.ports.feeds import BusMessage

AccessReader = Callable[[], Awaitable[AccessContext | None]]


async def bell_payload(
    message: BusMessage, user_id: UUID, read_access: AccessReader
) -> dict[str, Any] | None:
    targets = message.payload.get("user_ids")
    if isinstance(targets, frozenset):
        return {} if user_id in targets else None
    scope = message.payload.get("scope")
    if not isinstance(scope, tuple) or len(scope) != 2:
        return None
    created_by, team_id = scope
    access = await read_access()
    if access is None:
        return None
    # The bell's own scope, so an administrator is not woken for every team's change.
    return {} if in_bell_scope(access, created_by, team_id) else None

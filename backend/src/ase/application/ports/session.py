"""Session re-validation seams between use cases, the delivery layer and persistence."""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

# Re-validates the caller's session and raises Unauthenticated once it has ended.
# Use cases call it after private reads or external work, before persisting or
# releasing protected material. The HTTP layer supplies SessionFence.confirm.
SessionCheck = Callable[[], Awaitable[None]]

# Bus message kind that wakes open streams after a committed session change.
SESSION_CHANGED = "session.changed"


class SessionSignals(Protocol):
    """Committed changes to a user's sessions or access: revocation, security version,
    role, activation, team membership or team state."""

    def publish(self, user_id: UUID) -> None:
        """Record a committed change; call only after the transaction has committed."""
        ...

    def changed_since(self, user_id: UUID, moment: datetime) -> bool:
        """Whether a change for this user was published at or after `moment`."""
        ...

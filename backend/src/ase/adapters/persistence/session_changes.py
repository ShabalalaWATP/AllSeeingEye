"""Signal committed session or access changes: revocations, security version, role,
activation, team membership or team state.

Writers mark the affected user on their transaction; the marks are published only
after that transaction commits, so a rolled-back change never ends a session early and
a re-read can never observe the old state after the signal. Session factories carry
the signals under SIGNALS_KEY; sessions without them publish nothing.
"""

from uuid import UUID
from weakref import WeakKeyDictionary

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ase.application.ports.session import SessionSignals

SIGNALS_KEY = "ase.session_signals"
_pending: WeakKeyDictionary[Session, set[UUID]] = WeakKeyDictionary()


def mark_session_change(session: AsyncSession, user_id: UUID) -> None:
    _pending.setdefault(session.sync_session, set()).add(user_id)


@event.listens_for(Session, "after_commit")
def _publish(session: Session) -> None:
    changed = _pending.pop(session, None)
    signals: SessionSignals | None = session.info.get(SIGNALS_KEY)
    if changed and signals is not None:
        for user_id in changed:
            signals.publish(user_id)


@event.listens_for(Session, "after_rollback")
def _discard(session: Session) -> None:
    _pending.pop(session, None)

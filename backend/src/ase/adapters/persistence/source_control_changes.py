"""Version committed source-control writes so in-process admission caches can reload.

Any ORM insert, update or delete of a source-control row marks its session. The
process-wide version advances only after that transaction commits or rolls back,
so a reader that observes the new version always queries post-commit state. A
read that started before the change sees the version move and must not cache its
result. The configured deployment is one API process; writes from elsewhere are
bounded by the admission cache's time-to-live instead.
"""

from typing import Any
from weakref import WeakSet

from sqlalchemy import event
from sqlalchemy.orm import Mapper, Session, object_session

from ase.adapters.persistence.source_control_models import SourceControlRow

_pending: WeakSet[Session] = WeakSet()
_version = [0]


def source_control_version() -> int:
    return _version[0]


@event.listens_for(SourceControlRow, "after_insert")
@event.listens_for(SourceControlRow, "after_update")
@event.listens_for(SourceControlRow, "after_delete")
def _mark(_mapper: Mapper[Any], _connection: Any, target: SourceControlRow) -> None:
    session = object_session(target)
    if session is not None:
        _pending.add(session)


@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def _advance(session: Session) -> None:
    # A rollback also advances: a shared-connection reader may have seen the
    # uncommitted row, and reloading after the rollback is always safe.
    if session in _pending:
        _pending.discard(session)
        _version[0] += 1

"""Database sessions, their change signals and the freshness cache fences and streams share."""

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.persistence.session import create_session_factory
from ase.adapters.security.session_signals import InMemorySessionSignals
from ase.application.auth.session_freshness import SessionFreshness
from ase.application.ports import Clock
from ase.application.ports.feeds import BusMessage
from ase.application.ports.session import SESSION_CHANGED
from ase.infrastructure.settings import Settings


def build_sessions(
    settings: Settings, clock: Clock, bus: InMemoryEventBus, engine: AsyncEngine
) -> tuple[InMemorySessionSignals, SessionFreshness, async_sessionmaker[AsyncSession]]:
    def wake(user_id: UUID) -> None:
        # Open streams re-check at once instead of at their next periodic check.
        bus.publish_nowait(BusMessage(SESSION_CHANGED, {"user_id": user_id}))

    signals = InMemorySessionSignals(clock, notify=wake)
    freshness = SessionFreshness(
        clock, signals, timedelta(seconds=settings.session_recheck_seconds)
    )
    return signals, freshness, create_session_factory(engine, signals=signals)

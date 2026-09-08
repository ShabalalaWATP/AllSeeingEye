"""Position estimates have shorter useful lifetimes than their broad event categories."""

from datetime import UTC, datetime, timedelta

from ase.application.feeds.budgets import SATELLITE_POSITION_AGE
from ase.domain.events import Category, Event


def satellite_position_expired(event: Event, now: datetime) -> bool:
    if event.category is not Category.SPACE or event.subtype != "satellite":
        return False
    value = event.attributes.get("position_at")
    position_at = event.published_at
    if value is not None:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            position_at = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
        except ValueError:
            return True
    return (
        position_at is None
        or position_at < now - SATELLITE_POSITION_AGE
        or position_at > now + timedelta(minutes=1)
    )

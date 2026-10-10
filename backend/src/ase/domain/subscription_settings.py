"""Optimistic edit identity, independent of subscription activity and pause controls."""

import json
from dataclasses import asdict
from hashlib import sha256

from ase.domain.schedules import Schedule


def settings_revision(schedule: Schedule) -> str:
    """Bind editable settings to their exact subscription, scope and pinned brief."""
    value = {
        "id": str(schedule.id),
        "owner": str(schedule.created_by),
        "team": str(schedule.team_id) if schedule.team_id else None,
        "brief": str(schedule.brief_id) if schedule.brief_id else None,
        "brief_revision": schedule.brief_revision,
        "name": schedule.name,
        "recurrence": asdict(schedule.recurrence),
    }
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

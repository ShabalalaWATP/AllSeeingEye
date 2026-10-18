"""Synthetic rows for expiry contracts, usable on either disposable database."""

from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.selected_index_models import (
    SelectedIndexGateRow,
    SelectedIndexRecordRow,
)
from test_selected_subscription_index import _schedule


async def selected_scope(container, user):
    identifier = uuid4()
    async with container.session_factory() as session:
        session.add(_schedule(identifier, user.id))
        session.add(SelectedIndexGateRow(id=1, revision=0))
        await session.commit()
    return identifier


def selected_row(identifier, owner, number, now, **values):
    fields = {
        "id": number,
        "subscription_id": identifier,
        "owner_id": owner,
        "source_id": "usgs",
        "item_key": str(number),
        "origin_key": str(number),
        "source_version": "v1",
        "title": "Synthetic public observation",
        "content_sha256": "a" * 64,
        "fingerprint": f"{number:064x}",
        "policy_id": "usgs-public-v1",
        "retention_days": 30,
        "stored_bytes": 400,
        "retrieved_at": now,
        "first_seen_at": now - timedelta(days=30),
        "expires_at": now,
    }
    return SelectedIndexRecordRow(**(fields | values))


async def seed(container, *rows):
    async with container.session_factory() as session:
        session.add_all(rows)
        await session.commit()

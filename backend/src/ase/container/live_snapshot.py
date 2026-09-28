"""Wire the disposable live-store snapshot (ADR 0022); None when it is disabled."""

from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta
from typing import TYPE_CHECKING

from ase.adapters.store.snapshot_file import GzipSnapshotFile
from ase.application.feeds.budgets import DEFAULT_BUDGETS
from ase.application.feeds.live_snapshot import LiveStoreSnapshots

if TYPE_CHECKING:
    from ase.container import Container

MIB = 1024 * 1024


def build_live_snapshot(container: Container) -> LiveStoreSnapshots | None:
    settings = container.settings
    path = settings.live_snapshot_file
    if path is None:
        return None
    # A key derived from the API's signing secret under its own label: only this
    # installation can write a snapshot it will reload, and the secret itself is not reused.
    key = hmac.new(
        settings.jwt_secret_value.encode("utf-8"), b"ase-live-store-snapshot-v1", hashlib.sha256
    ).digest()
    storage = GzipSnapshotFile(
        path,
        key=key,
        max_bytes=settings.live_snapshot_max_mb * MIB,
        # Encoded records are smaller than the store's conservative memory estimate.
        max_decompressed_bytes=settings.live_store_memory_mb * MIB,
        max_events=sum(budget.max_items for budget in DEFAULT_BUDGETS.values()),
    )
    return LiveStoreSnapshots(
        container.store,
        storage,
        container.clock,
        interval=timedelta(seconds=settings.live_snapshot_interval_seconds),
    )

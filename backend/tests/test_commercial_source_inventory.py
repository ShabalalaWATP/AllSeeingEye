"""Licence refusals must not look like healthy feeds or an administrator toggle."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.cisa_kev import SPEC
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.source_inventory import ConnectionState, SourceInventory
from ase.domain.source_licences import LICENCE_UNAVAILABLE, SourceLicence, SourceLicencePolicy


@pytest.mark.parametrize(
    "commercial,acknowledged,blocked",
    [(False, False, False), (True, False, True), (True, True, False)],
)
async def test_inventory_describes_effective_licence_admission(
    commercial: bool, acknowledged: bool, blocked: bool
) -> None:
    health = HealthRegistry()
    health.get(SPEC.id).status = SourceStatus.HEALTHY
    # Even an administrator-enabled source with old healthy records is unavailable.
    admission = SimpleNamespace(enabled_many=AsyncMock(return_value={SPEC.id: True}))
    licence = SourceLicence(SPEC.id, "licence_required", True, "docs/SOURCE_LICENCES.md")
    policy = SourceLicencePolicy(
        [licence],
        commercial_use=commercial,
        acknowledgements=frozenset({SPEC.id}) if acknowledged else frozenset(),
    )
    inventory = SourceInventory(
        [SimpleNamespace(spec=SPEC)], [], [], {}, health, admission, licence_policy=policy
    )
    [row] = await inventory.list()
    if blocked:
        assert row.connection.state is ConnectionState.DISABLED_BY_LICENCE
        assert row.connection.detail == LICENCE_UNAVAILABLE
        assert row.connection.enabled is row.connection.active is False
        assert row.connection.health is None
    else:
        assert row.connection.state is ConnectionState.CONNECTED
        assert row.connection.enabled is row.connection.active is True

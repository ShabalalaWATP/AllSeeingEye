"""Radar research needs both a configured token and an explicit licence decision."""

import pytest

from ase.container.source_requirements import source_requirements
from ase.domain.source_controls import source_control_keys
from ase.infrastructure.settings import Settings


@pytest.mark.parametrize(
    "token,ack,expected",
    [
        (None, False, False),
        ("fixture-token", False, False),
        (None, True, False),
        ("fixture-token", True, True),
    ],
)
def test_research_radar_requires_token_and_noncommercial_acknowledgement(
    token: str | None, ack: bool, expected: bool
) -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        cloudflare_radar_token=token,
        cloudflare_radar_noncommercial_use_acknowledged=ack,
    )
    requirements = source_requirements(settings)
    for source_id in (
        "research-cloudflare-radar-layer3",
        "research-cloudflare-radar-layer7",
    ):
        assert requirements[source_id].satisfied is expected
        assert requirements[source_id].kind == "acknowledgement"
        assert source_control_keys(source_id) == (source_id, "cloudflare_radar_attack_trends")
        assert "fixture-token" not in repr(requirements[source_id])

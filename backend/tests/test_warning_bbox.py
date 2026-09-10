"""Area indicators use the same inclusive, dateline-aware bounds as map queries."""

from dataclasses import replace

import pytest

from ase.domain.events import BoundingBox, Point
from ase.domain.warning import evaluate
from test_warning import NOW, indicator
from tracker_helpers import conflict_events


@pytest.mark.parametrize(
    ("lon", "lat", "matches"),
    [
        (175, 0, True),
        (-175, 0, True),
        (170, -10, True),
        (-170, 10, True),
        (180, 0, True),
        (-180, 0, True),
        (0, 0, False),
        (175, 11, False),
    ],
)
def test_dateline_indicator_matches_both_sides(lon: float, lat: float, matches: bool) -> None:
    rule = indicator(bbox=BoundingBox(170, -10, -170, 10), countries=(), keywords=())
    event = replace(conflict_events(NOW)[0], point=Point(lon, lat), published_at=NOW)
    assert rule.matches(event) is matches
    assert (evaluate(rule, [event], NOW, None) is not None) is matches


def test_bounds_require_a_point_and_take_priority_over_country() -> None:
    rule = indicator(bbox=BoundingBox(-5, 50, 5, 60), countries=("UA",), keywords=())
    event = replace(conflict_events(NOW)[0], country_iso="UA", point=None)
    assert not rule.matches(event)
    assert not rule.matches(replace(event, point=Point(10, 55)))
    assert rule.matches(replace(event, country_iso="GB", point=Point(-5, 50)))

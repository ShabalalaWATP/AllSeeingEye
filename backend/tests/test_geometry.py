"""Ray casting on longitude and latitude rings, with holes and degenerate input."""

from __future__ import annotations

from ase.domain.geometry import bounds_contain, point_in_polygon, point_in_ring, ring_bounds

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
HOLE = [(4.0, 4.0), (6.0, 4.0), (6.0, 6.0), (4.0, 6.0)]
CONCAVE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (5.0, 5.0), (0.0, 10.0)]


def test_ring_membership() -> None:
    assert point_in_ring(5.0, 5.0, SQUARE)
    assert not point_in_ring(15.0, 5.0, SQUARE)
    assert not point_in_ring(5.0, -1.0, SQUARE)
    assert point_in_ring(1.0, 8.0, CONCAVE)
    assert not point_in_ring(5.0, 8.0, CONCAVE)  # inside the notch
    assert not point_in_ring(1.0, 1.0, [(0.0, 0.0), (1.0, 1.0)])  # not a polygon


def test_polygon_with_holes() -> None:
    assert point_in_polygon(2.0, 2.0, [SQUARE, HOLE])
    assert not point_in_polygon(5.0, 5.0, [SQUARE, HOLE])
    assert not point_in_polygon(5.0, 5.0, [])
    assert not point_in_polygon(50.0, 50.0, [SQUARE])


def test_bounds() -> None:
    bounds = ring_bounds(CONCAVE)
    assert bounds == (0.0, 0.0, 10.0, 10.0)
    assert bounds_contain(bounds, 10.0, 0.0)
    assert not bounds_contain(bounds, 10.1, 0.0)

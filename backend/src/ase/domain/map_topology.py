"""Conservative planar polygon validation with a shared bounded predicate budget.

Counting matches the frontend: charge one per ring edge (area/duplicate/wrap
checks), one per nonadjacent segment-pair intersection test, one per point-in-ring
iteration (including the repeated closing position), and one per hole/earlier-ring
segment pair. Intersection internals are a constant-cost predicate, not additional
charges. Charge before work; the 1,000,001st check fails. Hole containment tests
short-circuit in input order. The same counter spans every polygon in an upload.
"""

from dataclasses import dataclass
from itertools import pairwise

Position = tuple[float, float]
Ring = tuple[Position, ...]
MAX_POLYGON_VERTICES = 256
MAX_TOPOLOGY_CHECKS = 1_000_000
EPSILON = 1e-10


@dataclass(slots=True)
class TopologyBudget:
    checks: int = 0

    def charge(self) -> None:
        if self.checks >= MAX_TOPOLOGY_CHECKS:
            raise ValueError("Geometry topology exceeds its work limit. Simplify the geometry.")
        self.checks += 1


def _side(a: Position, b: Position, c: Position) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Position, b: Position, c: Position) -> bool:
    return (
        abs(_side(a, b, c)) < EPSILON
        and min(a[0], b[0]) <= c[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
    )


def _crosses(a: Position, b: Position, c: Position, d: Position) -> bool:
    return (
        (_side(a, b, c) * _side(a, b, d) < 0 and _side(c, d, a) * _side(c, d, b) < 0)
        or _on_segment(a, b, c)
        or _on_segment(a, b, d)
        or _on_segment(c, d, a)
        or _on_segment(c, d, b)
    )


def _inside(point: Position, ring: Ring, budget: TopologyBudget) -> bool:
    result = False
    for index, a in enumerate(ring):
        budget.charge()
        b = ring[index - 1]
        if (a[1] > point[1]) != (b[1] > point[1]) and (
            point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]
        ):
            result = not result
    return result


def _validate_ring(ring: Ring, budget: TopologyBudget) -> None:
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError("Polygon rings need at least four positions and must be closed.")
    area = 0.0
    for index, (a, b) in enumerate(pairwise(ring)):
        budget.charge()
        if abs(a[0] - b[0]) > 180:
            raise ValueError("Polygon crosses the antimeridian. Supply a pre-split MultiPolygon.")
        if a == b:
            raise ValueError("Polygon contains duplicate consecutive positions.")
        area += a[0] * b[1] - b[0] * a[1]
        for other in range(index + 2, len(ring) - 1):
            if index == 0 and other == len(ring) - 2:
                continue
            budget.charge()
            if _crosses(a, b, ring[other], ring[other + 1]):
                raise ValueError("Polygon ring intersects itself.")
    if abs(area) < EPSILON:
        raise ValueError("Polygon has no supported area.")


def validate_polygon(rings: tuple[Ring, ...], budget: TopologyBudget) -> None:
    """Preserve winding; allow only simple outer rings and contained disjoint holes.

    Each MultiPolygon component is validated independently, matching the display
    importer. This does not claim that distinct features/components are disjoint.
    """
    if not rings or sum(map(len, rings)) > MAX_POLYGON_VERTICES:
        raise ValueError("Each polygon is limited to 256 vertices. Simplify the geometry.")
    for ring in rings:
        _validate_ring(ring, budget)
    for index, hole in enumerate(rings[1:], 1):
        if not _inside(hole[0], rings[0], budget):
            raise ValueError("Polygon hole lies outside its outer ring.")
        for earlier, other in enumerate(rings[:index]):
            if earlier > 0 and (_inside(hole[0], other, budget) or _inside(other[0], hole, budget)):
                raise ValueError("Nested or overlapping polygon holes are unsupported.")
            for a, b in pairwise(hole):
                for c, d in pairwise(other):
                    budget.charge()
                    if _crosses(a, b, c, d):
                        raise ValueError("Polygon rings touch or intersect.")

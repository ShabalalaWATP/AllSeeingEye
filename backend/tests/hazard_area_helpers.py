"""Deterministic source geometry and response fixtures for area hazard collection."""

import json
from datetime import timedelta

from ase.domain.map_geometry import parse_map_geometry
from ase.domain.research import ResearchQuery
from ase.domain.research_area import ResearchArea
from research_feed_helpers import NOW

RING = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]


def area(coordinates=None, kind="Polygon"):
    return ResearchArea(
        parse_map_geometry(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {"type": kind, "coordinates": coordinates or [RING]},
                        }
                    ],
                }
            )
        )
    )


QUERY = ResearchQuery(
    "Private question that must not be transmitted",
    since=NOW - timedelta(days=1),
    until=NOW,
    area=area(),
    terms=("private phrase",),
)
ACQUIRED = NOW - timedelta(hours=1)
ACQUIRED_TEXT = ACQUIRED.isoformat()


def earthquake(key="one", coordinates=None, acquired=ACQUIRED, **props):
    return {
        "type": "Feature",
        "id": key,
        "geometry": {"type": "Point", "coordinates": coordinates or [2, 2, 5]},
        "properties": {
            "type": "earthquake",
            "time": int(acquired.timestamp() * 1000),
            "mag": 4.2,
            "place": "Test epicentre",
            "url": "https://earthquake.usgs.gov/earthquakes/eventpage/one",
            "status": "reviewed",
            **props,
        },
    }


def observation(coordinates=None, date=ACQUIRED_TEXT, kind="Point"):
    return {"type": kind, "coordinates": coordinates or [2, 2], "date": date}


def hazard(key="EONET_1", geometry=None, **extra):
    return {
        "id": key,
        "title": "Test fire",
        "categories": [{"id": "wildfires", "title": "Wildfires"}],
        "sources": [{"id": "InciWeb", "url": "https://inciweb.wildfire.gov/incident/test"}],
        "geometry": geometry if geometry is not None else [observation()],
        "closed": None,
        **extra,
    }

"""Energy and semiconductor site imports and infrastructure enrichment parse bounded records."""

from __future__ import annotations

from typing import Any

from ase.adapters.geo import infrastructure_import as infra
from ase.adapters.geo import infrastructure_notes as notes
from ase.adapters.geo import sites_import as sites
from ase.adapters.geo.countries import CountryIndex, load_records
from ase.adapters.geo.infrastructure import public_infrastructure
from ase.adapters.geo.sites_osm import parse_osm_sites, wikipedia_url
from ase.adapters.wikidata_entities import EntityFacts
from ase.api.schemas_infrastructure import InfrastructureOut


class FakeEntities:
    """Canned search hits and facts, standing in for the Wikidata entity API."""

    def __init__(self, hits: dict[str, list[tuple[str, str, str]]], facts: dict[str, EntityFacts]):
        self._hits, self._facts = hits, facts

    def search(self, text: str, limit: int = 5) -> list[tuple[str, str, str]]:
        return self._hits.get(text, [])[:limit]

    def facts(self, qids: list[str]) -> dict[str, EntityFacts]:
        return {qid: self._facts[qid] for qid in qids if qid in self._facts}


def fact(qid: str, label: str, coords: tuple[float, float] | None, **extra: Any) -> EntityFacts:
    base: dict[str, Any] = {
        "qid": qid,
        "label": label,
        "description": "",
        "coords": coords,
        "operators": (),
        "owners": (),
        "country": None,
        "website": None,
        "wikipedia": None,
    }
    base.update(extra)
    return EntityFacts(**base)


def test_packaged_site_layers_are_bounded_and_attributed() -> None:
    data = InfrastructureOut.model_validate(public_infrastructure())
    assert 50 <= len(data.semiconductor_sites) <= 300
    assert 500 <= len(data.energy_sites) <= 3200
    assert "OpenStreetMap" in data.site_attribution and "Wikidata" in data.site_attribution
    for site in [*data.semiconductor_sites[:60], *data.energy_sites[:200]]:
        assert site.source_url.startswith("https://")
        assert site.precision in {"site", "mapped", "city"}
        assert site.website is None or site.website.startswith("https://")
    curated = [s for s in data.energy_sites if s.significance]
    assert len(curated) >= 40
    assert any("Qatar" in (s.significance or "") for s in curated)
    assert any(s.kind == "fab" and s.significance for s in data.semiconductor_sites)
    chips = [s for s in data.semiconductor_sites if s.significance]
    assert all(s.detail for s in chips) and sum(1 for s in chips if s.links) >= 45
    assert sum(1 for s in chips if any("website" in link.label for link in s.links)) >= 40
    keyed = [c for c in data.data_centres if c.id.startswith("key-")]
    assert {c.country for c in keyed} >= {"RU", "CN", "KP"}
    assert all(c.significance and c.detail for c in keyed)
    assert sum(1 for c in keyed if c.links) >= 15
    stations = [s for s in data.ground_stations if s.id.startswith("key-")]
    assert {s.country for s in stations} >= {"RU", "CN", "KP"}
    assert all(s.role and s.significance and s.precision for s in stations)


def test_osm_sites_parse_names_operators_and_links() -> None:
    index = CountryIndex(load_records())
    elements = [
        {
            "type": "way",
            "id": 7,
            "center": {"lat": 51.45, "lon": -0.95},
            "tags": {
                "name": "Fawley",
                "name:en": "Fawley Refinery",
                "operator": "Esso",
                "wikipedia": "en:Fawley Refinery",
                "website": "https://example.org/fawley",
                "wikidata": "Q123",
            },
        },
        {"type": "node", "id": 8, "lat": 60.0, "lon": 2.0, "tags": {"name": "Troll A"}},
        {"type": "node", "id": 9, "lat": 60.0, "lon": 2.0, "tags": {}},
        {"type": "node", "id": 10, "lat": 91, "lon": 2.0, "tags": {"name": "Bad"}},
    ]
    parsed = parse_osm_sites(elements, "refinery", index)
    assert [s["id"] for s in parsed] == ["osm-way-7", "osm-node-8"]
    fawley = parsed[0]
    assert fawley["name"] == "Fawley Refinery" and fawley["country"] == "GB"
    assert fawley["wikipedia"] == "https://en.wikipedia.org/wiki/Fawley_Refinery"
    assert fawley["wikidata"] == "Q123" and fawley["precision"] == "mapped"
    assert parsed[1]["operator"] == "Operator not recorded" and parsed[1]["country"] is None
    assert wikipedia_url("de:Irgendwo") is None and wikipedia_url(None) is None


def test_seed_resolution_prefers_match_word_and_falls_back_to_city() -> None:
    entities = FakeEntities(
        {
            "Abqaiq": [
                ("Q1", "Abqaiq", "gated community"),
                ("Q2", "Abqaiq oil field", "oilfield in Saudi Arabia"),
            ],
            "ASML": [("Q3", "ASML", "Dutch company")],
            "Veldhoven": [("Q4", "Veldhoven", "town in the Netherlands")],
            "Nowhere": [],
        },
        {
            "Q2": fact("Q2", "Abqaiq oil field", (49.7, 25.9), operators=("Saudi Aramco",)),
            "Q3": fact("Q3", "ASML", None, owners=("Public",)),
            "Q4": fact("Q4", "Veldhoven", (5.4, 51.4)),
        },
    )
    site = sites.resolve_seed(
        {
            "search": "Abqaiq",
            "match": "oil",
            "kind": "processing_plant",
            "country": "SA",
            "significance": "x",
        },
        entities,  # type: ignore[arg-type]
        sites.ENERGY_WORDS,
    )
    assert site and site["id"] == "wd-q2" and site["precision"] == "site"
    assert site["operator"] == "Saudi Aramco" and site["name"] == "Abqaiq oil field"
    city = sites.resolve_seed(
        {
            "search": "ASML",
            "city": "Veldhoven",
            "kind": "equipment",
            "company": "ASML",
            "country": "NL",
        },
        entities,  # type: ignore[arg-type]
        ("semiconductor",),
    )
    assert city and city["precision"] == "city" and city["id"] == "seed-asml"
    assert (
        city["operator"] == "ASML" and city["wikidata"] is None and "not geolocated" in city["note"]
    )
    assert (
        sites.resolve_seed({"search": "Nowhere", "kind": "fab", "country": "XX"}, entities, ())
        is None
    )  # type: ignore[arg-type]
    merged = sites.merge_sites(
        [site],
        [
            {**site, "id": "osm-node-1", "significance": None},
            {**site, "id": "osm-node-2", "longitude": 10.0, "significance": None},
        ],
        10,
    )
    assert [s["id"] for s in merged] == ["wd-q2", "osm-node-2"]


def test_company_and_site_links_are_ordered_and_deduplicated() -> None:
    entities = FakeEntities(
        {"TSMC": [("Q1", "TSMC", "Taiwanese semiconductor company")]},
        {
            "Q1": fact(
                "Q1",
                "TSMC",
                None,
                website="https://www.tsmc.com/",
                wikipedia="https://en.wikipedia.org/wiki/TSMC",
            )
        },
    )
    links = sites.company_links({"company_search": "TSMC"}, entities)  # type: ignore[arg-type]
    assert [link["label"] for link in links] == ["TSMC website", "TSMC on Wikipedia"]
    assert sites.company_links({}, entities) == []  # type: ignore[arg-type]
    site = {
        "wikipedia": "https://en.wikipedia.org/wiki/TSMC",
        "website": None,
        "links": links,
        "source_url": "https://www.openstreetmap.org/way/5",
    }
    ordered = sites.site_links(site)
    assert [link["label"] for link in ordered] == [
        "Wikipedia",
        "TSMC website",
        "OpenStreetMap feature",
    ]


def test_curated_stations_carry_role_and_precision(monkeypatch) -> None:
    entities = FakeEntities(
        {
            "Okno": [("Q2", "Okno", "space surveillance complex in Tajikistan")],
            "Nurek": [("Q3", "Nurek", "city in Tajikistan")],
        },
        {"Q2": fact("Q2", "Okno", (69.2, 38.3), operators=("Russian Space Forces",))},
    )
    monkeypatch.setattr(infra.WikidataEntities, "open", classmethod(lambda cls, contact: entities))
    monkeypatch.setattr(entities, "close", lambda: None, raising=False)
    monkeypatch.setattr(
        infra,
        "_seeds",
        lambda name: [
            {
                "search": "Okno",
                "match": "Tajikistan",
                "city": "Nurek",
                "country": "TJ",
                "operator": "Russian Space Forces",
                "role": "space_surveillance",
                "significance": "Optical surveillance.",
                "detail": "Tracks satellites.",
            }
        ],
    )
    stations = infra.curated_stations("contact")
    assert len(stations) == 1
    station = stations[0]
    assert station["id"] == "key-wd-q2" and station["role"] == "space_surveillance"
    assert station["precision"] == "site" and station["country"] == "TJ"
    assert station["significance"] == "Optical surveillance." and station["detail"]


def test_cable_enrichment_uses_way_tags_then_wikidata() -> None:
    cables = [
        {"name": "CANTAT 3", "source_url": "https://www.openstreetmap.org/way/1"},
        {
            "name": "Mapped submarine cable segment",
            "source_url": "https://www.openstreetmap.org/way/2",
        },
        {"name": "Other", "source_url": "https://www.openstreetmap.org/way/3"},
    ]
    tags = {
        1: {"operator": "BT", "wikidata": "Q9", "wikipedia": "en:CANTAT-3"},
        3: {"website": "http://insecure.example"},
    }
    facts = {
        "Q9": fact(
            "Q9",
            "CANTAT-3",
            None,
            owners=("BT", "TDC"),
            description="cable",
            inception="1994-01-01",
        )
    }
    assert notes.enrich_cables(cables, tags, facts) == 1
    assert cables[0]["operator"] == "BT" and cables[0]["owner"] == "BT, TDC"
    assert cables[0]["wikipedia"] == "https://en.wikipedia.org/wiki/CANTAT-3"
    assert cables[0]["inception"] == "1994-01-01" and "website" not in cables[0]
    assert "website" not in cables[2]
    assert notes._way_ids(cables) == [1, 3]


def test_record_enrichment_requires_matching_kind_and_nearby_position() -> None:
    entities = FakeEntities(
        {
            "Atucha I Argentina": [
                ("Q8", "Atucha II Nuclear Power Plant", "nuclear power plant in Argentina"),
                ("Q5", "Atucha I", "nuclear power plant in Argentina"),
            ],
            "Far Plant Chile": [("Q6", "Far Plant", "nuclear power plant")],
            "Not a plant France": [("Q7", "Not a plant", "village")],
        },
        {
            "Q5": fact(
                "Q5",
                "Atucha I",
                (-59.2, -33.97),
                owners=("Nucleoeléctrica Argentina",),
                wikipedia="https://en.wikipedia.org/wiki/Atucha",
            ),
            "Q6": fact("Q6", "Far Plant", (10.0, 10.0)),
            "Q7": fact("Q7", "Not a plant", (2.0, 48.0)),
        },
    )
    records = [
        {"name": "Atucha I", "country": "Argentina", "longitude": -59.2059, "latitude": -33.967},
        {"name": "Far Plant", "country": "Chile", "longitude": -70.0, "latitude": -30.0},
        {"name": "Not a plant", "country": "France", "longitude": 2.0, "latitude": 48.0},
        {"id": "wd-q1", "name": "Done", "country": "X", "longitude": 0, "latitude": 0},
        {"name": "Stale", "country": "Y", "longitude": 0, "latitude": 0, "wikidata": "Q0"},
    ]
    changed = notes.enrich_records(records, entities, ("nuclear",))  # type: ignore[arg-type]
    assert changed == 1
    assert records[0]["owner"] == "Nucleoeléctrica Argentina" and records[0]["wikidata"] == "Q5"
    assert "wikidata" not in records[1] and "wikidata" not in records[2]
    assert "wikidata" not in records[3] and "wikidata" not in records[4]
    assert notes.label_fits("ATUCHA I", "Atucha I") and not notes.label_fits(
        "ATUCHA I", "Atucha II"
    )
    assert notes.label_fits("DOEL 4", "Doel Nuclear Power Station unit 4")
    assert not notes.label_fits("Goldstone Complex", "Madrid Complex")

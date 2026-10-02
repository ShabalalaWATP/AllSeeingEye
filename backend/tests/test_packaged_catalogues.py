"""The packaged JSON catalogues load, validate strictly and keep their invariants."""

from __future__ import annotations

import json
from importlib import resources

import pytest

from ase.adapters.feeds import rss_seeds, telegram_channels, youtube_channel_seeds
from ase.adapters.feeds.rss_sources import RSS_SEEDS
from ase.adapters.feeds.telegram_channels import TELEGRAM_CHANNELS
from ase.adapters.feeds.youtube_channel_seeds import CHANNELS
from ase.adapters.geo.camera_europe import curated
from ase.adapters.geo.camera_europe_catalogue import COUNTRIES, curated_rows, parse_rows
from ase.adapters.packaged_json import CatalogueError, fields, names, parse, text
from ase.container.research_allocation_profiles import research_allocation_profiles
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS

ROOT = resources.files("ase.resources")
CAMERA = {
    "id": "pl-test",
    "lat": 54.5,
    "lng": 18.5,
    "name": "Test",
    "city": "Gdynia",
    "country": "Poland",
    "stream_url": "https://ls.tkchopin.pl/live/a.m3u8",
    "stream_type": "hls",
    "source": "Test",
}


def packaged(folder: str, prefix: str) -> set[str]:
    return {
        entry.name.removesuffix(".json").removeprefix(prefix)
        for entry in ROOT.joinpath(folder).iterdir()
        if entry.name.startswith(prefix) and entry.name.endswith(".json")
    }


@pytest.mark.parametrize("country", COUNTRIES)
def test_camera_catalogues_load_with_unique_ids_and_build_every_camera(country):
    rows = curated_rows(country)
    assert rows
    assert len({row["id"] for row in rows}) == len(rows)
    assert all({"id", "lat", "lng", "name", "source"} <= row.keys() for row in rows)
    assert len(curated(country)) == len(rows)


def test_every_camera_file_is_listed_and_the_licence_notice_ships():
    assert packaged("cameras", "") == set(COUNTRIES)
    notice = ROOT.joinpath("cameras").joinpath("NOTICE.md").read_text("utf-8")
    assert "MIT License" in notice
    assert "Copyright (c) 2026 simplifaisoul" in notice
    assert "fac8d1b" in notice


def test_camera_records_keep_their_packaged_key_order():
    raw = json.loads(ROOT.joinpath("cameras").joinpath("bulgaria.json").read_text("utf-8"))
    assert [list(row) for row in curated_rows("bulgaria")] == [list(row) for row in raw]


@pytest.mark.parametrize("country", ["../italy", "open", "greece", "ITALY"])
def test_camera_loader_reads_only_listed_countries(country):
    with pytest.raises(ValueError, match="Unknown curated camera provider"):
        curated_rows(country)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"extra": "x"}, "unknown field"),
        ({"lat": "54.5"}, "finite number"),
        ({"lng": True}, "finite number"),
        ({"name": ""}, "non-empty text"),
        ({"stream_type": "rtsp"}, "stream_type"),
        ({"stream_url": "http://ls.tkchopin.pl/a.m3u8"}, "HTTPS URL"),
        ({"stream_url": "https://ls.tkchopin.pl@evil.example/a.m3u8"}, "plain host"),
    ],
)
def test_camera_loader_rejects_unreviewed_shapes(change, message):
    with pytest.raises(CatalogueError, match=message):
        parse_rows("poland", [{**CAMERA, **change}])


def test_camera_loader_rejects_missing_pairs_duplicates_and_empty_lists():
    lone = {key: value for key, value in CAMERA.items() if key != "stream_type"}
    with pytest.raises(CatalogueError, match="together"):
        parse_rows("poland", [lone])
    with pytest.raises(CatalogueError, match="missing city"):
        parse_rows("poland", [{key: value for key, value in CAMERA.items() if key != "city"}])
    with pytest.raises(CatalogueError, match="twice"):
        parse_rows("poland", [CAMERA, CAMERA])
    with pytest.raises(CatalogueError, match="list of 1 to"):
        parse_rows("poland", [])


def test_rss_groups_load_every_packaged_file_with_unique_ids():
    assert packaged("feeds", "rss_") == set(rss_seeds.GROUPS)
    groups = (
        rss_seeds.OFFICIAL_SEEDS,
        rss_seeds.OUTLET_SEEDS,
        rss_seeds.REGIONAL_SEEDS,
        rss_seeds.ECONOMY_SEEDS,
        rss_seeds.CYBER_SEEDS,
        rss_seeds.NEWS_SEEDS,
    )
    assert all(groups)
    assert tuple(seed for group in groups for seed in group) == RSS_SEEDS
    ids = [seed.spec.id for seed in RSS_SEEDS]
    assert len(ids) == len(set(ids)) == 151
    assert all(seed.spec.url.startswith("https://") for seed in RSS_SEEDS)
    assert all(seed.spec.rating is not None for seed in RSS_SEEDS)
    news = {seed.spec.id for seed in rss_seeds.NEWS_SEEDS}
    assert all(seed.spec.rating.provenance_role == "publisher" for seed in rss_seeds.NEWS_SEEDS)
    assert news.isdisjoint(seed.spec.id for group in groups[:-1] for seed in group)


def test_every_collection_seed_keeps_a_reviewed_research_profile_within_the_bound():
    profiles = research_allocation_profiles()
    publisher = (
        *rss_seeds.OFFICIAL_SEEDS,
        *rss_seeds.OUTLET_SEEDS,
        *rss_seeds.ECONOMY_SEEDS,
        *rss_seeds.CYBER_SEEDS,
    )
    assert {f"research_publisher_{seed.spec.id}" for seed in publisher} <= profiles.keys()
    assert {f"research_regional_{seed.spec.id}" for seed in rss_seeds.REGIONAL_SEEDS} <= (
        profiles.keys()
    )
    assert len(profiles) <= MAX_COLLECTION_PROVIDERS


def test_rss_option_presets_are_named_per_group():
    assert rss_seeds.US_ADVISORY.country_category_domain == "Country-Tag"
    assert set(rss_seeds.OPTION_PRESETS) == set(rss_seeds.GROUPS)


def rss_group(**change):
    seed = {
        "id": "test_feed",
        "name": "Test feed",
        "organisation": "Test",
        "category": "news",
        "url": "https://example.org/feed.xml",
        "homepage": "https://example.org/",
        "reliability": "F",
        "poll_minutes": 30,
        "language": "en",
        "options": "base",
        "licence": "terms",
        "flags": [],
        **change,
    }
    options = {
        "subtype": "article",
        "tags": [],
        "credibility": "cannot_be_judged",
        "rationale": "Test rationale",
        "headlines_only": True,
        "newest_first": False,
    }
    return {
        "about": ["Test."],
        "licences": {"terms": "Terms"},
        "options": {"base": options},
        "seeds": [seed],
    }


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"unexpected": 1}, "unknown field"),
        ({"category": "gossip"}, "category"),
        ({"reliability": "Z"}, "reliability"),
        ({"url": "http://example.org/feed.xml"}, "HTTPS URL"),
        ({"url": "https://user:secret@example.org/feed.xml"}, "plain host"),
        ({"url": "https://[::1/feed.xml"}, "HTTPS URL"),
        ({"poll_minutes": "30"}, "whole number"),
        ({"options": "missing"}, "options"),
        ({"flags": ["Upper"]}, "lower-case name"),
        ({"language": "english"}, "language code"),
    ],
)
def test_rss_loader_rejects_unreviewed_rows(monkeypatch, change, message):
    monkeypatch.setattr(rss_seeds, "load_resource", lambda *_: rss_group(**change))
    with pytest.raises(CatalogueError, match=message):
        rss_seeds._load("official")


def test_rss_loader_builds_a_row_and_refuses_unused_presets(monkeypatch):
    monkeypatch.setattr(rss_seeds, "load_resource", lambda *_: rss_group(rating_scope="Test."))
    ((seed,), presets) = rss_seeds._load("official")
    assert seed.spec.id == "test_feed" and seed.spec.rating.scope.startswith("Test.")
    assert presets["base"].headlines_only
    unused = rss_group()
    unused["licences"]["spare"] = "Spare"
    monkeypatch.setattr(rss_seeds, "load_resource", lambda *_: unused)
    with pytest.raises(CatalogueError, match="not used"):
        rss_seeds._load("official")


def test_telegram_areas_load_every_packaged_file_with_unique_channels():
    assert packaged("feeds", "telegram_") == set(telegram_channels.AREAS)
    assert TELEGRAM_CHANNELS
    usernames = [entry.username.casefold() for entry in TELEGRAM_CHANNELS]
    assert len(usernames) == len(set(usernames))


def test_telegram_loader_rejects_unreviewed_rows(monkeypatch):
    row = {
        "username": "test_channel",
        "name": "Test",
        "operator": "Test operator",
        "topic": "cyber_threat",
        "reason": "A stated reason that is long enough.",
        "viewpoint": "observer",
        "alignment": "",
        "language": "en",
        "poll_minutes": 60,
    }
    data = {"about": ["Test."], "groups": [{"group": "test", "channels": [row]}]}
    monkeypatch.setattr(telegram_channels, "load_resource", lambda *_: data)
    with pytest.raises(CatalogueError, match="viewpoint"):
        telegram_channels._area("world")
    row["viewpoint"] = "publisher"
    assert telegram_channels._area("world")[0].source_id == "telegram_test_channel"


def test_youtube_channels_load_with_unique_identities():
    assert youtube_channel_seeds.load_channels() == CHANNELS
    assert CHANNELS
    assert len({channel.source_id for channel in CHANNELS}) == len(CHANNELS)


def test_youtube_loader_rejects_unreviewed_rows(monkeypatch):
    row = {
        "source_id": "yt_test",
        "name": "Test",
        "organisation": "Test",
        "handle": "@TestChannel",
        "topics": ["world_news"],
        "reliability": "C",
        "kind": "influencer",
        "state_aligned": False,
        "language": "en",
        "poll_minutes": 30,
    }
    data = {"about": ["Test."], "groups": [{"group": "test", "about": "Test.", "channels": [row]}]}
    monkeypatch.setattr(youtube_channel_seeds, "load_resource", lambda *_: data)
    with pytest.raises(CatalogueError, match="kind"):
        youtube_channel_seeds._read()
    row["kind"] = "outlet"
    assert youtube_channel_seeds._read()[0].topics == ("world_news",)


def test_strict_json_helpers_refuse_duplicates_and_loose_text():
    with pytest.raises(CatalogueError, match="duplicate key 'a'"):
        parse("test.json", '{"a": 1, "a": 2}')
    with pytest.raises(CatalogueError, match="not valid JSON"):
        parse("test.json", "{")
    with pytest.raises(CatalogueError, match="expected an object"):
        fields("test", [], ("a",))
    with pytest.raises(CatalogueError, match="surrounding space"):
        text("test", " padded ")
    with pytest.raises(CatalogueError, match="listed twice"):
        names("test", ["a", "a"])

"""Social listening: Mastodon hashtags and language detection."""

# ruff: noqa: RUF001 (Ukrainian samples are the point)

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ase.adapters.feeds.http_contracts import FeedHttpStatusError
from ase.adapters.feeds.mastodon import MastodonConnector, spec_for
from ase.adapters.feeds.mastodon_watch import (
    DEFAULT_POLL_MINUTES,
    MAX_DISTINCT_TAGS,
    MAX_INSTANCES,
    MAX_TAGS_PER_INSTANCE,
    InstanceWatch,
    load_watch,
    parse_watch,
    watch_host_intervals,
    watch_terms,
)
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.translate.language import LangidDetector, NullDetector
from ase.application.feeds.language import LanguageStage
from ase.application.feeds.pipeline import strip_html
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.social import MAX_TERMS
from feeds_helpers import FakeClock, FakeHttp, load_fixture, make_event

NOW = datetime(2026, 9, 5, 22, 30, tzinfo=UTC)


async def test_mastodon_hashtag_posts_become_social_events() -> None:
    http = FakeHttp({"timelines/tag/ukraine": load_fixture("mastodon_tag.json")})
    connector = MastodonConnector(http, FakeClock(NOW), "mastodon.social", ["#Ukraine", " "])  # type: ignore[arg-type]
    assert connector.spec.id == "mastodon_mastodon_social"
    assert connector.spec.reliability is Reliability.E and connector.spec.language == "und"
    events = await connector.fetch()
    assert http.requests == ["https://mastodon.social/api/v1/timelines/tag/ukraine?limit=40"]
    assert len(events) == 3
    raw = load_fixture("mastodon_tag.json")[0]
    first = events[0]
    assert first.category is Category.SOCIAL and first.subtype == "post"
    assert first.credibility is Credibility.CANNOT_BE_JUDGED
    plain = strip_html(raw["content"]) or ""
    assert first.title.startswith(plain[:20]) and len(first.title) <= 140
    assert first.summary == plain[:2_000] and "<" not in first.summary
    assert first.url.startswith("https://") and first.language == raw["language"]
    assert {"mastodon", *(tag["name"].lower() for tag in raw["tags"])} <= first.tags
    assert first.attributes["account"] == raw["account"]["acct"]
    assert first.published_at == datetime.fromisoformat(raw["created_at"].replace("Z", "+00:00"))
    # The same post seen under two tags is one event.
    twice = MastodonConnector(
        FakeHttp({"timelines/tag/": load_fixture("mastodon_tag.json")}),
        FakeClock(NOW),
        "mastodon.social",
        ["ukraine", "osint"],
    )  # type: ignore[arg-type]
    assert len(await twice.fetch()) == 3
    assert (
        MastodonConnector(FakeHttp(not_modified=True), FakeClock(NOW), "x.social", ["a"]).spec.id
        == "mastodon_x_social"
    )  # type: ignore[arg-type]
    assert (
        await MastodonConnector(
            FakeHttp(not_modified=True), FakeClock(NOW), "x.social", ["a"]
        ).fetch()
        == []
    )  # type: ignore[arg-type]


def test_social_sources_are_registered_without_the_retired_scraped_feeds() -> None:
    """Reddit and the YouTube channel Atom feeds are disallowed by both hosts' robots.txt."""
    connectors = build_connectors(FakeHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    ids = {connector.spec.id for connector in connectors}
    urls = {connector.spec.url or "" for connector in connectors}
    assert "mastodon_mastodon_social" in ids
    assert {f"mastodon_{w.instance.replace('.', '_')}" for w in load_watch()} <= ids
    assert not any(id_.startswith("reddit_") for id_ in ids)
    assert not any("reddit.com" in url for url in urls)
    assert not any("/feeds/videos.xml" in url for url in urls)
    assert spec_for("masto.ai").homepage == "https://masto.ai/"


class FakeDetector:
    def __init__(self) -> None:
        self.samples: list[str] = []

    def detect(self, text: str) -> str | None:
        self.samples.append(text)
        return "uk" if "Київ" in text else None


def test_language_stage_fills_only_unknown_languages() -> None:
    detector = FakeDetector()
    stage = LanguageStage(detector)
    tagged = replace(make_event("t", title="Talks in Kyiv continue today"), language="en")
    unknown = replace(make_event("u", title="Ракетний удар по Київ"), language="und")
    short = replace(make_event("s", title="Київ", summary="Обстріл Київ сьогодні"), language="")
    blank = replace(make_event("b", title="Nothing to see here really"), language="mul")
    out = stage.process([tagged, unknown, short, blank])
    assert [e.language for e in out] == ["en", "uk", "uk", "und"]
    assert detector.samples[1].startswith("Київ Обстріл")
    assert NullDetector().detect("Anything at all, however long") is None


def test_langid_detects_short_headlines() -> None:
    detector = LangidDetector()
    assert detector.detect("Russian attacks on the Kyiv region kill two people") == "en"
    assert detector.detect("Ракетний удар по Києву: двоє загиблих, пошкоджено 28 об'єктів") == "uk"
    assert detector.detect("Frappes russes sur la région de Kyiv : deux morts") == "fr"
    assert detector.detect("short") is None


def test_packaged_watch_list_is_bounded_and_reviewed() -> None:
    watches = load_watch()
    assert 1 < len(watches) <= MAX_INSTANCES
    assert watches[0].instance == "mastodon.social"
    assert "ukraine" in watches[0].tags
    assert all(5 <= watch.minutes <= 120 for watch in watches)
    assert all(1 <= len(watch.tags) <= MAX_TAGS_PER_INSTANCE for watch in watches)
    terms = watch_terms(watches)
    assert terms == tuple(sorted(set(terms)))
    # The packaged tags share MAX_TERMS with each operator's own collection vocabulary,
    # so half the board's capacity stays free for the terms an operator chose.
    assert len(terms) <= MAX_DISTINCT_TAGS <= MAX_TERMS // 2
    assert watch_host_intervals(watches) == {watch.instance: 1.0 for watch in watches}
    assert set(watch_host_intervals(watches)) <= {watch.instance for watch in watches}


@pytest.mark.parametrize(
    "document",
    [
        {"mastodon": []},
        {"mastodon": [{"instance": "a.social", "tags": ["x"]}] * (MAX_INSTANCES + 1)},
        {"mastodon": [{"instance": "a.social", "tags": ["ok"]}, {"instance": "A.social"}]},
        {"mastodon": ["a.social"]},
        {"mastodon": [{"instance": "localhost", "tags": ["ok"]}]},
        {"mastodon": [{"instance": "http://a.social", "tags": ["ok"]}]},
        {"mastodon": [{"instance": "a.social", "tags": []}]},
        {"mastodon": [{"instance": "a.social", "tags": ["ok"], "minutes": 1}]},
        {"mastodon": [{"instance": "a.social", "tags": ["ok"], "minutes": 999}]},
        {"mastodon": [{"instance": "a.social", "tags": ["../secret"]}]},
        {"mastodon": [{"instance": "a.social", "tags": ["x"]}]},
        {"mastodon": [{"instance": "a.social", "tags": "ukraine"}]},
        {"mastodon": [{"instance": "a.social", "tags": [f"t{n}" for n in range(13)]}]},
    ],
)
def test_malformed_watch_documents_are_refused(document: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=r"."):
        parse_watch(document)


def test_watch_entries_normalise_tags_and_default_the_interval() -> None:
    watches = parse_watch(
        {"mastodon": [{"instance": "One.Social", "tags": ["#OSINT", "osint", " Ukraine "]}]}
    )
    assert watches == (InstanceWatch("one.social", ("osint", "ukraine"), DEFAULT_POLL_MINUTES),)
    repeated = parse_watch({"mastodon": [{"instance": "a.social", "tags": ["aa", "AA", "#aa"]}]})
    assert repeated[0].tags == ("aa",)
    with pytest.raises(ValueError, match="distinct"):
        parse_watch(
            {
                "mastodon": [
                    {"instance": f"i{n}.social", "tags": [f"t{n}{m}" for m in range(6)]}
                    for n in range(3)
                ]
            }
        )


async def test_a_retired_hashtag_does_not_cost_the_other_tags_on_that_instance() -> None:
    class Flaky:
        def __init__(self, status: int) -> None:
            self.requests: list[str] = []
            self._status = status

        async def get_json(self, url: str, *, conditional: bool = True) -> object:
            self.requests.append(url)
            if "gone" in url:
                raise FeedHttpStatusError(self._status, url)
            return load_fixture("mastodon_tag.json")

    http = Flaky(410)
    events = await MastodonConnector(http, FakeClock(NOW), "a.social", ["gone", "ukraine"]).fetch()  # type: ignore[arg-type]
    assert len(http.requests) == 2 and len(events) == 3
    # An instance fault or a rate limit is the scheduler's business, not the connector's.
    for status in (429, 500, 403):
        with pytest.raises(FeedHttpStatusError):
            await MastodonConnector(Flaky(status), FakeClock(NOW), "a.social", ["gone"]).fetch()  # type: ignore[arg-type]


def test_connector_takes_the_configured_interval_and_caps_its_tag_list() -> None:
    connector = MastodonConnector(
        FakeHttp(), FakeClock(NOW), "a.social", [f"t{n}" for n in range(40)], 30
    )  # type: ignore[arg-type]
    assert connector.spec.poll_interval == timedelta(minutes=30)
    assert len(connector._tags) == MAX_TAGS_PER_INSTANCE
    assert spec_for("a.social").poll_interval == timedelta(minutes=DEFAULT_POLL_MINUTES)

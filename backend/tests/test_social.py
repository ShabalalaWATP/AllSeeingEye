"""Social listening: Mastodon hashtags, outlet channels and subreddits, and language detection."""

# ruff: noqa: RUF001 (Ukrainian samples are the point)

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

from ase.adapters.feeds.mastodon import MastodonConnector, load_watch, spec_for
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.rss_seeds_social import SOCIAL_SEEDS
from ase.adapters.translate.language import LangidDetector, NullDetector
from ase.application.feeds.language import LanguageStage
from ase.application.feeds.pipeline import strip_html
from ase.domain.events import Category, Credibility, Reliability
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


def test_social_sources_are_registered() -> None:
    ids = {connector.spec.id for connector in build_connectors(FakeHttp(), FakeClock(NOW))}  # type: ignore[arg-type]
    assert {"yt_bbc_news", "yt_reuters", "reddit_worldnews", "mastodon_mastodon_social"} <= ids
    assert load_watch()[0][0] == "mastodon.social" and "ukraine" in load_watch()[0][1]
    by_id = {seed.spec.id: seed for seed in SOCIAL_SEEDS}
    assert by_id["reddit_worldnews"].spec.reliability is Reliability.E
    assert by_id["reddit_worldnews"].options.credibility is Credibility.CANNOT_BE_JUDGED
    assert by_id["yt_bbc_news"].spec.reliability is Reliability.B
    assert all(seed.spec.category is Category.SOCIAL for seed in SOCIAL_SEEDS)
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

"""Registry ratings disclose their basis without upgrading platforms or changing grades."""

import json
from dataclasses import asdict, replace
from datetime import timedelta

from ase.adapters.feeds.google_news import SPEC as GOOGLE_NEWS
from ase.adapters.feeds.mastodon import spec_for
from ase.adapters.feeds.network_outages import CLOUDFLARE_RADAR
from ase.adapters.feeds.radar_attack_trends import SPEC as RADAR_ATTACK_SPEC
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.rss_seeds_regional import REGIONAL_SEEDS
from ase.application.feeds.grading import profiles_from_specs
from ase.domain.events import Category, Reliability
from ase.domain.grading import SourceProfile, grade_events
from ase.domain.source_rating_catalog import CATALOGUE
from ase.domain.source_ratings import (
    SOURCE_RATING_POLICY_VERSION,
    source_rating_for,
    unassessed_source_rating,
)
from ase.domain.sources import SourceKind, SourceSpec
from feeds_helpers import NOW, FakeClock, FakeHttp, make_event, make_spec


def test_every_registered_source_has_explicit_versioned_rating_context():
    connectors = build_connectors(FakeHttp(), FakeClock(NOW))  # type: ignore[arg-type]
    specs = [
        *(connector.spec for connector in connectors),
        GOOGLE_NEWS,
        CLOUDFLARE_RADAR,
        RADAR_ATTACK_SPEC,
    ]
    assert len({spec.id for spec in specs}) == len(specs)
    assert set(CATALOGUE) <= {spec.id for spec in specs}
    for spec in specs:
        rating = spec.rating
        assert rating is not None, spec.id
        assert rating.policy_version == SOURCE_RATING_POLICY_VERSION
        assert rating.basis and rating.scope and rating.limitations
        assert rating.reviewed_at is None
        assert "measured accuracy percentage" in " ".join(rating.limitations)
        if (
            rating.provenance_role == "platform"
            or spec.id in {seed.spec.id for seed in REGIONAL_SEEDS}
            # Publisher headline feeds are registered with an explicit F grade and stay
            # unassessed until an editorial review records a basis; that is by design.
            or spec.reliability is Reliability.F
        ):
            assert rating.status == "unassessed" and rating.assessed_grade is None, spec.id
        else:
            assert rating.status == "editorial", spec.id
            assert rating.assessed_grade is spec.reliability
        json.dumps(asdict(rating))


def test_unknown_source_cannot_borrow_a_grade_from_a_familiar_name_or_host():
    source = SourceSpec(
        "unknown_publisher",
        "BBC via an unfamiliar account",
        "Google News",
        Category.NEWS,
        SourceKind.RSS,
        "https://news.google.com/rss/search",
        Reliability.A,
        timedelta(minutes=5),
    )
    assert (
        source.reliability is Reliability.A
    )  # Metadata does not silently replace a configured grade.
    assert source.rating == unassessed_source_rating()
    assert not source.rating.publisher_reliability_assessed
    assert SourceProfile("unknown", "BBC", "BBC").rating == unassessed_source_rating()


def test_platforms_and_aggregators_do_not_assess_the_original_publishers():
    for source_id, grade in [
        ("google_news_watchlists", Reliability.C),
        ("gdelt_events", Reliability.C),
        ("reliefweb_updates", Reliability.B),
        ("nasa_eonet", Reliability.A),
        ("ransomware_live", Reliability.B),
    ]:
        rating = source_rating_for(source_id, grade)
        assert rating.provenance_role == "aggregator"
        assert not rating.publisher_reliability_assessed
        assert rating.assessed_grade is grade
    for instance in ("mastodon.social", "foreign.example", "unfamiliar.instance"):
        source = spec_for(instance)
        assert source.reliability is Reliability.E
        assert source.rating is not None and source.rating.status == "unassessed"
        assert not source.rating.publisher_reliability_assessed
        assert "does not confer publisher credibility" in " ".join(source.rating.limitations)
    # Retired subreddit listings keep no catalogue entry of their own.
    for source_id in ("reddit_worldnews", "reddit_geopolitics", "reddit_ukrainianconflict"):
        assert source_rating_for(source_id, Reliability.E) == unassessed_source_rating()


def test_changed_configured_grade_does_not_invent_a_reassessment():
    rating = source_rating_for("bbc_world", Reliability.A)
    assert rating.status == "unassessed" and rating.assessed_grade is None
    assert "differs from the inherited registry assignment B" in rating.basis
    assert not rating.publisher_reliability_assessed
    platform = source_rating_for("mastodon_custom", Reliability.F)
    assert "retained F feed grade" in platform.basis and platform.assessed_grade is None
    source = replace(make_spec(), id="bbc_world", reliability=Reliability.B, rating=None)
    changed = replace(source, reliability=Reliability.A)
    assert changed.rating is not None and changed.rating.status == "unassessed"
    assert changed.reliability is Reliability.A


def test_appended_defaults_preserve_constructors_and_explicit_ratings_transfer_unchanged():
    spec = make_spec()
    assert spec.rating == unassessed_source_rating()
    explicit = replace(
        unassessed_source_rating(),
        basis="Explicit operator-provided source review.",
        status="editorial",
        assessed_grade=Reliability.A,
        reviewed_at=NOW,
    )
    custom = replace(spec, rating=explicit)
    profile = profiles_from_specs([custom])[custom.id]
    assert profile.rating is explicit
    assert profile.independence_key == spec.independence_key
    assert profile.flags == spec.flags and profile.instrument == spec.instrument


def test_rating_metadata_does_not_change_item_grading():
    spec = SourceSpec(
        "usgs_earthquakes",
        "USGS",
        "USGS",
        Category.DISASTER,
        SourceKind.API,
        "https://earthquake.usgs.gov/",
        Reliability.A,
        timedelta(minutes=5),
        instrument=True,
    )
    with_context = profiles_from_specs([spec])
    without_context = {spec.id: SourceProfile(spec.id, spec.independence_key, spec.name, True)}
    events = [make_event("seismic", source_id=spec.id, title="Earthquake recorded offshore")]
    assert grade_events(events, with_context) == grade_events(events, without_context)
    assert with_context[spec.id].rating is spec.rating

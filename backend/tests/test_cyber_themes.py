# ruff: noqa: RUF001
"""Theme lenses and state associations are bounded text matches, never attribution."""

from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.cyber_reference import load_actor_catalogue
from ase.adapters.feeds.cisa_kev import SPEC as KEV
from ase.adapters.feeds.cyber import IODA, RANSOMWARE
from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.cyber import CyberService
from ase.application.feeds.health import HealthRegistry
from ase.domain.cyber import CYBER_PUBLISHER_IDS, CyberKind, CyberWindowDays, cyber_kind
from ase.domain.cyber_actors import CyberActorReference, assessed_state_association
from ase.domain.cyber_themes import MAX_THEME_TEXT, CyberTheme, classify_cyber_themes
from ase.domain.events import Category
from feeds_helpers import NOW, FakeClock, make_event

T = CyberTheme


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Russian state-sponsored actors target NATO ministries", (T.NATION_STATE, T.NATO_ALLIES)),
        ("APT28 phishing campaign against Polish government", (T.NATION_STATE, T.NATO_ALLIES)),
        (
            "Volt Typhoon persistence in US critical infrastructure",
            (T.NATION_STATE, T.NATO_ALLIES, T.CRITICAL_INFRASTRUCTURE),
        ),
        ("New Windows patch fixes memory bug", ()),
        ("Poland hosts a security conference", ()),
        ("GPS jamming reported over the Baltic Sea", (T.NATO_ALLIES, T.GNSS_INTERFERENCE)),
        ("Email spoofing campaign abuses DKIM", ()),
        (
            "Spoofing of navigation signals near airports",
            (T.GNSS_INTERFERENCE, T.CRITICAL_INFRASTRUCTURE),
        ),
        ("NHS trust hit by ransomware", (T.UK_INFRASTRUCTURE, T.CRITICAL_INFRASTRUCTURE)),
        ("Cyberattack disrupts Kyiv energy company", (T.UKRAINE, T.CRITICAL_INFRASTRUCTURE)),
        ("AVEVA Pipeline Integrity Monitor advisory", (T.CRITICAL_INFRASTRUCTURE,)),
        ("An apt package update for Debian", ()),
        ("Unit 29155 espionage against Baltic states", (T.NATION_STATE, T.NATO_ALLIES)),
    ],
)
def test_lenses_match_bounded_text_only(text, expected):
    assert classify_cyber_themes(text) == expected


def test_metadata_rules_use_explicit_source_and_country_context():
    assert classify_cyber_themes("Outage", country_iso="UA") == (T.UKRAINE,)
    assert classify_cyber_themes("Outage", country_iso="GB", connectivity_signal=True) == (
        T.UK_INFRASTRUCTURE,
    )
    assert classify_cyber_themes("Outage", country_iso="GB") == ()
    assert classify_cyber_themes("Local title", source_id="cyber_cert_ua") == (T.UKRAINE,)
    assert classify_cyber_themes("Guidance for water utilities", source_id="cyber_ncsc_news") == (
        T.UK_INFRASTRUCTURE,
        T.CRITICAL_INFRASTRUCTURE,
    )
    # Ransomware claims against firms in a member state are not automatically alliance activity.
    assert classify_cyber_themes("Acme: claimed by Group", country_iso="PL") == ()


def test_lens_text_is_bounded():
    text = "x" * MAX_THEME_TEXT + " NATO"
    assert classify_cyber_themes(text) == ()
    assert classify_cyber_themes("NATO " + text) == (T.NATO_ALLIES,)


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("APT28 is a threat group that has been attributed to Russia's GRU.", "Russia"),
        ("Lazarus Group is a North Korean state-sponsored cyber threat group.", "North Korea"),
        ("APT41 is assessed as a Chinese state-sponsored espionage group.", "China"),
        ("MuddyWater is a subordinate element within Iran's Ministry of Intelligence.", "Iran"),
        ("Salt Typhoon is a People’s Republic of China (PRC) state-backed actor.", "China"),
        ("Contagious Interview is a North Korea–aligned threat group.", "North Korea"),
        ("TA459 is believed to operate out of China and has targeted Russia and Belarus.", "China"),
        ("Inception has targeted governmental entities primarily in Russia.", None),
        ("The group targeted Russian government entities in 2020.", None),
        ("APT-C-23 focused its operations on the region, including Israeli military assets.", None),
        ("Circumstantial evidence suggests a link with the United Arab Emirates (UAE).", None),
        ("FIN7 is a financially-motivated threat group that has been active since 2013.", None),
        ("Nomadic Octopus is a Russian-speaking cyber espionage threat group.", None),
        ("The group is reportedly a Chinese state-sponsored actor.", None),
        ("Tooling allegedly overlaps with Iranian government operators.", None),
        ("Compared to Russian state actors, the group is loud; no link is confirmed.", None),
        ("Researchers noted similarities to North Korean state-backed tradecraft.", None),
        ("", None),
    ],
)
def test_state_association_follows_profile_wording_not_targets(description, expected):
    assert assessed_state_association(description) == expected


def test_packaged_catalogue_associations_are_derived_from_source_wording():
    catalogue = load_actor_catalogue()
    by_name = {actor.name: actor.state_association for actor in catalogue.actors}
    assert by_name["APT28"] == "Russia"
    assert by_name["APT29"] == "Russia"
    assert by_name["Lazarus Group"] == "North Korea"
    assert by_name["Volt Typhoon"] == "China"
    assert by_name["MuddyWater"] == "Iran"
    assert by_name["FIN7"] is None
    assert by_name["Inception"] is None
    assert by_name["Equation"] is None
    associated = sum(1 for value in by_name.values() if value)
    assert 80 <= associated <= 110


def test_news_kind_and_publisher_registration():
    assert cyber_kind("news_report") is CyberKind.NEWS_REPORT
    assert len(CYBER_SEEDS) == 16
    assert {seed.spec.id for seed in CYBER_SEEDS} == set(CYBER_PUBLISHER_IDS)
    by_id = {seed.spec.id: seed for seed in CYBER_SEEDS}
    assert by_id["cyber_cert_ua"].spec.language == "uk"
    assert by_id["cyber_cert_fr"].spec.language == "fr"
    assert by_id["cyber_the_record"].options.subtype == "news_report"
    assert all(seed.options.headlines_only for seed in CYBER_SEEDS)
    assert all(seed.spec.url.startswith("https://") for seed in CYBER_SEEDS)


APT28 = CyberActorReference(
    "G0007",
    "APT28",
    ("Fancy Bear", "Pawn Storm"),
    "Reference only",
    "https://attack.mitre.org/groups/G0007/",
    NOW,
    (),
    state_association="Russia",
)
CRIMINAL = CyberActorReference(
    "G0046",
    "FIN7",
    (),
    "Reference only",
    "https://attack.mitre.org/groups/G0046/",
    NOW,
    (),
)


def service(events, disabled=()):
    store = InMemoryEventStore()
    store.upsert(events)
    admission = SimpleNamespace(
        enabled_many=AsyncMock(side_effect=lambda ids: {key: key not in disabled for key in ids})
    )
    specs = (KEV, IODA, RANSOMWARE, *(seed.spec for seed in CYBER_SEEDS))
    return CyberService(
        store,
        FakeClock(NOW),
        {spec.id: spec for spec in specs},
        admission,
        HealthRegistry(),
        (APT28, CRIMINAL),
    )


def publication(key, title, *, days_ago=0, source_id="cyber_the_record", **changes):
    return replace(
        make_event(
            key,
            source_id=source_id,
            category=Category.CYBER,
            subtype="news_report",
            title=title,
            published_at=NOW - timedelta(days=days_ago, hours=1),
            point=None,
        ),
        **changes,
    )


async def test_snapshot_reports_theme_and_state_tallies_per_day():
    events = (
        publication("a", "APT28 targets NATO summit hosts"),
        publication("b", "FIN7 returns with new phishing", days_ago=1),
        publication("c", "Pawn Storm activity against Ukrainian ministries", days_ago=1),
        publication("d", "GPS jamming over the Baltic", source_id="cyber_ncsc_news"),
    )
    svc = service(events)
    snapshot = await svc.release(await svc.read(CyberWindowDays.TWO))
    by_theme = {row.theme: row for row in snapshot.themes}
    assert set(by_theme) == set(CyberTheme)
    assert by_theme[CyberTheme.NATION_STATE].count == 2
    assert by_theme[CyberTheme.NATO_ALLIES].count == 2
    assert by_theme[CyberTheme.UKRAINE].count == 1
    assert by_theme[CyberTheme.GNSS_INTERFERENCE].count == 1
    assert len(by_theme[CyberTheme.NATION_STATE].daily) == len(snapshot.timeline)
    assert sum(by_theme[CyberTheme.NATION_STATE].daily) == 2
    assert snapshot.state_mentions == (
        replace(snapshot.state_mentions[0], state="Russia", count=2, group_ids=("G0007",)),
    )
    items = {item.title: item for item in snapshot.items}
    assert items["FIN7 returns with new phishing"].themes == ()
    assert items["APT28 targets NATO summit hosts"].kind is CyberKind.NEWS_REPORT
    linked = items["Pawn Storm activity against Ukrainian ministries"]
    assert CyberTheme.NATION_STATE in linked.themes and CyberTheme.UKRAINE in linked.themes


async def test_disabling_the_reference_removes_derived_state_lens_but_keeps_text_lenses():
    events = (
        publication("a", "Pawn Storm activity against Ukrainian ministries"),
        publication("b", "Russian state-sponsored campaign", days_ago=1),
    )
    svc = service(events, disabled=("mitre_attack",))
    snapshot = await svc.release(await svc.read(CyberWindowDays.TWO))
    assert snapshot.state_mentions == ()
    by_theme = {row.theme: row.count for row in snapshot.themes}
    assert by_theme[CyberTheme.NATION_STATE] == 1
    assert by_theme[CyberTheme.UKRAINE] == 1
    assert all(item.actor_mentions == () for item in snapshot.items)

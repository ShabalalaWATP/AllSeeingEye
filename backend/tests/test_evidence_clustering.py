"""Duplicate folding merges circulation of one story and keeps distinct reporting apart."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.prompts import evidence_block
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence_clusters import canonical_link, duplicate_clusters, normalised_title
from ase.domain.source_provenance import SourceProfile
from feeds_helpers import NOW, make_event

PROFILES = {
    "wire": SourceProfile("wire", "wire-group", "Global Wire"),
    "paper": SourceProfile("paper", "paper-group", "The Daily Paper"),
    "broadcast": SourceProfile("broadcast", "broadcast-group", "State Broadcast"),
    "local": SourceProfile("local", "local-group", "Local Herald"),
}


def select(events, *, maximum: int = 10, cap: int = 8):
    store = InMemoryEventStore()
    store.upsert(events)
    return select_evidence(
        store,
        PROFILES,
        replace(TEMPLATES["intsum"].strategy, max_items=maximum, per_source_cap=cap),
        now=NOW,
    )


def syndicated() -> list:
    """One wire story republished by three outlets, plus a translated fourth copy."""
    return [
        make_event(
            "origin",
            source_id="wire",
            title="Power plant halted after drone strike on substation",
        ).with_changes(url="https://wire.example/news/plant-halted"),
        make_event(
            "paper",
            source_id="paper",
            title="Power plant halted after drone strike on substation",
            published_at=NOW - timedelta(hours=2),
        ).with_changes(url="https://paper.example/world/plant-halted"),
        make_event(
            "broadcast",
            source_id="broadcast",
            title="Power plant halted, after drone strike on substation.",
            published_at=NOW - timedelta(hours=5),
        ).with_changes(url="https://broadcast.example/a/1"),
        make_event(
            "translated",
            source_id="local",
            title="Elektrownia wstrzymana po ataku drona na stacje",
            published_at=NOW - timedelta(hours=8),
        ).with_changes(
            url="https://local.example/pl/1",
            language="pl",
            title_en="Power plant halted after drone strike on substation",
        ),
    ]


def test_syndicated_and_translated_copies_fold_into_one_representative():
    pool = syndicated()
    keys, reasons = duplicate_clusters(pool)
    assert len({keys[event.id] for event in pool}) == 1
    assert set(next(iter(reasons.values()))) <= {"same_title", "near_identical_text"}
    selected = select(pool)
    assert len(selected.items) == 1
    assert selected.merged == 3
    assert {row.source_name for row in selected.items[0].corroboration} == {
        "The Daily Paper",
        "State Broadcast",
        "Local Herald",
    }


def test_distinct_reporting_on_a_shared_topic_never_merges():
    pool = [
        make_event("one", source_id="wire", title="Power plant halted after drone strike"),
        make_event("two", source_id="paper", title="Rail freight resumes through the border"),
        make_event("three", source_id="broadcast", title="Finance ministry raises the base rate"),
    ]
    keys, _ = duplicate_clusters(pool)
    assert len({keys[event.id] for event in pool}) == 3
    selected = select(pool)
    assert len(selected.items) == 3
    assert selected.merged == 0
    assert all(item.corroboration == () for item in selected.items)


def test_identical_links_and_hashes_fold_without_publication_proximity():
    first = make_event(
        "first", source_id="wire", title="Ministry statement on the border crossing"
    ).with_changes(url="https://wire.example/statement")
    later = make_event(
        "later",
        source_id="paper",
        title="A different headline entirely about customs queues",
        published_at=NOW - timedelta(days=30),
    ).with_changes(url="http://www.wire.example/statement/?utm_campaign=x")
    hashed = make_event(
        "hashed",
        source_id="broadcast",
        title="Yet another headline about lorries",
        published_at=NOW - timedelta(days=40),
    ).with_changes(content_hash=first.content_hash)
    keys, reasons = duplicate_clusters([first, later, hashed])
    assert len({keys[event.id] for event in (first, later, hashed)}) == 1
    assert set(next(iter(reasons.values()))) == {"same_link", "identical_content_hash"}


def test_titles_outside_the_window_stay_separate():
    first = make_event("first", source_id="wire", title="Bridge closes after structural damage")
    stale = make_event(
        "stale",
        source_id="paper",
        title="Bridge closes after structural damage",
        published_at=NOW - timedelta(days=9),
    )
    keys, _ = duplicate_clusters([first, stale])
    assert keys[first.id] != keys[stale.id]


def test_clustering_is_independent_of_input_order():
    pool = syndicated()
    forward, _ = duplicate_clusters(pool)
    backward, _ = duplicate_clusters(list(reversed(pool)))
    assert forward == backward


def test_link_and_title_normalisation_ignore_presentation_differences():
    assert canonical_link("https://WWW.Example.com/a/b/?utm_source=x&id=7#top") == (
        "example.com/a/b?id=7"
    )
    assert canonical_link(None) == ""
    assert normalised_title("  Bridge -- closes, AFTER damage! ") == "bridge closes after damage"


def test_the_prompt_shows_the_folded_copies_without_claiming_corroboration():
    selected = select(syndicated())
    block = evidence_block(selected.items[0])
    assert "Also carried by 3 further retrieved item(s) from 3 source(s)" in block
    assert "not independent corroboration" in block
    assert "The Daily Paper" in block


def test_folded_copies_do_not_spend_the_per_organisation_cap():
    pool = [
        *syndicated(),
        make_event("extra", source_id="paper", title="Customs queues grow at the crossing"),
    ]
    selected = select(pool, maximum=10, cap=1)
    assert [item.source_name for item in selected.items] == ["Global Wire", "The Daily Paper"]
    assert selected.merged == 3

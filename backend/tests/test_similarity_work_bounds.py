"""Large common-word topics have bounded candidate memory and work."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.grading import MAX_POOL, GradingService, profiles_from_specs
from ase.domain.events import Category
from ase.domain.similarity_candidates import MAX_CANDIDATES, token_candidate_pairs
from ase.domain.source_provenance import ProvenanceItem, organisation_groups
from ase.domain.story_clustering import build_stories
from feeds_helpers import NOW, FakeClock, make_event, make_spec


def test_five_thousand_common_word_headlines_do_not_form_quadratic_pairs() -> None:
    tokens = [frozenset({"common", "breaking", "news", str(i)}) for i in range(5000)]
    assert list(token_candidate_pairs(tokens)) == []


def test_five_thousand_exact_duplicates_keep_linear_links() -> None:
    tokens = [frozenset({"identical", "breaking", "headline"})] * 5000
    assert len(list(token_candidate_pairs(tokens))) == 4999
    events = [
        make_event(str(i), title="Identical breaking headline", category=Category.NEWS)
        for i in range(5000)
    ]
    assert [len(story) for story in build_stories(events)] == [5000]


def test_candidate_work_is_bounded_per_item() -> None:
    tokens = [frozenset({str(i % 100), str(i % 30), str(i)}) for i in range(5000)]
    assert sum(1 for _ in token_candidate_pairs(tokens)) <= 5000 * (MAX_CANDIDATES + 1)


def test_many_rare_postings_stop_at_candidate_budget_and_empty_tokens_do_not_link() -> None:
    tokens = [frozenset({str(i)}) for i in range(200)]
    tokens.append(frozenset(str(i) for i in range(200)))
    assert len(list(token_candidate_pairs(tokens))) == MAX_CANDIDATES
    assert list(token_candidate_pairs([frozenset(), frozenset()])) == []


def test_exact_topic_links_preserve_transitive_time_windows() -> None:
    events = [
        make_event(
            str(i),
            title="Identical breaking headline",
            category=Category.NEWS,
            published_at=NOW + timedelta(hours=40 * i),
        )
        for i in range(3)
    ]
    assert len(build_stories(list(reversed(events)))) == 1
    distant = events[0].with_changes(id="distant", published_at=NOW - timedelta(days=5))
    assert len(build_stories([*events, distant])) == 2


def test_exact_copy_provenance_and_content_hashes_remain_folded() -> None:
    items = [
        ProvenanceItem(str(i), f"organisation-{i}", "Identical breaking headline", str(i))
        for i in range(5000)
    ]
    groups = organisation_groups(items)
    assert groups.possible_copies
    assert len(groups.known_groups) == 1
    assert (
        len(
            organisation_groups(
                [
                    ProvenanceItem("a", "one", "Different first title", "same-hash"),
                    ProvenanceItem("b", "two", "Unrelated second item", "same-hash"),
                ]
            ).known_groups
        )
        == 1
    )


def test_instrument_batch_is_not_truncated_to_narrative_context_limit() -> None:
    store = InMemoryEventStore()
    events = [make_event(str(i)) for i in range(MAX_POOL + 1)]
    store.put(events)
    profiles = profiles_from_specs([replace(make_spec(), instrument=True)])
    changed = GradingService(store, profiles, FakeClock(NOW)).regrade(events)
    assert len(changed) == len(events)
    assert all("Provisional instrument" in event.grade_rationale for event in changed)

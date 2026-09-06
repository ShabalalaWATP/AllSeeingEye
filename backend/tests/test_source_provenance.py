"""Declared organisation counts must not be inflated by copies or missing provenance."""

from itertools import permutations

from ase.domain.source_provenance import ProvenanceItem, organisation_groups


def test_copy_and_parent_links_are_transitive_in_every_input_order() -> None:
    items = [
        ProvenanceItem("bbc", "BBC", "Soldiers seize border city after overnight assault"),
        ProvenanceItem("copy", "Reuters", "Soldiers seize border city after overnight assault"),
        ProvenanceItem(
            "rewrite", "Reuters", "Fighting at frontier ends as army takes regional hub"
        ),
    ]
    for order in permutations(items):
        groups = organisation_groups(order)
        assert len(groups.known_groups) == 1
        assert len(set(groups.group_of.values())) == 1
        assert groups.possible_copies


def test_different_headlines_do_not_hide_identical_content() -> None:
    items = [
        ProvenanceItem("first", "BBC", "A first heading", "same-body"),
        ProvenanceItem("second", "Reuters", "Completely unrelated headline", "same-body"),
    ]
    groups = organisation_groups(items)
    assert len(groups.known_groups) == 1
    assert groups.possible_copies


def test_unknown_provenance_is_not_an_extra_known_organisation() -> None:
    groups = organisation_groups(
        [
            ProvenanceItem("known", "BBC", "Minister appointed in London"),
            ProvenanceItem("unknown", None, "Unknown account repeats claim"),
            ProvenanceItem("empty", "", "New mystery source appears"),
        ]
    )
    assert len(groups.known_groups) == 1
    assert groups.group_of["unknown"] == groups.group_of["empty"]
    assert groups.group_of["known"] != groups.group_of["unknown"]
    assert not groups.possible_copies


def test_distinct_declared_parents_and_empty_hashes_remain_separate() -> None:
    groups = organisation_groups(
        [
            ProvenanceItem("first", "BBC", "Finance minister presents budget"),
            ProvenanceItem("second", "Reuters", "Volcano erupts on remote island"),
        ]
    )
    assert len(groups.known_groups) == 2
    assert not groups.possible_copies
    assert organisation_groups([]).known_groups == frozenset()


def test_shared_parent_counts_once_even_with_distinct_content() -> None:
    groups = organisation_groups(
        [
            ProvenanceItem("first", "BBC", "Cabinet reshuffle announced"),
            ProvenanceItem("second", "BBC", "Bridge closes for repairs"),
        ]
    )
    assert len(groups.known_groups) == 1
    assert not groups.possible_copies

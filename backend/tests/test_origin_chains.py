"""A01 origin relationships constrain independence without asserting uncertain links."""

from dataclasses import replace
from datetime import timedelta
from itertools import permutations

import pytest

from ase.domain.origin_chains import analyse_origin_chains
from ase.domain.origin_records import OriginObservation, OriginRelation, OriginRole, OriginStatus
from source_assessment_helpers import NOW, edge, node


def test_three_translations_with_different_titles_share_one_original_claim():
    nodes = [node(), *[node(f"N{i}", role=OriginRole.DERIVED) for i in range(2, 5)]]
    observations = [
        OriginObservation(
            f"P{i}",
            f"E{i}",
            "passage",
            f"retained-passage-{i}",
            OriginRelation.TRANSLATION,
            "E1",
            "C1",
        )
        for i in range(2, 5)
    ]
    edges = [edge(f"translation-{i}", f"N{i}", observation_ids=(f"P{i}",)) for i in range(2, 5)]
    result = analyse_origin_chains(nodes, edges, observations=observations)
    assert len(result.groups) == 1
    assert result.groups[0].member_ids == ("N1", "N2", "N3", "N4")
    assert result.groups[0].known_original_ids == ("N1",)
    assert all(row.status is OriginStatus.OBSERVED for row in result.relationships)
    assert not result.groups[0].review_required


def test_transitive_links_and_group_ids_are_input_order_independent():
    nodes = [node(), node("N2"), node("N3")]
    edges = [edge(), edge("link-2", "N3", "N2")]
    expected = analyse_origin_chains(nodes, edges)
    for ordered_nodes in permutations(nodes):
        for ordered_edges in permutations(edges):
            assert analyse_origin_chains(ordered_nodes, ordered_edges) == expected


def test_model_suggestion_remains_proposal_but_cannot_inflate_independence():
    result = analyse_origin_chains([node(), node("N2")], [edge()])
    assert len(result.groups) == 1
    assert result.relationships[0].status is OriginStatus.PROPOSAL
    assert result.groups[0].review_required
    assert "proposals" in " ".join(result.groups[0].reasons)


def test_existing_passage_id_alone_does_not_validate_a_model_suggested_relationship():
    observation = OriginObservation("P2", "E2", "passage", "An unrelated retained passage.")
    result = analyse_origin_chains(
        [node(), node("N2")], [edge(observation_ids=("P2",))], observations=[observation]
    )
    assert result.relationships[0].status is OriginStatus.PROPOSAL
    assert result.groups[0].review_required


def test_recorded_human_review_can_accept_or_reject_a_relationship():
    accepted = edge(reviewer_id="reviewer-1", reviewed_at=NOW)
    result = analyse_origin_chains([node(), node("N2")], [accepted])
    assert len(result.groups) == 1 and result.relationships[0].status is OriginStatus.REVIEWED
    rejected = analyse_origin_chains([node(), node("N2")], [replace(accepted, rejected=True)])
    assert len(rejected.groups) == 2
    assert rejected.relationships[0].status is OriginStatus.REJECTED
    assert not any(group.review_required for group in rejected.groups)


def test_later_model_proposal_cannot_overwrite_a_reviewer_rejection():
    rejected = edge("review", reviewer_id="reviewer-1", reviewed_at=NOW, rejected=True)
    proposal = edge("new-model-proposal", recorded_at=NOW + timedelta(days=1))
    for edges in permutations((rejected, proposal)):
        result = analyse_origin_chains([node(), node("N2")], edges)
        assert len(result.groups) == 2
        assert not any(group.review_required for group in result.groups)
        records = {row.edge.id: row for row in result.relationships}
        assert records["review"].effective
        assert not records["new-model-proposal"].effective
        assert records["new-model-proposal"].status is OriginStatus.PROPOSAL


def test_later_reviewer_can_revive_a_relation_but_tied_review_times_are_ambiguous():
    rejected = edge("review-1", reviewer_id="reviewer-1", reviewed_at=NOW, rejected=True)
    later = NOW + timedelta(days=1)
    accepted = edge("review-2", reviewer_id="reviewer-2", reviewed_at=later, recorded_at=later)
    result = analyse_origin_chains([node(), node("N2")], [rejected, accepted])
    assert len(result.groups) == 1
    assert [row.effective for row in result.relationships] == [False, True]
    with pytest.raises(ValueError, match="Tied"):
        analyse_origin_chains([node(), node("N2")], [rejected, replace(accepted, reviewed_at=NOW)])


def test_older_tied_review_decisions_are_rejected_in_every_input_order():
    first = edge("review-1", reviewer_id="reviewer-1", reviewed_at=NOW, rejected=True)
    tied = edge("review-2", reviewer_id="reviewer-2", reviewed_at=NOW)
    later = NOW + timedelta(days=1)
    newest = edge("review-3", reviewer_id="reviewer-3", reviewed_at=later, recorded_at=later)
    for edges in permutations((first, tied, newest)):
        with pytest.raises(ValueError, match="Tied"):
            analyse_origin_chains([node(), node("N2")], edges)


def test_unknown_anonymous_origin_does_not_become_independent_because_publishers_differ():
    nodes = [node(f"N{i}", role=OriginRole.UNKNOWN, original_identity=None) for i in range(1, 4)]
    result = analyse_origin_chains(nodes)
    assert len(result.groups) == 1
    assert result.groups[0].known_original_ids == ()
    assert result.groups[0].review_required


def test_possible_shared_anonymous_origin_remains_uncertain_even_with_observable_link():
    observed = OriginObservation(
        "P2",
        "E2",
        "passage",
        "Both cite an unnamed official.",
        OriginRelation.POSSIBLE_SHARED_ANONYMOUS_ORIGIN,
        "E1",
        "C1",
    )
    result = analyse_origin_chains(
        [node(), node("N2")],
        [
            edge(
                relation=OriginRelation.POSSIBLE_SHARED_ANONYMOUS_ORIGIN,
                observation_ids=("P2",),
            )
        ],
        observations=[observed],
    )
    assert result.relationships[0].status is OriginStatus.OBSERVED
    assert result.groups[0].review_required


def test_known_publisher_cannot_lend_original_identity_to_an_unknown_strong_source():
    unknown = node(role=OriginRole.UNKNOWN, original_identity=None, organisation=None)
    copy = node("N2", role=OriginRole.DERIVED, original_identity="document-N2")
    result = analyse_origin_chains([unknown, copy], [edge()])
    assert result.groups[0].known_original_ids == ()


def test_same_publisher_and_same_original_are_conservative_groups():
    for second in (node("N2", organisation="org-N1"), node("N2", original_identity="document-N1")):
        assert len(analyse_origin_chains([node(), second]).groups) == 1


def test_unrelated_claims_do_not_merge_even_with_same_source_or_unknown_origin():
    for changes in (
        {"organisation": "org-N1", "original_identity": "document-N1"},
        {"role": OriginRole.UNKNOWN, "original_identity": None},
    ):
        nodes = [node(**changes), node("N2", claim_id="C2", **changes)]
        assert len(analyse_origin_chains(nodes).groups) == 2
        with pytest.raises(ValueError, match="same declared claim"):
            analyse_origin_chains(nodes, [edge()])


def test_direct_witness_and_primary_document_remain_distinct_without_a_dependency():
    result = analyse_origin_chains([node(), node("N2", role=OriginRole.DIRECT_WITNESS)])
    assert len(result.groups) == 2
    assert all(len(group.known_original_ids) == 1 for group in result.groups)


def test_cycles_are_retained_as_a_review_issue_and_do_not_create_corroboration():
    edges = [edge(), edge("return", "N1", "N2")]
    result = analyse_origin_chains([node(), node("N2")], edges)
    assert len(result.groups) == 1 and result.groups[0].review_required
    assert "cycle" in " ".join(result.groups[0].reasons)


@pytest.mark.parametrize(
    "observation",
    [
        OriginObservation("unrelated", "E1", "passage", "P1"),
        OriginObservation("P2", "E3", "passage", "P3"),
    ],
)
def test_fabricated_or_unrelated_observation_cannot_support_an_edge(observation):
    with pytest.raises(ValueError):
        analyse_origin_chains(
            [node(), node("N2"), node("N3")],
            [edge(observation_ids=("P2",))],
            observations=[observation],
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"reason": " "},
        {"assessor": "model"},
        {"child_id": "N1"},
        {"observation_ids": ["P1"]},
        {"observation_ids": ("P1", "P1")},
        {"reviewer_id": "reviewer-1"},
        {"reviewed_at": NOW},
        {"rejected": True},
        {"recorded_at": NOW.replace(tzinfo=None)},
        {"reviewer_id": "reviewer-1", "reviewed_at": NOW + timedelta(seconds=1)},
    ],
)
def test_invalid_origin_edge_metadata_fails_before_grouping(changes):
    with pytest.raises(ValueError):
        edge(**changes)


def test_dangling_duplicate_and_unbounded_records_are_rejected():
    with pytest.raises(ValueError):
        analyse_origin_chains([node()], [edge()])
    with pytest.raises(ValueError):
        analyse_origin_chains([node(), node()])
    with pytest.raises(ValueError):
        analyse_origin_chains([node(), node("N2")], [edge(), edge()])
    with pytest.raises(ValueError):
        analyse_origin_chains([node(f"N{i}") for i in range(513)])
    with pytest.raises(ValueError):
        analyse_origin_chains([node(), node("N2", evidence_id="E1")])


def test_an_unknown_role_cannot_claim_a_resolved_original_identity():
    with pytest.raises(ValueError, match="unknown origin"):
        node(role=OriginRole.UNKNOWN)


@pytest.mark.parametrize(
    "relation,target",
    [
        (OriginRelation.TRANSLATION, None),
        (None, "E1"),
        ("translation", "E1"),
        (OriginRelation.TRANSLATION, "E2"),
    ],
)
def test_observed_relationship_requires_typed_kind_and_distinct_target(relation, target):
    with pytest.raises(ValueError):
        OriginObservation("P2", "E2", "passage", "retained-passage-2", relation, target)


def test_observed_other_relation_or_direction_does_not_confirm_the_proposal():
    observations = [
        OriginObservation(
            "P2", "E2", "link", "retained-link-2", OriginRelation.CITATION_CHAIN, "E1", "C1"
        ),
        OriginObservation(
            "P1", "E1", "link", "retained-link-1", OriginRelation.TRANSLATION, "E2", "C1"
        ),
    ]
    for observation in observations:
        result = analyse_origin_chains(
            [node(), node("N2")],
            [edge(observation_ids=(observation.id,))],
            observations=[observation],
        )
        assert result.relationships[0].status is OriginStatus.PROPOSAL


def test_observed_relationship_cannot_be_reused_for_another_claim_between_same_publications():
    nodes = [
        node(),
        node("N2"),
        node("N3", evidence_id="E1", claim_id="C2"),
        node("N4", evidence_id="E2", claim_id="C2"),
    ]
    observation = OriginObservation(
        "P2", "E2", "passage", "retained-passage-2", OriginRelation.TRANSLATION, "E1", "C1"
    )
    with pytest.raises(ValueError, match="this claim"):
        analyse_origin_chains(
            nodes,
            [edge(child="N4", parent="N3", observation_ids=("P2",))],
            observations=[observation],
        )


def test_unrelated_observation_target_cannot_create_dangling_frozen_provenance():
    observation = OriginObservation(
        "P2", "E2", "passage", "retained-passage-2", OriginRelation.TRANSLATION, "E3", "C1"
    )
    with pytest.raises(ValueError, match="endpoints"):
        analyse_origin_chains(
            [node(), node("N2"), node("N3")],
            [edge(observation_ids=("P2",))],
            observations=[observation],
        )


def test_empty_origin_analysis_is_valid_and_cannot_supply_a_group():
    result = analyse_origin_chains([])
    assert result.nodes == result.groups == result.relationships == result.observations == ()

"""Frozen context never turns collection metadata into verified dates or identity matches."""

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import timedelta

import pytest

from ase.api.schemas_research_context import ResearchContextOut
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import EvidenceAttribute, freeze_evidence_attributes
from ase.domain.research_context import MAX_CONTEXT_ITEMS, build_research_context
from feeds_helpers import NOW, make_event


def item(label="E1", **changes):
    evidence = EvidenceItem.from_event(
        label,
        make_event(label, title=f"Distinct headline {label}"),
        NOW,
        source_name="Collector",
        independence_key="",
    )
    return replace(evidence, **changes)


def attrs(**values):
    return freeze_evidence_attributes(values)


def test_empty_context_and_typed_api_have_explicit_limitations():
    context = build_research_context(())
    assert not context.timeline and not context.identity_candidates
    assert not context.source_chains and not context.source_relationships
    assert context.method_version == "ase-research-context-v1"
    assert "no external verification" in context.limitations[0]
    assert ResearchContextOut.model_validate(context).model_dump(mode="json")["timeline"] == []


def test_timeline_keeps_all_three_dates_and_original_day_precision_without_inventing_event_dates():
    filing = item(
        published_at=NOW - timedelta(days=3),
        observed_at=NOW - timedelta(minutes=1),
        attributes=attrs(date_precision="day", timestamp_basis="filing date"),
    )
    snapshot = item("E2", published_at=NOW, attributes=attrs(record_kind="current_dns_snapshot"))
    context = build_research_context((snapshot, filing))
    first, second = context.timeline
    assert first.published_at == filing.published_at
    assert first.observed_at == filing.observed_at and first.captured_at == NOW
    assert first.date_precision == "day" and first.timestamp_basis == "filing date"
    assert first.current_snapshot is None and second.current_snapshot is True
    assert "historical event" in " ".join(second.limitations)
    assert "event_at" not in asdict(first)
    with pytest.raises(FrozenInstanceError):
        first.published_at = NOW


def test_absent_metadata_and_naive_legacy_dates_are_not_repaired_or_assumed_utc():
    legacy = item("E2", published_at=NOW.replace(tzinfo=None), observed_at=None)
    context = build_research_context((legacy, item()))
    row = context.timeline[-1]
    assert row.evidence_label == "E2" and row.published_at.tzinfo is None
    assert row.observed_at is None and row.current_snapshot is None
    assert row.timestamp_basis is None and row.date_precision is None
    assert len(row.limitations) == 4


def test_conflicting_and_untyped_temporal_hints_remain_disclosed():
    frozen = item(attributes=attrs(current_snapshot=False, record_kind="current_registry_snapshot"))
    row = build_research_context((frozen,)).timeline[0]
    assert row.current_snapshot is False and "conflicts" in " ".join(row.limitations)
    unknown = item(attributes=attrs(current_snapshot="unknown", date_precision=2))
    row = build_research_context((unknown,)).timeline[0]
    assert row.current_snapshot is None and row.date_precision is None
    assert row.temporal_attributes == unknown.attributes


def test_exact_identifiers_and_aliases_are_candidates_and_never_merge_by_name_or_identifier():
    records = (
        item(
            attributes=attrs(
                cik="0000000123",
                accession="0000000123-26-000001",
                ticker="ABC",
                company_name="Same Name",
                identity_match="candidate_only",
            )
        ),
        item("E2", attributes=attrs(cik="0000000456", company_name="Same Name")),
        item("E3", attributes=attrs(cik="0000000123", alias="Old Name")),
        item("E4", attributes=attrs(domain="example.com", registry_handle="123_COM")),
    )
    context = build_research_context(records)
    assert len(context.identity_candidates) == 4
    candidate = context.identity_candidates[0]
    assert candidate.identifiers[0].value == "0000000123"
    assert candidate.declared_match_status == "candidate_only"
    assert all(row.status == "unverified_candidate" for row in context.identity_candidates)
    assert context.identity_candidates[-1].identifiers[1].namespace == "registry_handle"
    assert all("shared_declared_parent" not in row.reasons for row in context.source_relationships)


def test_alias_only_remains_candidate_and_nonstrings_are_not_invented_identifiers():
    context = build_research_context((item(attributes=attrs(name="A name", cik=123)),))
    candidate = context.identity_candidates[0]
    assert not candidate.identifiers and candidate.aliases[0].value == "A name"


def test_attribution_edges_are_direct_declarations_not_an_inferred_publisher_account_chain():
    frozen = item(
        attributes=attrs(
            original_publisher="Publisher",
            original_publisher_url="https://p.test",
            original_account="Unverified author",
            original_account_id="001",
            original_source_url="javascript:alert(1)",
        )
    )
    context = build_research_context((frozen,))
    assert len(context.source_chains) == 3
    assert {edge.collector_source_id for edge in context.source_chains} == {frozen.source_id}
    assert all(edge.status == "unverified_attribution" for edge in context.source_chains)
    assert context.source_chains[-1].declared_name is None
    # A captured URL remains plain untrusted data; rendering layers must validate clickable links.
    assert context.source_chains[-1].declared_url == "javascript:alert(1)"
    output = ResearchContextOut.model_validate(context).model_dump(mode="json")
    assert output["source_chains"][1]["declared_id"] == "001"


def test_shared_parent_and_translated_copies_are_separate_unverified_cautions():
    first = item(
        title="Original language A",
        title_en="Flood closes major eastern capital roads",
        content_hash="first",
        independence_key="parent",
    )
    second = item(
        "E2",
        title="Original language B",
        title_en=first.title_en,
        content_hash="second",
        independence_key="other",
    )
    third = item(
        "E3", title="Completely unrelated story", content_hash="first", independence_key="parent"
    )
    context = build_research_context((first, second, third))
    by_pair = {row.evidence_labels: row for row in context.source_relationships}
    assert by_pair[("E1", "E2")].reasons == ("similar_headline_possible_copy",)
    assert by_pair[("E1", "E3")].reasons == ("shared_declared_parent", "matching_content_hash")
    assert by_pair[("E1", "E2")].shared_parent is None
    assert by_pair[("E1", "E3")].shared_parent == "parent"
    assert build_research_context((third, first, second)) == context


def test_unknown_parent_empty_hash_and_topic_cluster_never_create_source_relationships():
    first = item(title="Floodwater rises near river", content_hash="", story_id="topic")
    second = item("E2", title="Election polling closes tonight", content_hash="", story_id="topic")
    assert not build_research_context((first, second)).source_relationships


@pytest.mark.parametrize("label", ["", " ", "x" * 65])
def test_ambiguous_or_oversized_labels_are_rejected(label):
    with pytest.raises(ValueError, match="labels"):
        build_research_context((item(label),))


def test_bounded_input_and_duplicate_labels_fail_explicitly_instead_of_omitting_evidence():
    with pytest.raises(ValueError, match="limit"):
        build_research_context(tuple(item(f"E{x}") for x in range(MAX_CONTEXT_ITEMS + 1)))
    with pytest.raises(ValueError, match="labels"):
        build_research_context((item(), item()))
    with pytest.raises(ValueError, match="oversized"):
        build_research_context((item(title="x" * 2001),))
    with pytest.raises(ValueError, match="attribute"):
        build_research_context((item(attributes=(EvidenceAttribute("key", "x" * 501),)),))

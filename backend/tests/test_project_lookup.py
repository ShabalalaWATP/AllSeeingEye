"""Exact identifiers retain term, country and date constraints through native collection."""

import pytest

from ase.adapters.research_records.aiddata_search import search_catalogue
from ase.domain.project_lookup import preserve_project_lookup, project_lookup
from ase.domain.research import CollectionStatus
from test_aiddata_provider import provider, query
from test_aiddata_search import END, START, catalogue


def test_model_rewording_keeps_exact_identifier_and_rejects_substitution():
    assert preserve_project_lookup(("aiddata:35756",), ("airport",)) == (
        "aiddata:35756",
        "airport",
    )
    with pytest.raises(ValueError, match="cannot change"):
        preserve_project_lookup(("aiddata:35756",), ("aiddata:35757",))


async def test_exact_lookup_finds_id_absent_from_title_and_keeps_other_constraints(tmp_path):
    native = provider(catalogue(tmp_path, 2))
    found = await native.collect(query(terms=("aiddata:35757",)))
    assert [item.project.project_id for item in found.items] == ["35757"]
    for terms in [("aiddata:357",), ("aiddata:35757", "unmatched")]:
        assert not (await native.collect(query(terms=terms))).items
    assert not (
        await native.collect(
            query(terms=("aiddata:35757",), since=END, until=END.replace(year=2013))
        )
    ).items


@pytest.mark.parametrize(
    "terms",
    [
        ("aiddata:x",),
        ("aiddata:123 OR 1=1",),
        ("aiddata:٣٥٧",),
        ("aiddata:1", "aiddata:2"),
        ("aiddata:1234567890123",),
    ],
)
async def test_invalid_identifier_is_unsupported_without_catalogue_access(terms):
    with pytest.raises(ValueError):
        project_lookup(terms)
    assert (await provider(None).collect(query(terms=terms))).attempts[
        0
    ].status is CollectionStatus.UNSUPPORTED


def test_direct_lookup_keeps_recipient_filter_and_rejects_invalid_id(tmp_path):
    path = catalogue(tmp_path)
    assert not search_catalogue(
        path, terms=(), since=START, until=END, project_id="35756", recipient_iso3="CHN"
    ).records
    with pytest.raises(ValueError):
        search_catalogue(path, terms=(), since=START, until=END, project_id="x")

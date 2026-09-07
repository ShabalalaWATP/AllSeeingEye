"""Catalogue searches preserve scope, uncertainty and bounded local access."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from ase.adapters.research_records.aiddata_catalogue import import_project_directory
from ase.adapters.research_records.aiddata_search import search_catalogue
from ase.cli import app
from ase.domain.project_time import ProjectYearMatch
from test_aiddata_records import source

START, END = datetime(2011, 1, 1, tzinfo=UTC), datetime(2012, 1, 1, tzinfo=UTC)


def catalogue(tmp_path, count=1):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    for number in range(count):
        identity = 35756 + number
        (inputs / f"{identity}.geojson").write_bytes(source(id=identity))
    return import_project_directory(inputs, tmp_path / "cache")


def test_country_terms_and_year_scope_are_applied_without_modifying_catalogue(tmp_path):
    path = catalogue(tmp_path)
    before = path.read_bytes()
    result = search_catalogue(
        path, terms=("AIRPORT",), since=START, until=END, recipient_iso3="LAO"
    )
    assert len(result.records) == 1
    assert result.matches == (ProjectYearMatch.WITHIN,)
    assert result.catalogue_count == 1 and not result.truncated
    assert not search_catalogue(
        path, terms=("airport",), since=START, until=END, recipient_iso3="CHN"
    ).records
    assert not search_catalogue(path, terms=("' OR 1=1 --",), since=START, until=END).records
    assert path.read_bytes() == before


def test_partial_year_is_only_a_possible_temporal_match(tmp_path):
    result = search_catalogue(
        catalogue(tmp_path), terms=(), since=datetime(2011, 6, 1, tzinfo=UTC), until=END
    )
    assert result.matches == (ProjectYearMatch.POSSIBLE,)


def test_result_cap_discloses_truncation(tmp_path):
    result = search_catalogue(catalogue(tmp_path, 21), terms=(), since=START, until=END)
    assert len(result.records) == 20
    assert result.truncated and result.catalogue_count == 21


def test_tampered_index_is_rejected(tmp_path):
    path = catalogue(tmp_path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE projects SET commitment_year=2010")
    with pytest.raises(ValueError, match="disagree"):
        search_catalogue(path, terms=(), since=datetime(2010, 1, 1, tzinfo=UTC), until=END)


def test_unknown_years_require_explicit_inclusion(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "35756.geojson").write_bytes(source(**{"Commitment.Year": None}))
    path = import_project_directory(inputs, tmp_path / "cache")
    assert not search_catalogue(path, terms=(), since=START, until=END).records
    result = search_catalogue(path, terms=(), since=START, until=END, include_unknown_years=True)
    assert result.matches == (ProjectYearMatch.UNKNOWN,)


def test_whitespace_fields_normalise_consistently_during_import_and_search(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "35756.geojson").write_bytes(source(Title="   ", Recipient=" "))
    path = import_project_directory(inputs, tmp_path / "cache")
    result = search_catalogue(path, terms=(), since=START, until=END)
    assert result.records[0].title == "Unknown"
    assert result.records[0].recipient == "Unknown"


def test_result_byte_limit_reports_truncation(tmp_path, monkeypatch):
    path = catalogue(tmp_path)
    monkeypatch.setattr("ase.adapters.research_records.aiddata_search.MAX_RESULT_BYTES", 1)
    result = search_catalogue(path, terms=(), since=START, until=END)
    assert result.records == () and result.truncated


def test_forged_search_index_cannot_supply_unmatched_records(tmp_path):
    path = catalogue(tmp_path)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("UPDATE projects SET search_text='unrelated'")
    with pytest.raises(ValueError, match="disagree"):
        search_catalogue(path, terms=("unrelated",), since=START, until=END)


def test_operator_import_command_creates_catalogue_without_activation(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "35756.geojson").write_bytes(source())
    result = CliRunner().invoke(
        app, ["import-aiddata", str(inputs), "--cache-dir", str(tmp_path / "cache")]
    )
    assert result.exit_code == 0, result.output
    assert "does not activate" in result.output
    assert len(list((tmp_path / "cache").glob("*.sqlite"))) == 1

"""Bounded immutable catalogue imports fail without publishing partial data."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ase.adapters.research_records.aiddata_catalogue import import_project_directory
from test_aiddata_records import source


def test_native_directory_import_is_searchable_versioned_and_never_overwritten(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "35756.geojson").write_bytes(source())
    cache = tmp_path / "cache"
    target = import_project_directory(inputs, cache)
    with closing(sqlite3.connect(target)) as connection:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        assert metadata["project_count"] == "1"
        assert "unverified" in metadata["authenticity"]
        row = connection.execute(
            "SELECT id FROM projects WHERE instr(search_text, ?) > 0", ("airport",)
        ).fetchone()
        assert row == ("35756",)
    original = target.read_bytes()
    with pytest.raises(FileExistsError):
        import_project_directory(inputs, cache)
    assert target.read_bytes() == original
    assert list(cache.iterdir()) == [target]


def test_bad_file_does_not_publish_partial_catalogue(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "35756.geojson").write_bytes(source())
    (inputs / "123.geojson").write_bytes(b"not json")
    cache = tmp_path / "cache"
    with pytest.raises(ValueError):
        import_project_directory(inputs, cache)
    assert not list(cache.iterdir())


def test_import_obeys_total_byte_budget(tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "35756.geojson").write_bytes(source())
    cache = tmp_path / "cache"
    monkeypatch.setattr("ase.adapters.research_records.aiddata_catalogue.MAX_SOURCE_BYTES", 1)
    with pytest.raises(ValueError, match="budget"):
        import_project_directory(inputs, cache)
    assert not list(cache.iterdir())


def test_replaced_file_is_rejected_before_reading(tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    selected = inputs / "35756.geojson"
    selected.write_bytes(source())
    original_open = os.open

    def swapped_open(path, flags, *args, **kwargs):
        if isinstance(path, str | Path) and Path(path) == selected:
            selected.rename(inputs / "original.saved")
            selected.write_bytes(source())
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swapped_open)
    cache = tmp_path / "cache"
    with pytest.raises(ValueError, match="changed"):
        import_project_directory(inputs, cache)
    assert not list(cache.iterdir())

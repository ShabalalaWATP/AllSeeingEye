"""Infrastructure commands load their selected adapter and preserve CLI contracts."""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from typer.testing import CliRunner

from ase.cli import app

COMMANDS = [
    (
        "import-ground-stations",
        "ase.adapters.geo.infrastructure_import.import_ground_stations",
        "--destination",
        None,
        30,
        "Wrote 30 ground stations",
    ),
    (
        "import-data-centres",
        "ase.adapters.geo.infrastructure_import.import_data_centres",
        "--destination",
        None,
        20,
        "Wrote 20 data centres",
    ),
    (
        "import-energy-sites",
        "ase.adapters.geo.sites_import.import_sites",
        "--destination",
        "energy",
        10,
        "Wrote 10 energy sites",
    ),
    (
        "import-semiconductor-sites",
        "ase.adapters.geo.sites_import.import_sites",
        "--destination",
        "semiconductor",
        5,
        "Wrote 5 semiconductor sites",
    ),
    (
        "import-infrastructure-notes",
        "ase.adapters.geo.infrastructure_notes.import_infrastructure_notes",
        "--resources",
        None,
        {"cables": 3, "nuclear": 2, "stations": 1},
        "Enriched 3 cable segments, 2 nuclear plants and 1 ground stations.",
    ),
]


@pytest.mark.parametrize("command,adapter,option,layer,count,message", COMMANDS)
@pytest.mark.parametrize("contact", [None, "https://example.test/operator"])
def test_selected_command_preserves_arguments_and_counts(
    tmp_path: Path, monkeypatch, command, adapter, option, layer, count, message, contact
):
    importer = Mock(return_value=count)
    monkeypatch.setattr(adapter, importer)
    destination = tmp_path / "selected destination"
    arguments = [command, option, str(destination)]
    if contact is not None:
        arguments += ["--contact", contact]

    result = CliRunner().invoke(app, arguments)

    assert result.exit_code == 0, result.output
    assert message in result.output
    positional = (str(destination),) if layer is None else (layer, str(destination))
    importer.assert_called_once_with(
        *positional, contact=contact or "https://github.com/ShabalalaWATP/OSINT"
    )


@pytest.mark.parametrize("command,adapter,option,layer,count,message", COMMANDS)
def test_selected_command_keeps_upstream_failure_details_private(
    tmp_path: Path, monkeypatch, command, adapter, option, layer, count, message
):
    importer = Mock(side_effect=httpx.ConnectError("synthetic-private-upstream-detail"))
    monkeypatch.setattr(adapter, importer)

    result = CliRunner().invoke(app, [command, option, str(tmp_path / "selected destination")])

    assert result.exit_code == 1
    assert "Import failed: ConnectError. Check connectivity and retry." in result.output
    assert "synthetic-private-upstream-detail" not in result.output
    assert message not in result.output
    importer.assert_called_once()

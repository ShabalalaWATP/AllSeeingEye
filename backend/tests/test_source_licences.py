"""Licence coverage is a source-addition gate, not proof of legal permission."""

import json
import runpy
import socket
from copy import deepcopy
from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from ase.container.source_requirements import source_requirements
from ase.infrastructure.settings import Settings
from source_licence_catalogue import catalogue_assets, catalogue_specs
from source_licence_validation import validate_register

ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> dict[str, Any]:
    return json.loads(files("ase.resources").joinpath(name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError("Licence inventory tests must not contact providers")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def test_every_supported_source_has_one_licence_register_row() -> None:
    metadata = load("source_licences.json")
    catalogue = [row.id for row in [*catalogue_specs(), *catalogue_assets()]]
    registered = [row["id"] for row in metadata["sources"]]
    assert len(catalogue) == len(set(catalogue)), "Duplicate catalogue identities"
    assert len(registered) == len(set(registered)), "Duplicate licence-register rows"
    assert set(registered) == set(catalogue), {
        "missing": sorted(set(catalogue) - set(registered)),
        "obsolete": sorted(set(registered) - set(catalogue)),
    }


def test_register_is_valid_and_packaged_with_policy_evidence() -> None:
    validate_register(load("source_licences.json"), load("source_licence_policies.json"))


def test_known_catalogue_prerequisites_are_not_lost_in_the_register() -> None:
    rows = {row["id"]: row for row in load("source_licences.json")["sources"]}
    requirements = source_requirements(Settings.model_construct())
    requirements.update(
        {asset.id: asset.requirement for asset in catalogue_assets() if asset.requirement}
    )
    for source_id, requirement in requirements.items():
        if requirement.setting:
            assert requirement.setting in rows[source_id]["gating_flags"], source_id


def test_every_configured_camera_host_has_an_explicit_review_policy() -> None:
    configured = json.loads((ROOT / "frontend/src/lib/api/cameraMediaHosts.json").read_text())
    rows = load("source_licences.json")["camera_hosts"]
    policies = load("source_licence_policies.json")["policies"]
    assert {row["host"] for row in rows} == set().union(*configured.values())
    for row in rows:
        assert set(row["uses"]) == {
            kind for kind, hosts in configured.items() if row["host"] in hosts
        }
        assert row["policy"] in policies


def test_generated_document_is_fresh() -> None:
    # Load the pure renderer without invoking its writing CLI entry point.
    renderer = runpy.run_path(str(ROOT / "scripts/render_source_licences.py"))
    assert (ROOT / "docs/SOURCE_LICENCES.md").read_text(encoding="utf-8") == renderer["render"]()


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_field",
        "unknown_policy",
        "duplicate_id",
        "invalid_date",
        "blocked_verified",
        "unknown_allowed",
        "future_check",
        "claim_enforcement",
    ],
)
def test_rejects_incomplete_or_misleading_metadata(mutation: str) -> None:
    register = deepcopy(load("source_licences.json"))
    policies = deepcopy(load("source_licence_policies.json"))
    if mutation == "missing_field":
        del register["sources"][0]["gating_flags"]
    elif mutation == "unknown_policy":
        register["sources"][0]["policy"] = "nonexistent"
    elif mutation == "duplicate_id":
        register["sources"][1]["id"] = register["sources"][0]["id"]
    elif mutation == "invalid_date":
        register["sources"][0]["code_checked_on"] = "2026-02-30"
    elif mutation == "blocked_verified":
        policies["policies"]["ioda"]["terms_checked_on"] = "2026-10-09"
    elif mutation == "unknown_allowed":
        policies["policies"]["unknown-publisher"]["commercial_use"] = "conditional"
    elif mutation == "future_check":
        policies["policies"]["ooni"]["terms_checked_on"] = "2030-01-01"
    else:
        register["enforcement"] = "approved_for_commercial_use"
    with pytest.raises((AssertionError, ValidationError)):
        validate_register(register, policies)

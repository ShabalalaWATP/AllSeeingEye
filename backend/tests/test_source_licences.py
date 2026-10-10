"""Licence coverage is a source-addition gate, not proof of legal permission."""

import json
import re
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


@pytest.mark.parametrize("link", [None, "", "not-a-url", "file:///private", "javascript:void(0)"])
def test_every_source_requires_an_http_provenance_link(link: str | None) -> None:
    register = deepcopy(load("source_licences.json"))
    register["sources"][0]["source_url"] = link
    with pytest.raises(ValidationError):
        validate_register(register, load("source_licence_policies.json"))


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


@pytest.mark.parametrize(
    ("host", "use"),
    [("www.youtube-nocookie.com", "frames"), ("www.youtube.com", "legacyFrames")],
)
def test_youtube_embed_hosts_retain_owner_and_provider_permission_review(
    host: str, use: str
) -> None:
    rows = {row["host"]: row for row in load("source_licences.json")["camera_hosts"]}
    policies = load("source_licence_policies.json")["policies"]
    row = rows[host]
    assert row["uses"] == [use]
    assert row["policy"] == "camera-owner-rights"
    assert row["provider_policy"] == "camera-youtube"
    for policy_id in (row["policy"], row["provider_policy"]):
        policy = policies[policy_id]
        assert policy["commercial_use"] == "unknown"
        assert policy["hosted_multi_user_use"] == "unknown"
        assert policy["commercial_use_policy"] == "licence_required"
    assert (
        "https://support.google.com/youtube/answer/171780?expand=PrivacyEnhancedMode&hl=en-GB"
        in policies["camera-youtube"]["additional_terms_urls"]
    )


def test_generated_document_is_fresh() -> None:
    # Load the pure renderer without invoking its writing CLI entry point.
    renderer = runpy.run_path(str(ROOT / "scripts/render_source_licences.py"))
    assert (ROOT / "docs/SOURCE_LICENCES.md").read_text(encoding="utf-8") == renderer["render"]()


@pytest.mark.parametrize(
    "source_id",
    [
        "map:military_source_index",
        "reference:conflicts",
        "research-asset-register",
        "research-retained-area-feeds",
        "research_import",
        "research_media",
    ],
)
def test_mixed_and_private_sources_link_catalogue_without_claiming_terms(source_id: str) -> None:
    rows = {row["id"]: row for row in load("source_licences.json")["sources"]}
    row = rows[source_id]
    policy = load("source_licence_policies.json")["policies"][row["policy"]]
    assert row["source_url_kind"] == "catalogue_provenance_only"
    assert isinstance(row["source_url"], str)
    assert re.fullmatch(
        r"https://github\.com/ShabalalaWATP/AllSeeingEye/blob/[0-9a-f]{40}/.+",
        row["source_url"],
    )
    assert policy["review_status"] == "per_item_required"
    assert policy["terms_url"] is policy["terms_checked_on"] is None
    assert policy["lookup_attempted_on"] is None
    assert policy["commercial_use"] == policy["hosted_multi_user_use"] == "unknown"


def test_per_item_rows_show_catalogue_dates_without_claiming_terms() -> None:
    policies = load("source_licence_policies.json")["policies"]
    renderer = runpy.run_path(str(ROOT / "scripts/render_source_licences.py"))
    rendered = renderer["render"]().splitlines()
    for row in load("source_licences.json")["sources"]:
        if policies[row["policy"]]["review_status"] != "per_item_required":
            continue
        line = next(line for line in rendered if f'id="source-{row["id"]}"' in line)
        assert f"catalogue checked {row['code_checked_on']} (provider terms not verified)" in line
        assert f"]({row['source_url']}) (catalogue provenance only)" in line
        assert "terms unverified; per_item_required" in line


def test_attempted_terms_dates_remain_attempts_in_the_rendered_register() -> None:
    policies = load("source_licence_policies.json")["policies"]
    renderer = runpy.run_path(str(ROOT / "scripts/render_source_licences.py"))
    rendered = renderer["render"]().splitlines()
    for row in load("source_licences.json")["sources"]:
        policy = policies[row["policy"]]
        if policy["review_status"] not in {"lookup_blocked", "lookup_inconclusive"}:
            continue
        line = next(line for line in rendered if f'id="source-{row["id"]}"' in line)
        assert f"attempt {policy['lookup_attempted_on']}" in line
        assert "catalogue checked" not in line
        assert policy["terms_checked_on"] is None


def test_composite_kev_scores_retain_both_enrichment_provider_policies() -> None:
    # A SourceSpec-only inventory would miss these retained score providers.
    rows = {row["id"]: row for row in load("source_licences.json")["sources"]}
    assert rows["cisa_kev"]["policy"] == "cisa"
    assert set(rows["cisa_kev"]["additional_policies"]) == {"first-epss", "nist-nvd"}


@pytest.mark.parametrize("source_id", ["map:nuclear_facilities", "map:submarine_cables"])
def test_bundled_infrastructure_retains_structured_fact_provenance(source_id: str) -> None:
    rows = {row["id"]: row for row in load("source_licences.json")["sources"]}
    assert "wikidata-structured" in rows[source_id]["additional_policies"]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_field",
        "unknown_policy",
        "duplicate_id",
        "invalid_date",
        "blocked_verified",
        "inconclusive_verified",
        "missing_camera_provider",
        "unknown_camera_use",
        "missing_enrichment_provider",
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
    elif mutation == "inconclusive_verified":
        policies["policies"]["mediazona"]["terms_checked_on"] = "2026-10-09"
    elif mutation == "missing_camera_provider":
        register["camera_hosts"][0]["provider_policy"] = "nonexistent"
    elif mutation == "unknown_camera_use":
        register["camera_hosts"][0]["uses"] = ["unreviewed"]
    elif mutation == "missing_enrichment_provider":
        register["sources"][0]["additional_policies"] = ["nonexistent"]
    elif mutation == "unknown_allowed":
        policies["policies"]["unknown-publisher"]["commercial_use"] = "conditional"
    elif mutation == "future_check":
        policies["policies"]["ooni"]["terms_checked_on"] = "2030-01-01"
    else:
        register["enforcement"] = "approved_for_commercial_use"
    with pytest.raises((AssertionError, ValidationError)):
        validate_register(register, policies)

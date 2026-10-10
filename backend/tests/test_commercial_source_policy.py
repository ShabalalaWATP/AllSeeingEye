"""Commercial source restrictions are independent of credentials and admin overrides."""

import json
from importlib.resources import files

import pytest

from ase.domain.errors import Forbidden
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from ase.infrastructure.source_licences import load_source_licences, parse_source_licences


def entry(source_id: str, status: str) -> SourceLicence:
    return SourceLicence(source_id, status, True, f"docs/SOURCE_LICENCES.md#source-{source_id}")


@pytest.mark.parametrize("status", ["allowed", "forbidden", "licence_required"])
def test_default_mode_preserves_existing_admission(status: str) -> None:
    policy = SourceLicencePolicy([entry("source", status)])
    assert policy.allowed("source")
    assert policy.allowed("test-injected-source")
    policy.require("source")


def test_explicit_acknowledgement_is_per_source_and_cannot_override_forbidden() -> None:
    policy = SourceLicencePolicy(
        [
            entry("allowed", "allowed"),
            entry("unknown", "licence_required"),
            entry("other", "licence_required"),
            entry("forbidden", "forbidden"),
        ],
        commercial_use=True,
        acknowledgements=frozenset({"unknown", "forbidden"}),
    )
    assert policy.allowed("allowed")
    assert policy.allowed("unknown")
    assert not policy.allowed("other")
    assert not policy.allowed("forbidden")
    assert not policy.allowed("new-unregistered-source")
    with pytest.raises(Forbidden, match="due to licence terms"):
        policy.require("forbidden")


def documents() -> tuple[dict, dict]:
    resources = files("ase.resources")
    return (
        json.loads(resources.joinpath("source_licences.json").read_text()),
        json.loads(resources.joinpath("source_licence_policies.json").read_text()),
    )


@pytest.mark.parametrize("field", ["commercial_use", "attribution_required", "licence_ref"])
def test_startup_rejects_missing_mandatory_metadata(field: str) -> None:
    register, evidence = documents()
    del register["sources"][0][field]
    with pytest.raises(ValueError):
        parse_source_licences(register, evidence)


def test_startup_rejects_permissive_classification_over_unverified_component() -> None:
    register, evidence = documents()
    row = next(row for row in register["sources"] if row["id"] == "cisa_kev")
    row["commercial_use"] = "allowed"
    with pytest.raises(ValueError, match="not fully reviewed"):
        parse_source_licences(register, evidence)


def test_startup_rejects_missing_additional_policy() -> None:
    register, evidence = documents()
    del evidence["policies"]["first-epss"]
    with pytest.raises(ValueError, match="Missing policy"):
        parse_source_licences(register, evidence)


@pytest.mark.parametrize("corruption", ["duplicate_id", "wrong_reference", "repeated_policy"])
def test_startup_rejects_ambiguous_or_untraceable_metadata(corruption: str) -> None:
    register, evidence = documents()
    row = register["sources"][0]
    if corruption == "duplicate_id":
        register["sources"].append(dict(row))
    elif corruption == "wrong_reference":
        row["licence_ref"] = "docs/SOURCE_LICENCES.md#source-another-source"
    else:
        row["additional_policies"].append(row["policy"])
    with pytest.raises(ValueError):
        parse_source_licences(register, evidence)


def test_additional_component_prohibition_cannot_be_reduced_to_acknowledgement() -> None:
    register, evidence = documents()
    row = next(row for row in register["sources"] if row["id"] == "map:nuclear_facilities")
    row["commercial_use"] = "licence_required"
    evidence["policies"]["wikidata-structured"]["commercial_use_policy"] = "forbidden"
    with pytest.raises(ValueError, match="forbidden commercial component"):
        parse_source_licences(register, evidence)


def test_packaged_noncommercial_imagery_and_sources_are_never_acknowledged_open() -> None:
    blocked = {"map:eox_s2cloudless", "research-ooni-aggregate"}
    policy = load_source_licences(commercial_use=True, acknowledgements=frozenset(blocked))
    for source_id in blocked:
        decision = policy.decision(source_id)
        assert decision.commercial_use == "forbidden"
        assert not decision.available


def test_acknowledgement_typo_is_rejected_at_startup() -> None:
    with pytest.raises(ValueError, match="Unknown source licence acknowledgement"):
        load_source_licences(acknowledgements=frozenset({"invented-source"}))


def test_missing_catalogue_entry_fails_startup_validation() -> None:
    policy = SourceLicencePolicy([entry("known", "allowed")])
    with pytest.raises(ValueError, match="Missing source licence metadata"):
        policy.validate_ids(["known", "new-source"])

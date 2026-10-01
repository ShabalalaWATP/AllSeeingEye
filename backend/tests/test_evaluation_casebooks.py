"""Packaged evaluation casebooks keep the CLI working and every case fingerprint stable."""

import hashlib
from importlib.resources import files

import pytest
from evaluations.casebook import CASE_DIRECTORY
from evaluations.casebook import load_cases as cli_load_cases

from ase.adapters.evaluations.casebook import CASEBOOKS, load_cases, packaged_cases

# Recorded from the checked-in casebooks before they moved into the ase package.
COMBINED_FINGERPRINTS = {
    "core": (8, "9d0b3cc1290752d53497e44eb1887f8b55ed40cc11f8e3142ec2e9d7708fd770"),
    "regional": (12, "ed447b3a4e6a4c656822a1d1dbd55fb9365f0fd37f2398f217b31c3ca5b37025"),
}


def _combined(cases) -> str:
    text = "".join(f"{case.id}:{case.fingerprint}\n" for case in cases)
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.mark.parametrize("casebook", sorted(COMBINED_FINGERPRINTS))
def test_packaged_casebooks_preserve_case_fingerprints(casebook: str) -> None:
    count, digest = COMBINED_FINGERPRINTS[casebook]
    cases = packaged_cases(casebook)
    assert len(cases) == count
    assert _combined(cases) == digest


def test_casebooks_are_package_resources_the_cli_still_reads() -> None:
    assert set(CASEBOOKS) == {"core", "regional"}
    resource = files("ase.resources").joinpath("evaluations/core")
    assert any(item.name.endswith(".json") for item in resource.iterdir())
    # The CLI default is the packaged core casebook, not a second copy.
    assert [case.fingerprint for case in cli_load_cases()] == [
        case.fingerprint for case in packaged_cases("core")
    ]
    assert [case.id for case in cli_load_cases(CASE_DIRECTORY)] == [
        case.id for case in load_cases(CASE_DIRECTORY)
    ]


def test_unknown_casebooks_are_refused() -> None:
    with pytest.raises(ValueError, match="Unknown evaluation casebook"):
        packaged_cases("v01")

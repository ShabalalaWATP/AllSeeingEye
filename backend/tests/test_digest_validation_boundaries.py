"""Mechanical digest checks handle malformed dates, decimal forms and byte limits."""

from ase.application import ukraine_digest_validation as validation
from ase.application.ukraine_digest_evidence import evidence_pack
from ase.domain.ukraine.digest import UkraineDigest
from ukraine_digest_helpers import NOW, answer, board


def test_digest_checks_in_period_and_invalid_dates_without_crashing():
    pack = evidence_pack(board(), NOW)
    digest = UkraineDigest.model_validate_json(answer())
    digest = digest.model_copy(
        update={
            "watch": [
                f"Watch developments from {pack.period_start.isoformat()} "
                f"to {pack.period_end.isoformat()}.",
                "An impossible date such as 2026-02-31 needs correction.",
            ]
        }
    )
    errors = validation.validate_digest(digest, pack)
    assert any("not a real date" in error for error in errors)
    assert not any("falls outside" in error for error in errors)


def test_decimal_normalisation_and_serialised_byte_budget(monkeypatch):
    assert validation._canonical("000.500") == "0.5"
    assert validation._canonical("001.000") == "1.0"
    digest = UkraineDigest.model_validate_json(answer())
    monkeypatch.setattr(validation, "MAX_PAYLOAD_BYTES", 10)
    errors = validation.validate_digest(digest, evidence_pack(board(), NOW))
    assert "The digest is too long. Shorten the summaries and changes." in errors

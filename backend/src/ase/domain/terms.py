"""The published Terms and Acceptable Use Policy version that accounts must accept."""

from __future__ import annotations

from ase.domain.errors import AppError

# Bump with every material change to the public /terms or /acceptable-use wording.
# Signed-in accounts whose accepted version differs are asked to accept again.
CURRENT_TERMS_VERSION = "2026-10-27"


class TermsNotAccepted(AppError):
    """Reported like any other field validation failure, so it reveals nothing else."""

    code = "validation_error"
    default_message = "The request is invalid."

    def __init__(self) -> None:
        reason = "Agree to the Terms and Acceptable Use Policy to request an account."
        super().__init__(fields={"accept_terms": reason})


class TermsVersionChanged(AppError):
    code = "conflict"
    default_message = "The terms have changed. Review the current version before accepting."

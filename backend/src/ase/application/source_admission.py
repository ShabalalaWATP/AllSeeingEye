"""Public admission reasons, retaining compatibility with minimal injected gates."""

from ase.application.ports.source_controls import LicenceAwareSourceAdmission, SourceAdmission


def source_denial_reason(admission: SourceAdmission | None, source_id: str, fallback: str) -> str:
    if isinstance(admission, LicenceAwareSourceAdmission):
        return admission.licence_denial(source_id) or fallback
    return fallback

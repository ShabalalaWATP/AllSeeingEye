"""Narrow structural checks for generic analytical confidence explanations."""

import re

_GENERIC_RATIONALES = frozenset(
    {
        "because",
        "uncertain",
        "unknown",
        "limited information",
        "insufficient evidence",
        "low confidence",
        "moderate confidence",
        "high confidence",
        "sources say so",
        "the sources say so",
        "the evidence is sufficient",
        "the evidence supports this",
    }
)
_GENERIC_PATTERN = re.compile(
    r"(?:because )?(?:the )?(?:evidence|sources|reporting) "
    r"(?:says?|indicates?|supports?) (?:so|this|it)"
)


def generic_confidence_rationale(value: str) -> bool:
    """Reject a small, explicit boilerplate set; never claim to grade prose quality."""
    normalised = re.sub(r"[^\w]+", " ", value.casefold()).strip()
    return (
        not normalised
        or normalised in _GENERIC_RATIONALES
        or bool(_GENERIC_PATTERN.fullmatch(normalised))
    )

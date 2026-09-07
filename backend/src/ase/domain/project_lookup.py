"""Explicit project lookup tokens are constraints, never fuzzy identity matches."""

import re


def project_lookup(terms: tuple[str, ...]) -> tuple[str | None, tuple[str, ...]]:
    identifiers = [term for term in terms if term.lower().startswith("aiddata:")]
    if not identifiers:
        return None, terms
    if len(identifiers) != 1 or not re.fullmatch(r"aiddata:[0-9]{1,12}", identifiers[0], re.I):
        raise ValueError("Provide one exact AidData project ID containing up to 12 digits")
    return identifiers[0].split(":", 1)[1], tuple(term for term in terms if term != identifiers[0])


def preserve_project_lookup(
    original: tuple[str, ...], proposed: tuple[str, ...]
) -> tuple[str, ...]:
    """Keep exact project scope when a model proposes different search wording."""
    identity, _ = project_lookup(original)
    if identity is None:
        return proposed
    revised, terms = project_lookup(proposed)
    if revised is not None and revised != identity:
        raise ValueError("A revised search cannot change the selected project")
    return (f"aiddata:{identity}", *terms)

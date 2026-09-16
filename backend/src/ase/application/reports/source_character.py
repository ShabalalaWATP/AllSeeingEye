"""One compact clause naming a source's viewpoint, remit and observation date.

The interface already shows the reader a source's flags, provenance role and scope.
The model saw the grade and the flags but not the role or the remit, so an official
issuer, a participant and an aggregator read alike. This states them in the same
words the interface uses. Nothing here is a reliability finding: an unassessed source
stays unassessed, and a declared remit is a catalogue description, not verification.
"""

from __future__ import annotations

from ase.domain.evidence import EvidenceItem

MAX_REMIT_CHARS = 160
# The interface labels these two flags explicitly; the model must see them too.
VIEWPOINT_FLAGS = (
    ("state_controlled", "state-aligned outlet, so treat its claims as the state's position"),
    ("interested_party", "participant or interested party in what it reports"),
)
ROLE_VIEWPOINTS = {
    "originator": "official issuer of the record it publishes",
    "publisher": "publisher of its own reporting",
    "aggregator": "aggregator republishing other publishers",
    "platform": "platform carrying accounts whose reliability is not assessed",
    "unassessed": "viewpoint not assessed",
}


def _viewpoints(item: EvidenceItem) -> list[str]:
    flags = frozenset(item.flags)
    found = [text for flag, text in VIEWPOINT_FLAGS if flag in flags]
    role = item.source_rating.provenance_role if item.source_rating else "unassessed"
    found.append(ROLE_VIEWPOINTS.get(role, "viewpoint not assessed"))
    return found


def _reliability(item: EvidenceItem) -> str:
    rating = item.source_rating
    if rating is None or rating.status != "editorial" or rating.assessed_grade is None:
        return "source reliability unassessed"
    assessed = "publisher reliability assessed" if rating.publisher_reliability_assessed else (
        "publisher reliability not assessed"
    )  # fmt: skip
    return f"inherited editorial grade {rating.assessed_grade.value}, {assessed}"


def source_character(item: EvidenceItem) -> str:
    """Viewpoint, remit, reliability standing and observation date, in one bounded clause."""
    parts = [
        f"organisation {item.independence_key or 'unknown'}",
        *_viewpoints(item),
        _reliability(item),
    ]
    remit = (item.source_rating.scope if item.source_rating else "") or "remit not recorded"
    parts.append(f"remit: {remit[:MAX_REMIT_CHARS].rstrip()}")
    if item.observed_at is not None:
        parts.append(f"observed {item.observed_at.strftime('%Y-%m-%d %H:%M UTC')}")
    return " Source character: " + "; ".join(parts) + "."

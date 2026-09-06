"""Conservative item grading independent of source reliability.

Automated headline/place matches identify related topics, not independent agreement.
Without claim-level verification they cannot justify grades 1, 4 or 5. Instrument
metadata can support provisional grade 2; it does not prove a claim has been verified.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ase.domain.event_similarity import (
    GEO_RADIUS_KM,
    TEXT_WINDOW,
    distance_km,
    jaccard,
    title_tokens,
)
from ase.domain.events import Credibility, Event
from ase.domain.source_provenance import ProvenanceItem, SourceProfile, organisation_groups
from ase.domain.story_clustering import build_stories, story_id_for

__all__ = [
    "Graded",
    "SourceProfile",
    "build_stories",
    "cutoff_for",
    "distance_km",
    "grade_events",
    "jaccard",
    "title_tokens",
]


@dataclass(frozen=True, slots=True)
class Graded:
    event: Event
    credibility: Credibility
    rationale: str
    story_id: str

    @property
    def changed(self) -> bool:
        event = self.event
        return (
            event.credibility is not self.credibility
            or event.story_id != self.story_id
            or event.grade_rationale != self.rationale
        )

    def apply(self) -> Event:
        return self.event.with_changes(
            credibility=self.credibility, grade_rationale=self.rationale, story_id=self.story_id
        )


def _has_context(event: Event, pool: Sequence[Event]) -> int:
    count = 0
    for other in pool:
        if other.id == event.id or other.category is not event.category:
            continue
        if abs(other.published_at - event.published_at) > TEXT_WINDOW:
            continue
        same_country = event.country_iso is not None and other.country_iso == event.country_iso
        near = (
            event.point is not None
            and other.point is not None
            and distance_km(event.point, other.point) <= GEO_RADIUS_KM
        )
        if same_country or near:
            count += 1
    return count


# These English surface cues request review. They cannot establish a contradiction,
# distinguish quotation from assertion, or assess other languages without translation.
_QUALIFICATION = re.compile(
    r"\b(?:no|not|never|without|deny|denies|denied|denial|false|falsely|"
    r"unconfirmed|unverified|alleged|reportedly|disputed|debunked|hoax|fake|"
    r"rumou?r|could|might)\b|n['\u2019]t\b",
    re.IGNORECASE,
)


def _qualified(event: Event) -> bool:
    return _QUALIFICATION.search(event.title_en or event.title) is not None


def _grade_single(
    event: Event, profile: SourceProfile | None, pool: Sequence[Event]
) -> tuple[Credibility, str]:
    flags = profile.flags if profile is not None else frozenset()
    if event.language != "en" and not event.title_en:
        return Credibility.CANNOT_BE_JUDGED, "Untranslated item; claim agreement not verified"
    if _qualified(event):
        return (
            Credibility.CANNOT_BE_JUDGED,
            "Headline contains negation or qualification; claim agreement not verified",
        )
    if "state_controlled" in flags or "state_controlled" in event.tags:
        return (
            Credibility.POSSIBLY_TRUE,
            "State-controlled outlet, uncorroborated: treat as the government's position",
        )
    if "interested_party" in flags:
        return Credibility.POSSIBLY_TRUE, "Interested party, uncorroborated"
    if profile is not None and (profile.instrument or "authoritative" in flags):
        return (
            Credibility.PROBABLY_TRUE,
            "Provisional instrument or authoritative-source assessment; not independently verified",
        )
    context = _has_context(event, pool)
    rationale = (
        f"Area/category context ({context} other item(s)) does not establish corroboration"
        if context
        else "Single source; claim agreement not verified"
    )
    return Credibility.CANNOT_BE_JUDGED, rationale


def grade_events(events: Sequence[Event], profiles: Mapping[str, SourceProfile]) -> list[Graded]:
    """Grade cautiously: related topics and declared provenance never verify a claim.

    Mixed negation/qualification cues lower the whole topic group to unassessed. That
    review signal intentionally errs on the side of uncertainty. It does not choose
    which headline is true, and absence of a cue does not prove claim agreement.
    """
    graded: list[Graded] = []
    for story in build_stories(events):
        story_id = story_id_for(story)
        groups = organisation_groups(
            [
                ProvenanceItem(
                    event.id,
                    profiles[event.source_id].independence_key
                    if event.source_id in profiles
                    else None,
                    event.title_en or event.title,
                    event.content_hash,
                )
                for event in story
            ]
        )
        mixed_wording = len({_qualified(event) for event in story}) > 1
        for event in story:
            credibility, rationale = _grade_single(event, profiles.get(event.source_id), events)
            if mixed_wording:
                credibility = Credibility.CANNOT_BE_JUDGED
                rationale = (
                    "Related headlines differ in negation or qualification; "
                    "possible conflicting wording requires review"
                )
            if len(story) > 1:
                rationale += (
                    f"; related topic across {len(groups.known_groups)} declared organisation "
                    "group(s); independent sourcing and claim agreement not verified"
                )
            if groups.possible_copies:
                rationale += "; near-identical headlines or content may be copies, grouped once"
            graded.append(Graded(event, credibility, rationale, story_id))
    return graded


def cutoff_for(now: datetime) -> datetime:
    return now - TEXT_WINDOW

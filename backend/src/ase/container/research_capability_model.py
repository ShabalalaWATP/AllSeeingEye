"""Shared values for reviewed structured source capabilities."""

from dataclasses import dataclass

from ase.domain.source_capabilities import CapabilityPrerequisite, CapabilitySupport
from ase.domain.source_capabilities import CapabilityScope as Scope
from ase.domain.source_capabilities import ContentCapability as Content
from ase.domain.source_capabilities import DateSupport as Dates
from ase.domain.source_capabilities import ExecutionRoute as Route
from ase.domain.source_capabilities import LanguageSupport as Language


@dataclass(frozen=True, slots=True)
class CapabilityProfile:
    family: str
    support: CapabilitySupport
    content: Content = Content.STRUCTURED
    route: Route = Route.PUBLIC_RESEARCH
    prerequisites: tuple[CapabilityPrerequisite, ...] = ()
    unknown_origin: bool = False


def _profile(
    family: str,
    scopes: tuple[Scope, ...],
    date: Dates | tuple[Dates, ...],
    constraints: str,
    *,
    prerequisite: CapabilityPrerequisite | None = None,
    english_terms: bool = False,
    unknown_origin: bool = False,
    content: Content = Content.STRUCTURED,
    route: Route = Route.PUBLIC_RESEARCH,
) -> CapabilityProfile:
    return CapabilityProfile(
        family,
        CapabilitySupport(
            scopes,
            date if isinstance(date, tuple) else (date,),
            ("en",) if english_terms else (),
            Language.ENGLISH_TERMS if english_terms else Language.NOT_FILTERED,
            constraints,
        ),
        content,
        route,
        (prerequisite,) if prerequisite else (),
        unknown_origin,
    )

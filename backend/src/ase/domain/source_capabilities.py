"""Versioned source inventory values, never a promise of coverage or permission to collect."""

from dataclasses import dataclass
from enum import StrEnum

from ase.domain.research_brief_values import stable_id

CAPABILITY_POLICY_VERSION = "ase-source-capabilities-v1"


class ExecutionRoute(StrEnum):
    PUBLIC_RESEARCH = "public_research"
    RETAINED_AREA = "retained_area"
    PRIVATE_DOCUMENT = "private_document"
    PRIVATE_MEDIA = "private_media"
    FRESH_WEB = "fresh_web"


class CapabilityScope(StrEnum):
    TOPIC = "topic"
    COUNTRY_CONTEXT = "country_context"
    AREA = "area"
    COMPANY = "company"
    DOMAIN = "domain"
    PRIVATE_INPUT = "private_input"


class DateSupport(StrEnum):
    PUBLICATION_INTERVAL = "publication_interval"
    CURRENT_SNAPSHOT = "current_snapshot"
    RECORDED_INTERVAL = "recorded_interval"
    RESEARCH_INTERVAL = "research_interval"
    ANNUAL_PERIODS = "annual_periods"
    INPUT_METADATA = "input_metadata"


class ContentCapability(StrEnum):
    DISCOVERY = "discovery_metadata"
    STRUCTURED = "structured_records"
    RETAINED = "retained_observations"
    PRIVATE_PASSAGES = "private_passages"
    PRIVATE_MEDIA = "private_media_metadata"


class LanguageSupport(StrEnum):
    CONFIGURED = "configured_language"
    ENGLISH_TERMS = "english_terms"
    NOT_FILTERED = "not_filtered"


class PrerequisiteKind(StrEnum):
    API_KEY = "api_key"
    ACKNOWLEDGEMENT = "acknowledgement"
    SNAPSHOT = "snapshot"
    CATALOGUE = "catalogue"
    RUNTIME = "runtime"
    MODEL = "model"
    RETAINED_STORE = "retained_store"
    PRIVATE_INPUT = "private_input"


@dataclass(frozen=True, slots=True)
class CapabilityPrerequisite:
    kind: PrerequisiteKind
    setting: str | None
    optional: bool = False


@dataclass(frozen=True, slots=True)
class CapabilitySupport:
    """Coarse declared support. Provider.supports and item-level checks remain authoritative.

    Country context is a selection capability, never precise incident geography.
    Configured languages are not detected article languages or translation support.
    Date support describes filtering semantics, never archive completeness.
    """

    scopes: tuple[CapabilityScope, ...]
    dates: tuple[DateSupport, ...]
    languages: tuple[str, ...]
    language_policy: LanguageSupport
    constraints: str


@dataclass(frozen=True, slots=True)
class SourceCapability:
    id: str
    name: str
    family: str
    route: ExecutionRoute
    content: ContentCapability
    support: CapabilitySupport
    origin_group: str | None
    limitations: tuple[str, ...]
    prerequisites: tuple[CapabilityPrerequisite, ...] = ()
    control_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        stable_id(self.id, "capability.id")
        if self.id.startswith("gap."):
            raise ValueError("A declared gap cannot be an executable capability")
        if not self.name or not self.support.constraints or not self.limitations:
            raise ValueError("Capabilities require names, support constraints and limitations")

    @property
    def provider_id(self) -> str | None:
        """Only these routes belong to the bounded research provider factory."""
        if self.route in (ExecutionRoute.PUBLIC_RESEARCH, ExecutionRoute.RETAINED_AREA):
            return self.id
        return None


@dataclass(frozen=True, slots=True)
class CapabilityRef:
    id: str

    def __post_init__(self) -> None:
        stable_id(self.id, "capability_ref.id")
        if self.id.startswith("gap."):
            raise ValueError("Use a gap reference for unavailable coverage")


@dataclass(frozen=True, slots=True)
class GapRef:
    id: str

    def __post_init__(self) -> None:
        stable_id(self.id, "gap_ref.id")
        if not self.id.startswith("gap."):
            raise ValueError("Gap references use the gap namespace")


@dataclass(frozen=True, slots=True)
class UnavailableCapabilityGap:
    """Unimplemented research coverage, deliberately without a provider ID."""

    id: str
    name: str
    reason: str
    related_source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        GapRef(self.id)
        if not self.name or not self.reason:
            raise ValueError("Coverage gaps require a name and reason")


@dataclass(frozen=True, slots=True)
class SourceBundle:
    id: str
    name: str
    references: tuple[CapabilityRef | GapRef, ...]

    def __post_init__(self) -> None:
        stable_id(self.id, "bundle.id")
        if (
            not isinstance(self.references, tuple)
            or not self.references
            or len(self.references) > 256
            or any(not isinstance(ref, (CapabilityRef, GapRef)) for ref in self.references)
        ):
            raise ValueError("Bundles require one to 256 typed references")
        if len({ref.id for ref in self.references}) != len(self.references):
            raise ValueError("Bundle references must be unique")

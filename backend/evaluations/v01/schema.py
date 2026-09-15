"""Bounded, versioned packets and assistant-authored expectations for offline review."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Domain = Literal[
    "conflict", "cyber", "economy", "disaster_humanitarian", "company_policy", "custom_area"
]
Split = Literal["development", "held_out"]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,79}$")]
Text = Annotated[str, Field(min_length=1, max_length=2000)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Indicator = Literal["name_mismatch", "date_mismatch", "number_mismatch", "negation_mismatch"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def packet_digest(title: str, summary: str) -> str:
    return hashlib.sha256(f"{title}\n{summary}".encode()).hexdigest()


class PacketItem(StrictModel):
    id: Identifier
    source_id: Identifier
    source_name: Annotated[str, Field(min_length=1, max_length=160)]
    origin_id: Identifier
    origin_basis: Literal["explicit_synthetic_assignment"]
    title: Annotated[str, Field(min_length=1, max_length=300)]
    summary: Text
    content_sha256: Digest
    url: Annotated[str, Field(pattern=r"^https://example\.invalid/[a-z0-9/_-]{1,200}$")]
    language: Annotated[str, Field(pattern=r"^[a-z]{2}$")]
    published_at: AwareDatetime | None
    retrieved_at: AwareDatetime
    publication_precision: Literal["instant", "day", "month", "unknown"]
    country: Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
    evidence_role: Literal["support", "counterevidence", "context", "unverified_claim"]
    limitations: tuple[Text, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def consistent_packet(self) -> Self:
        if self.content_sha256 != packet_digest(self.title, self.summary):
            raise ValueError("Packet content differs from its frozen digest")
        if (self.publication_precision == "instant") != (self.published_at is not None):
            raise ValueError("Partial or unknown dates must not acquire an invented instant")
        return self


class ExpectedPassage(StrictModel):
    packet_id: Identifier
    packet_sha256: Digest
    text: Annotated[str, Field(min_length=1, max_length=1200)]


class Requirement(StrictModel):
    id: Identifier
    question: Text
    useful_packet_ids: tuple[Identifier, ...] = Field(max_length=8)
    expected_passages: tuple[ExpectedPassage, ...] = Field(max_length=8)
    reference_state: Literal["answer", "partial", "disputed", "gap"]
    reference_outcome: Text

    def validate_passages(self, packet: dict[str, PacketItem]) -> None:
        for passage in self.expected_passages:
            source = packet.get(passage.packet_id)
            if source is None or source.content_sha256 != passage.packet_sha256:
                raise ValueError("Expected passage has no matching frozen source version")
            if passage.text not in source.summary:
                raise ValueError("Expected passage is absent from its frozen source version")


class Scope(StrictModel):
    countries: tuple[Annotated[str, Field(pattern=r"^[A-Z]{2}$")], ...] = Field(
        min_length=1, max_length=8
    )
    since: AwareDatetime
    until: AwareDatetime
    privacy_boundary: Text
    geographic_limit: Text

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.since >= self.until:
            raise ValueError("Evaluation time window is empty or reversed")
        return self


class QuoteProbe(StrictModel):
    kind: Literal["quote"]
    packet_id: Identifier
    proposed: Annotated[str, Field(min_length=1, max_length=1200)]
    expected_present: bool


class CueProbe(StrictModel):
    kind: Literal["literal_cues"]
    packet_id: Identifier
    claim: Annotated[str, Field(min_length=1, max_length=1600)]
    expected_indicators: tuple[Indicator, ...] = Field(max_length=4)


class TimeProbe(StrictModel):
    kind: Literal["publication_time"]
    packet_id: Identifier
    expected_admitted: bool


class AreaProbe(StrictModel):
    kind: Literal["point_in_area"]
    bounds: tuple[float, float, float, float]
    point: tuple[float, float]
    expected_inside: bool

    @model_validator(mode="after")
    def valid_coordinates(self) -> Self:
        west, south, east, north = self.bounds
        lon, lat = self.point
        if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError("Invalid evaluation bounds")
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("Invalid evaluation point")
        return self


Probe = Annotated[QuoteProbe | CueProbe | TimeProbe | AreaProbe, Field(discriminator="kind")]


class ClaimSnapshot(StrictModel):
    id: Identifier
    meaning: Text
    likelihood: Literal["unlikely", "realistic_possibility", "likely", "highly_likely"]
    horizon: Text | None
    support: tuple[Identifier, ...] = Field(max_length=8)
    opposition: tuple[Identifier, ...] = Field(max_length=8)
    significant_contradiction: bool = False


class EvidenceSnapshot(StrictModel):
    packet_id: Identifier
    correction_of_packet_id: Identifier | None = None
    relevant: bool = True


class EditionSnapshot(StrictModel):
    number: int = Field(ge=1, le=100)
    produced_at: AwareDatetime
    claims: tuple[ClaimSnapshot, ...] = Field(max_length=8)
    evidence: tuple[EvidenceSnapshot, ...] = Field(max_length=8)

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({item.id for item in self.claims}) != len(self.claims):
            raise ValueError("Duplicate edition claims")
        if len({item.packet_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("Duplicate edition evidence")
        return self


class EditionProbe(StrictModel):
    subscription_id: Identifier
    previous: EditionSnapshot
    current: EditionSnapshot
    coverage: Literal["complete_for_plan", "partial", "insufficient", "unknown"]
    attempted_providers: tuple[Identifier, ...] = Field(max_length=8)
    successful_providers: tuple[Identifier, ...] = Field(max_length=8)
    current_failed: bool = False
    expected_state: Literal[
        "failure",
        "insufficient_coverage",
        "significant_contradiction_or_correction",
        "assessment_changed",
        "new_evidence_broadly_unchanged_assessment",
        "no_new_relevant_captured_evidence",
    ]
    expected_reasons: tuple[Annotated[str, Field(min_length=1, max_length=80)], ...] = Field(
        min_length=1, max_length=20
    )
    expected_changed_claim_ids: tuple[Identifier, ...] = Field(max_length=8)
    expected_corrected_packet_ids: tuple[Identifier, ...] = Field(max_length=8)
    expected_novel_packet_ids: tuple[Identifier, ...] = Field(max_length=8)
    expected_syndicated_packet_ids: tuple[Identifier, ...] = Field(max_length=8)

    @model_validator(mode="after")
    def consecutive(self) -> Self:
        if self.current.number != self.previous.number + 1:
            raise ValueError("Edition comparisons must be consecutive")
        if self.current.produced_at <= self.previous.produced_at:
            raise ValueError("Edition production timestamps must increase")
        if not set(self.successful_providers) <= set(self.attempted_providers):
            raise ValueError("Successful providers were not attempted")
        return self


class ContractCase(StrictModel):
    schema_version: Literal["ase-v01-case-1"]
    id: Identifier
    domain: Domain
    split: Split
    requested_depth: Literal["basic", "deep", "advanced"]
    title: Text
    evidence_origin: Literal["synthetic_assistant_authored"]
    label_origin: Literal["assistant_authored_reference_expectations"]
    human_review_status: Literal["pending"]
    question: Text
    requirements: tuple[Requirement, ...] = Field(min_length=1, max_length=8)
    scope: Scope
    packet: tuple[PacketItem, ...] = Field(min_length=1, max_length=8)
    probes: tuple[Probe, ...] = Field(max_length=16)
    edition: EditionProbe | None = None
    known_pitfalls: tuple[Text, ...] = Field(min_length=1, max_length=12)
    acceptable_abstentions: tuple[Text, ...] = Field(min_length=1, max_length=8)
    analytical_review_questions: tuple[Text, ...] = Field(min_length=1, max_length=8)

    @model_validator(mode="after")
    def references(self) -> Self:
        packet_ids = {item.id for item in self.packet}
        if len(packet_ids) != len(self.packet):
            raise ValueError("Duplicate packet identifiers")
        if len({item.id for item in self.requirements}) != len(self.requirements):
            raise ValueError("Duplicate requirement identifiers")
        used = {key for item in self.requirements for key in item.useful_packet_ids}
        packet = {item.id: item for item in self.packet}
        for requirement in self.requirements:
            requirement.validate_passages(packet)
        used.update(probe.packet_id for probe in self.probes if not isinstance(probe, AreaProbe))
        if self.edition:
            for snapshot in (self.edition.previous, self.edition.current):
                for evidence in snapshot.evidence:
                    used.add(evidence.packet_id)
                    if evidence.correction_of_packet_id:
                        used.add(evidence.correction_of_packet_id)
                for claim in snapshot.claims:
                    used.update((*claim.support, *claim.opposition))
        if not used <= packet_ids:
            raise ValueError("Reference points outside the frozen packet")
        if not self.probes and self.edition is None:
            raise ValueError("A contract case requires an executable check")
        return self


class ManifestEntry(StrictModel):
    id: Identifier
    domain: Domain
    split: Split
    path: Annotated[str, Field(pattern=r"^cases/[a-z][a-z0-9_-]{0,79}\.json$")]
    sha256: Digest


class Manifest(StrictModel):
    schema_version: Literal["ase-v01-manifest-1"]
    frozen_at: AwareDatetime
    label_origin: Literal["assistant_authored_reference_expectations"]
    human_review_status: Literal["pending"]
    split_policy: Text
    held_out_limitations: Text
    cases: tuple[ManifestEntry, ...] = Field(min_length=60, max_length=60)

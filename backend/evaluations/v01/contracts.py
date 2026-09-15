"""Exercise existing pure production contracts without adapters, settings or network access."""

from dataclasses import asdict, dataclass
from typing import Any

from ase.domain.citation_checks import exact_excerpt, mismatch_indicators
from ase.domain.events import BoundingBox, Category, Event, Point, Reliability
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_matches_time
from ase.domain.research_changes import (
    ComparisonClaim,
    ComparisonEvidence,
    ComparisonInput,
    classify_research_change,
)
from ase.domain.subscription_editions import EditionCoverage
from evaluations.v01.schema import (
    AreaProbe,
    ClaimSnapshot,
    ContractCase,
    CueProbe,
    EvidenceSnapshot,
    PacketItem,
    QuoteProbe,
    TimeProbe,
)


@dataclass(frozen=True)
class CheckResult:
    contract: str
    passed: bool
    expected: Any
    actual: Any
    packet_id: str | None = None


def _event(item: PacketItem) -> Event:
    return Event(
        id=item.id,
        source_id=item.source_id,
        category=Category.NEWS,
        subtype="synthetic_evaluation",
        title=item.title,
        summary=item.summary,
        published_at=item.published_at,
        observed_at=item.retrieved_at,
        reliability=Reliability.F,
        language=item.language,
        country_iso=item.country,
        content_hash=item.content_sha256,
        url=item.url,
    )


def _claims(value: tuple[ClaimSnapshot, ...]) -> tuple[ComparisonClaim, ...]:
    return tuple(
        ComparisonClaim(
            claim_id=item.id,
            meaning_fingerprint=item.meaning,
            likelihood_band=item.likelihood,
            horizon_fingerprint=item.horizon,
            support=item.support,
            opposition=item.opposition,
            significant_contradiction=item.significant_contradiction,
        )
        for item in value
    )


def _evidence(
    value: tuple[EvidenceSnapshot, ...], packet: dict[str, PacketItem]
) -> tuple[ComparisonEvidence, ...]:
    return tuple(
        ComparisonEvidence(
            evidence_id=item.packet_id,
            content_hash=packet[item.packet_id].content_sha256,
            origin_id=packet[item.packet_id].origin_id,
            canonical_url=packet[item.packet_id].url,
            correction_of_hash=(
                packet[item.correction_of_packet_id].content_sha256
                if item.correction_of_packet_id
                else None
            ),
            relevant=item.relevant,
        )
        for item in value
    )


def check_edition(case: ContractCase) -> tuple[CheckResult, ...]:
    edition = case.edition
    if edition is None:
        return ()
    packet = {item.id: item for item in case.packet}
    actual = classify_research_change(
        ComparisonInput(
            previous_claims=_claims(edition.previous.claims),
            current_claims=_claims(edition.current.claims),
            previous_evidence=_evidence(edition.previous.evidence, packet),
            current_evidence=_evidence(edition.current.evidence, packet),
            coverage=EditionCoverage(edition.coverage),
            current_failed=edition.current_failed,
            attempted_providers=edition.attempted_providers,
            successful_providers=edition.successful_providers,
        )
    )
    fields = (
        ("edition_state", edition.expected_state, actual.state.value),
        (
            "edition_reasons",
            sorted(edition.expected_reasons),
            sorted(reason.value for reason in actual.reasons),
        ),
        ("edition_changed_claims", edition.expected_changed_claim_ids, actual.changed_claim_ids),
        (
            "edition_corrections",
            edition.expected_corrected_packet_ids,
            actual.corrected_evidence_ids,
        ),
        ("edition_novel_evidence", edition.expected_novel_packet_ids, actual.novel_evidence_ids),
        (
            "edition_syndication",
            edition.expected_syndicated_packet_ids,
            actual.syndicated_duplicate_ids,
        ),
    )
    return tuple(
        CheckResult(name, expected == result, expected, result) for name, expected, result in fields
    )


def check_case(case: ContractCase) -> tuple[CheckResult, ...]:
    """References are supplied only to the scorer, never to the production functions."""
    packet = {item.id: item for item in case.packet}
    results: list[CheckResult] = []
    for probe in case.probes:
        if isinstance(probe, QuoteProbe):
            excerpt = exact_excerpt("summary", packet[probe.packet_id].summary, probe.proposed)
            present = excerpt is not None
            results.append(
                CheckResult(
                    "exact_excerpt_presence",
                    present == probe.expected_present,
                    probe.expected_present,
                    present,
                    probe.packet_id,
                )
            )
            if excerpt is not None:
                source = packet[probe.packet_id].summary
                retained = source[excerpt.start : excerpt.end] == excerpt.text == probe.proposed
                results.append(
                    CheckResult(
                        "exact_excerpt_offsets",
                        retained,
                        True,
                        retained,
                        probe.packet_id,
                    )
                )
        elif isinstance(probe, CueProbe):
            indicators = tuple(
                sorted(
                    item.kind
                    for item in mismatch_indicators(probe.claim, packet[probe.packet_id].summary)
                )
            )
            expected = tuple(sorted(probe.expected_indicators))
            results.append(
                CheckResult(
                    "literal_cue_contract",
                    expected == indicators,
                    expected,
                    indicators,
                    probe.packet_id,
                )
            )
        elif isinstance(probe, TimeProbe):
            admitted = evidence_matches_time(
                _event(packet[probe.packet_id]),
                EvidenceTimeBasis.PUBLICATION,
                case.scope.since,
                case.scope.until,
            )
            results.append(
                CheckResult(
                    "publication_time_admission",
                    admitted == probe.expected_admitted,
                    probe.expected_admitted,
                    admitted,
                    probe.packet_id,
                )
            )
        elif isinstance(probe, AreaProbe):
            inside = BoundingBox(*probe.bounds).contains(Point(*probe.point))
            results.append(
                CheckResult(
                    "point_in_declared_area",
                    inside == probe.expected_inside,
                    probe.expected_inside,
                    inside,
                )
            )
    results.extend(check_edition(case))
    return tuple(results)


def serialise_checks(checks: tuple[CheckResult, ...]) -> list[dict[str, Any]]:
    return [asdict(item) for item in checks]

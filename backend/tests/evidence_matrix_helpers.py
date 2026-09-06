"""Synthetic frozen evidence for deterministic contribution-policy tests."""

from dataclasses import replace

from ase.domain.doctrine import Confidence, Probability
from ase.domain.events import Credibility, Reliability
from ase.domain.evidence import EvidenceItem
from ase.domain.reports import KeyJudgement
from feeds_helpers import NOW, make_event


def item(label: str, grade: str = "A2", organisation: str | None = None) -> EvidenceItem:
    titles = {
        "E1": "Satellite imagery reveals vacant camp",
        "E2": "Witness records transport departure",
        "E3": "Intercepted message contradicts timeline",
        "E4": "Rainfall totals northern catchments",
    }
    event = make_event(label, title=titles.get(label, label)).with_changes(
        reliability=Reliability(grade[0]),
        credibility=Credibility(int(grade[1])),
        content_hash=label,
    )
    return EvidenceItem.from_event(
        label,
        event,
        NOW,
        source_name=label,
        independence_key=organisation if organisation is not None else label,
    )


def judgement(*support: str, opposition: tuple[str, ...] = ()) -> KeyJudgement:
    return KeyJudgement(
        id="KJ1",
        statement="We assess it is likely that units leave.",
        probability=Probability.LIKELY,
        confidence=Confidence.HIGH,
        confidence_statement="Synthetic model rationale.",
        supporting_evidence=tuple(support),
        contradicting_evidence=opposition,
    )


def copy(item_: EvidenceItem, label: str, organisation: str) -> EvidenceItem:
    return replace(item_, label=label, event_id=label, independence_key=organisation)

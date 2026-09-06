"""Frozen model challenge and collection receipts, never independent corroboration."""

from dataclasses import dataclass
from typing import Literal

from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.research import CollectionAttempt

CHALLENGE_METHOD = "ase-report-challenge-v1"
CHALLENGE_LIMITATIONS = (
    "Queries and contrarian views are model-generated, not independent evidence or verification.",
    "Empty, failed or skipped searches do not confirm a judgement or prove counterevidence absent.",
    "Searches target the initial statements. Final judgements may change "
    "after reselection and redrafting.",
    "Advocacy uses final frozen snippets; substantive support and alternative "
    "explanations remain unverified.",
)


@dataclass(frozen=True, slots=True)
class ChallengeSearch:
    judgement_id: str
    statement: str
    terms: tuple[str, ...]
    status: Literal["attempted", "unavailable", "plan_missing", "budget_exhausted"]
    attempts: tuple[CollectionAttempt, ...] = ()
    collected_items: int = 0
    selected_event_ids: tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class ChallengeReview:
    judgement_id: str
    statement: str
    status: Literal["completed", "unavailable", "invalid"]
    advocacy: DevilsAdvocacy | None = None
    explanation: str = ""


@dataclass(frozen=True, slots=True)
class ReportChallenge:
    searches: tuple[ChallengeSearch, ...]
    reviews: tuple[ChallengeReview, ...]
    redrafted: bool = False
    method_version: str = CHALLENGE_METHOD
    request_limit: int = 6
    seconds_limit: int = 45
    limitations: tuple[str, ...] = CHALLENGE_LIMITATIONS

    def cited_labels(self) -> frozenset[str]:
        return frozenset(
            label
            for review in self.reviews
            if review.advocacy
            for label in review.advocacy.evidence
        )

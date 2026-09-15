"""Bounded original acquisition using injected guarded transport and isolated parsing.

This is a transient core, not a collector registration or durable budget ledger. Composition
must debit the shared E01/job allowance before use and persist consumed/uncertain reservations
across interruption. No default transport is supplied, so missing integration fails closed.
"""

import asyncio
import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from ase.application.access import AccessContext
from ase.application.ports import Clock
from ase.application.ports.research_inputs import DocumentImportPort
from ase.application.ports.source_controls import SourceAdmission
from ase.application.research.original_candidates import (
    AdmittedOriginalCandidate,
    OriginalCandidateCatalogue,
)
from ase.application.research.original_passages import OriginalDocumentVersion, extracted_version
from ase.application.research.original_policy import (
    MEDIA_EXTENSIONS,
    POLICY_VERSION,
    OriginalFetchRejected,
    OriginalFetchRequest,
    OriginalFetchResponse,
    OriginalSourcePolicy,
    validate_response,
)
from ase.domain.research import ResearchMode

GuardedOriginalFetch = Callable[[OriginalFetchRequest], Awaitable[OriginalFetchResponse]]
CurrentOriginalAccess = Callable[[], Awaitable[AccessContext]]


@dataclass(frozen=True, slots=True)
class OriginalReservation:
    transport_requests: int
    timeout_seconds: float
    id: UUID = field(default_factory=uuid4)


class OriginalAcquisitionBudget:
    """One run's remaining allowance; attempted documents include failed/uncertain work."""

    def __init__(
        self,
        mode: ResearchMode,
        *,
        remaining_source_operations: int,
        remaining_transport_requests: int,
        remaining_seconds: float,
        documents_attempted: int = 0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.document_ceiling = {
            ResearchMode.QUICK: 2,
            ResearchMode.DETAILED: 6,
            ResearchMode.ADVANCED: 10,
        }[mode]
        if (
            type(remaining_source_operations) is not int
            or not 0 <= remaining_source_operations <= 32
            or type(remaining_transport_requests) is not int
            or not 0 <= remaining_transport_requests <= 128
            or not 0 <= remaining_seconds <= 240
            or type(documents_attempted) is not int
            or not 0 <= documents_attempted <= self.document_ceiling
        ):
            raise ValueError("Invalid original acquisition allowance")
        self.source_operations_remaining = remaining_source_operations
        self.transport_requests_remaining = remaining_transport_requests
        self.documents_attempted = documents_attempted
        self._clock, self._deadline = monotonic, monotonic() + remaining_seconds
        self._pending: dict[UUID, OriginalReservation] = {}

    def reserve(self, policy: OriginalSourcePolicy) -> OriginalReservation | None:
        transport = policy.max_redirects + 1
        if (
            self.documents_attempted >= self.document_ceiling
            or self.source_operations_remaining < 1
            or self.transport_requests_remaining < transport
            or self._deadline - self._clock() < policy.timeout_seconds
        ):
            return None
        self.documents_attempted += 1
        self.source_operations_remaining -= 1
        self.transport_requests_remaining -= transport
        reservation = OriginalReservation(transport, policy.timeout_seconds)
        self._pending[reservation.id] = reservation
        return reservation

    def settle_known(self, reservation: OriginalReservation, used: int) -> None:
        """Only a completely validated transport receipt may release known unused requests."""
        if (
            not 1 <= used <= reservation.transport_requests
            or self._pending.get(reservation.id) != reservation
        ):
            raise ValueError("Invalid original transport accounting")
        del self._pending[reservation.id]
        self.transport_requests_remaining += reservation.transport_requests - used


@dataclass(frozen=True, slots=True)
class OriginalAcquisitionReceipt:
    candidate_id: str
    status: Literal["acquired", "headline_only"]
    reason: str
    documents_attempted: int
    source_operations: int
    transport_requests: int | None
    transport_requests_reserved: int
    passage_count: int
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True, slots=True)
class OriginalAcquisitionResult:
    receipt: OriginalAcquisitionReceipt
    document: OriginalDocumentVersion | None = None
    original_bytes: bytes = field(default=b"", repr=False)


class OriginalAcquisition:
    def __init__(
        self,
        catalogue: OriginalCandidateCatalogue,
        admission: SourceAdmission,
        current_access: CurrentOriginalAccess,
        parser: DocumentImportPort,
        clock: Clock,
        fetch: GuardedOriginalFetch | None = None,
    ) -> None:
        self.catalogue, self.admission, self.current_access = catalogue, admission, current_access
        self.parser, self.clock, self.fetch = parser, clock, fetch

    async def _candidate(
        self, candidate_id: str, previous: OriginalDocumentVersion | None = None
    ) -> AdmittedOriginalCandidate:
        access = await self.current_access()
        candidate = self.catalogue.get(candidate_id, access)
        if previous is not None:
            access.require_same_scope(
                candidate.owner_id, candidate.team_id, previous.owner_id, previous.team_id
            )
        return candidate

    async def acquire(  # noqa: PLR0911 - preserve distinct admission, parse and release failures
        self,
        candidate_id: str,
        policy: OriginalSourcePolicy,
        budget: OriginalAcquisitionBudget,
        *,
        previous: OriginalDocumentVersion | None = None,
    ) -> OriginalAcquisitionResult:
        """No arbitrary URL is accepted; caller chooses an already admitted candidate ID."""
        async with self.admission.guard():
            candidate = await self._candidate(candidate_id, previous)
            if not await self.admission.enabled(candidate.source_id):
                return _failure(candidate_id, "source_disabled")
            if policy.source_id != candidate.source_id or not policy.permits(
                candidate.requested_url, self.clock.now()
            ):
                return _failure(candidate_id, "policy_or_destination_not_permitted")
            if self.fetch is None:
                return _failure(candidate_id, "guarded_transport_unavailable")
            reservation = budget.reserve(policy)
            if reservation is None:
                return _failure(candidate_id, "insufficient_remaining_allowance")
        request = OriginalFetchRequest(
            candidate.requested_url,
            policy,
            policy.max_bytes,
            policy.max_redirects,
            reservation.timeout_seconds,
        )
        used: int | None = None
        stage = "fetch"
        try:
            async with asyncio.timeout(reservation.timeout_seconds):
                response = await self.fetch(request)
                retrieved_at = self.clock.now()
                reason = validate_response(response, request, policy, retrieved_at)
                if reason is not None:
                    return _failure(candidate_id, reason, reservation)
                used = len(response.hops)
                budget.settle_known(reservation, used)
                digest = hashlib.sha256(response.body).hexdigest()
                filename = f"original-{digest[:12]}{MEDIA_EXTENSIONS[response.media_type]}"
                stage = "parser"
                extraction = await self.parser.extract(response.body, filename, retrieved_at)
                if extraction.filename != filename:
                    return _failure(candidate_id, "parser_provenance_mismatch", reservation, used)
                document = extracted_version(
                    candidate, response, extraction, policy, retrieved_at, previous=previous
                )
        except TimeoutError:
            return _failure(candidate_id, f"{stage}_timeout", reservation, used)
        except OriginalFetchRejected as exc:
            return _failure(candidate_id, exc.reason, reservation, used)
        except Exception:
            # Transport/parser exceptions can contain document text, URLs or credentials.
            return _failure(candidate_id, f"{stage}_rejected", reservation, used)
        # Cancellation intentionally propagates. The pre-dispatch reservation is retained;
        # the isolated parser contract terminates its worker and releases transient bytes.
        async with self.admission.guard():
            await self._candidate(candidate_id)
            if not await self.admission.enabled(candidate.source_id):
                return _failure(
                    candidate_id, "source_disabled_after_acquisition", reservation, used
                )
            if not policy.permits(response.canonical_url, self.clock.now()):
                return _failure(candidate_id, "policy_expired_after_acquisition", reservation, used)
            return OriginalAcquisitionResult(
                OriginalAcquisitionReceipt(
                    candidate_id,
                    "acquired",
                    "original_passages_extracted",
                    1,
                    1,
                    used,
                    reservation.transport_requests,
                    len(document.passages),
                ),
                document,
                response.body,
            )


def _failure(
    candidate_id: str,
    reason: str,
    reservation: OriginalReservation | None = None,
    used: int | None = None,
) -> OriginalAcquisitionResult:
    attempted = int(reservation is not None)
    return OriginalAcquisitionResult(
        OriginalAcquisitionReceipt(
            candidate_id,
            "headline_only",
            reason,
            attempted,
            attempted,
            used if reservation is not None else 0,
            reservation.transport_requests if reservation is not None else 0,
            0,
        )
    )

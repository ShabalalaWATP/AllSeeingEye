"""Offline admitted source, transport and isolated-parser doubles for the E02 core."""

import hashlib
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ase.application.access import AccessContext
from ase.application.ports.research_inputs import InputExtraction
from ase.application.research.original_acquisition import (
    OriginalAcquisition,
    OriginalAcquisitionBudget,
)
from ase.application.research.original_candidates import OriginalCandidateCatalogue
from ase.application.research.original_policy import (
    OriginalFetchResponse,
    OriginalSourcePolicy,
    OriginalTransportHop,
)
from ase.domain.events import Category, Event, Reliability
from ase.domain.research import ResearchMode
from ase.domain.sources import SourceKind, SourceSpec
from ase.domain.users import Role, User

NOW = datetime(2026, 9, 14, 10, tzinfo=UTC)
SOURCE = "research_test_original"
URL = "https://publisher.example/report.txt"
ADDRESS = "93.184.216.34"
SPEC = SourceSpec(
    SOURCE,
    "Reviewed publisher",
    "Original issuer",
    Category.NEWS,
    SourceKind.API,
    "https://publisher.example",
    Reliability.F,
    timedelta(hours=24),
)


def access(owner_id: UUID) -> AccessContext:
    user = User(
        owner_id,
        "original@example.com",
        "Original reader",
        Role.USER,
        True,
        None,
        0,
        None,
        None,
        NOW,
        None,
    )
    return AccessContext(user, {}, {})


def event(**changes) -> Event:
    values = {
        "id": "admitted-event",
        "source_id": SOURCE,
        "category": Category.NEWS,
        "subtype": "headline",
        "title": "Original publisher headline",
        "published_at": None,
        "observed_at": NOW,
        "reliability": Reliability.F,
        "url": URL,
        "language": "fr",
        "summary": "Generated discovery summary must never become a passage.",
        "content_hash": "discovery-hash",
    }
    return Event(**(values | changes))


def catalogue(owner_id=None, **changes) -> OriginalCandidateCatalogue:
    values = {
        "events": (event(),),
        "owner_id": owner_id or uuid4(),
        "team_id": None,
        "admitted_source_ids": frozenset({SOURCE}),
        "source_specs": {SOURCE: SPEC},
        "requirement_ids": {"admitted-event": ("q1",)},
    }
    return OriginalCandidateCatalogue(**(values | changes))


def policy(**changes) -> OriginalSourcePolicy:
    values = {
        "source_id": SOURCE,
        "policy_id": "reviewed-policy-1",
        "allowed_origins": ("https://publisher.example",),
        "reviewed_at": NOW - timedelta(hours=1),
        "valid_until": NOW + timedelta(days=1),
        "terms": "allowed",
        "robots": "allowed",
        "permitted_use": "Short attributed passages for private research; retain for one day.",
    }
    return OriginalSourcePolicy(**(values | changes))


def response(body=b"Exact original passage.", **changes) -> OriginalFetchResponse:
    values = {
        "requested_url": URL,
        "canonical_url": URL,
        "hops": (OriginalTransportHop(URL, (ADDRESS,), ADDRESS, 200),),
        "media_type": "text/plain",
        "body": body,
        "wire_body_bytes": len(body),
    }
    return OriginalFetchResponse(**(values | changes))


def extraction(
    body, filename="original.txt", references=("Text line 1",), texts=None, media_type="text/plain"
) -> InputExtraction:
    digest = hashlib.sha256(body).hexdigest()
    texts = texts if texts is not None else (body.decode(),)
    events = tuple(
        event(
            id=f"passage-{index}",
            source_id="research_import",
            subtype="document_passage",
            url=None,
            summary=text,
            language="und",
            attributes={"source_reference": reference, "original_sha256": digest},
        )
        for index, (reference, text) in enumerate(zip(references, texts, strict=True))
    )
    return InputExtraction(filename, media_type, digest, events, ())


class Admission:
    allowed = True
    depth = 0

    @asynccontextmanager
    async def guard(self):
        self.depth += 1
        try:
            yield
        finally:
            self.depth -= 1

    async def enabled(self, source_id):
        assert source_id == SOURCE
        return self.allowed

    async def enabled_many(self, source_ids):
        return dict.fromkeys(source_ids, self.allowed)


class Clock:
    value = NOW

    def now(self):
        return self.value


class Parser:
    calls = 0

    async def extract(self, body, filename, captured_at):
        self.calls += 1
        assert captured_at == NOW
        return extraction(body, filename)


class Harness:
    def __init__(self):
        self.catalogue = catalogue()
        self.candidate = next(iter(self.catalogue.candidates.values()))
        self.access = access(self.catalogue.owner_id)
        self.admission, self.parser, self.clock = Admission(), Parser(), Clock()
        self.response, self.requests = response(), []
        self.policy = policy()
        self.budget = OriginalAcquisitionBudget(
            ResearchMode.QUICK,
            remaining_source_operations=6,
            remaining_transport_requests=12,
            remaining_seconds=45,
        )
        self.service = OriginalAcquisition(
            self.catalogue,
            self.admission,
            self.current_access,
            self.parser,
            self.clock,
            self.fetch,
        )

    async def current_access(self):
        assert self.admission.depth == 1
        return self.access

    async def fetch(self, request):
        assert self.admission.depth == 0
        self.requests.append(request)
        return self.response

    async def acquire(self, **kwargs):
        return await self.service.acquire(self.candidate.id, self.policy, self.budget, **kwargs)

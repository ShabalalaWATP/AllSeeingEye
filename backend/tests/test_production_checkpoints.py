"""Resumption restores one frozen evidence packet before any section is drafted."""

from dataclasses import replace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.challenge_models import ChallengeModelDraft
from ase.application.reports.drafting import Draft
from ase.application.reports.frozen_challenge import FROZEN_COLLECTION_GAP
from ase.application.reports.production import Producer
from ase.application.reports.production_checkpoint import collection_from_dict, collection_to_dict
from ase.application.reports.sections import SectionIncomplete
from ase.domain.challenge import ChallengeReview
from ase.domain.direction import Direction
from ase.domain.reports import ReportStatus, parse_body
from ase.domain.research import ResearchMode, ResearchQuery
from production_integration_helpers import RecordingUsage, StageGateway, production_job
from report_helpers import filled_store, good_body
from test_automatic_claim_storage import pending_for


class Checkpoints:
    def __init__(self):
        self.value = None
        self.writes = 0
        self.section_checkpoints = object()

    async def load_collection(self):
        return collection_from_dict(self.value) if self.value is not None else None

    async def save_collection(self, snapshot):
        self.value = collection_to_dict(snapshot)
        self.writes += 1


async def test_initial_packet_saved_before_draft_and_resume_does_not_recollect(container, user):
    job = production_job(user, container.cipher)
    job = replace(job, request=replace(job.request, devils_advocacy=False))
    gateway, checkpoints = StageGateway(), Checkpoints()
    stores = [filled_store(), InMemoryEventStore()]
    packets = []

    async def drafted(*args, **kwargs):
        assert checkpoints.value is not None
        assert kwargs["checkpoints"] is checkpoints.section_checkpoints
        packets.append(args[7])
        return Draft(body=parse_body(good_body()), model="sections", prompt_tokens=2)

    async def profile_for(_role):
        return job.profile

    with (
        patch("ase.application.reports.production.draft_sections", side_effect=drafted),
        patch(
            "ase.application.reports.production.draft_body",
            side_effect=AssertionError("whole body called"),
        ),
    ):
        for store in stores:
            producer = Producer(
                store=store,
                source_profiles={},
                cipher=container.cipher,
                gateway=gateway,
                usage=RecordingUsage(),
            )
            version = await producer.produce(job, profile_for, checkpoints=checkpoints)
            assert version.evidence == packets[0]
    assert len(packets[0]) > 0 and packets[0] == packets[1]
    assert checkpoints.writes == 1
    # The resumed run recollects nothing; each run still runs the entailment pass.
    assert gateway.calls == ["direction", "entailment", "entailment"]
    assert (await checkpoints.load_collection()).totals.prompt_tokens == 5


async def test_unanswered_section_requirement_publishes_as_needs_review(container, user):
    job = production_job(user, container.cipher)
    job = replace(
        job,
        direction=Direction("What changed?", eeis=("What happened?", "Who verified it?")),
        request=replace(job.request, devils_advocacy=False),
    )
    draft = Draft(
        body=parse_body(good_body()),
        supported_requirements=frozenset({"EEI-1"}),
    )
    checkpoints = Checkpoints()
    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=StageGateway(),
        usage=RecordingUsage(),
    )

    async def profile_for(_role):
        return job.profile

    with patch("ase.application.reports.production.draft_sections", AsyncMock(return_value=draft)):
        version = await producer.produce(job, profile_for, checkpoints=checkpoints)

    assert version.status is ReportStatus.NEEDS_REVIEW
    assert any(
        gap.eei == "EEI-2"
        and gap.text == "Not separately assessed from the retained evidence: Who verified it?"
        for gap in version.body.gaps
    )
    assert any(
        finding.rule == "requirement_coverage" and finding.location == "EEI-2"
        for finding in version.findings
    )


async def test_incomplete_section_propagates_with_collection_checkpoint_intact(container, user):
    job = production_job(user, container.cipher)
    checkpoints = Checkpoints()
    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=StageGateway(),
        usage=RecordingUsage(),
    )

    async def profile_for(_role):
        return job.profile

    with (
        patch(
            "ase.application.reports.production.draft_sections",
            side_effect=SectionIncomplete("S1", "token_budget_exhausted", Draft()),
        ),
        pytest.raises(SectionIncomplete),
    ):
        await producer.produce(job, profile_for, checkpoints=checkpoints)
    assert checkpoints.writes == 1 and checkpoints.value is not None


@pytest.mark.parametrize("mode", [ResearchMode.DETAILED, ResearchMode.ADVANCED])
async def test_detailed_resume_reviews_frozen_labels_without_new_collection(container, user, mode):
    job = production_job(user, container.cipher)
    job = replace(job, request=replace(job.request, research_mode=mode))
    checkpoints = Checkpoints()
    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=StageGateway(),
        usage=RecordingUsage(),
    )

    async def profile_for(_role):
        return job.profile

    draft = Draft(body=parse_body(good_body()))
    query = ResearchQuery("What changed?", job.period_from, job.period_to, mode=mode)
    prepared = AsyncMock(return_value=(filled_store(), None, query))
    reviews = tuple(
        ChallengeReview(row.id, row.statement, "completed") for row in draft.body.key_judgements
    )
    review = AsyncMock(return_value=ChallengeModelDraft(reviews=reviews, succeeded=True))
    with (
        patch("ase.application.reports.production.prepare_collection", prepared),
        patch("ase.application.reports.production.draft_sections", AsyncMock(return_value=draft)),
        patch("ase.application.reports.frozen_challenge.challenge_call", review),
        patch(
            "ase.application.reports.production.run_challenge",
            side_effect=AssertionError("recollection called"),
        ),
    ):
        version = await producer.produce(job, profile_for, checkpoints=checkpoints)
    snapshot = await checkpoints.load_collection()
    assert version.evidence == snapshot.selection.items
    assert review.call_args.kwargs["evidence"] == snapshot.selection.items
    assert version.challenge.redrafted is False
    assert all(row.status == "unavailable" for row in version.challenge.searches)
    assert FROZEN_COLLECTION_GAP in [gap.text for gap in version.body.gaps]


async def test_predetermined_ids_reach_automatic_claims_before_proposal_binding(container, user):
    job = production_job(user, container.cipher)
    job = replace(
        job,
        report_id=uuid4(),
        version_id=uuid4(),
        request=replace(job.request, devils_advocacy=False),
    )
    automatic = AutomaticClaims(
        StageGateway(), container.cipher, container.clock, container.limiter
    )
    prepared = []

    async def prepare(version, actor_id, _profile_for):
        assert version.id == job.version_id and version.report_id == job.report_id
        assert actor_id == user.id
        pending = pending_for(container, user, version)
        prepared.append(pending)
        return pending

    async def profile_for(_role):
        return job.profile

    producer = Producer(
        store=filled_store(),
        source_profiles={},
        cipher=container.cipher,
        gateway=StageGateway(),
        usage=RecordingUsage(),
        automatic_claims=automatic,
    )
    with patch.object(automatic, "prepare", side_effect=prepare):
        result = await producer.produce_with_claims(job, profile_for)
    assert result.version.id == job.version_id and result.version.report_id == job.report_id
    assert result.claims is prepared[0]
    assert result.claims.report_id == job.report_id and result.claims.version_id == job.version_id
    assert result.claims.revisions
    assert all(
        row.report_id == job.report_id and row.report_version_id == job.version_id
        for row in result.claims.revisions
    )

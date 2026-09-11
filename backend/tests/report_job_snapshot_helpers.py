"""Pure frozen-job fixtures with no provider, authentication or database effects."""

from dataclasses import replace
from uuid import UUID

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.model_routing import RoleProfiles
from ase.application.reports.production_types import Job, Totals
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope, report_window
from ase.application.reports.templates import template_for
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage, ReasoningEffort
from ase.domain.model_routing import ModelRoutingRecord, RoutedModel
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchFocus, ResearchMode
from ase.domain.users import Role, User
from feeds_helpers import NOW, make_event

ACTOR_ID = UUID("b127bddf-df4a-499b-9056-fb241f6c473a")
PROFILE_ID = UUID("bd44c5c9-38c6-419a-a48b-2d915c1e1030")
INPUT_ID = UUID("5fa6fc56-43b4-4625-9766-768aa10ea419")
PRIVATE_SENTINEL = "private-test-material-must-not-be-persisted"


def fixture_job(request: ReportRequest | None = None) -> Job:
    actor = User(
        ACTOR_ID,
        "test@example.invalid",
        "Fixture",
        Role.USER,
        True,
        PRIVATE_SENTINEL,
        0,
        None,
        None,
        NOW,
        None,
    )
    profile = LlmProfile(
        PROFILE_ID,
        "Fixture model",
        "https://fixture.invalid/v1",
        "model",
        PRIVATE_SENTINEL,
        "test",
        frozenset({LlmRole.ASSESSMENT}),
        4000,
        0.2,
        True,
        NOW,
        NOW,
        ReasoningEffort.MAX,
    )
    request = request or ReportRequest(
        "ask", question="What is known?", research_mode=ResearchMode.QUICK
    )
    template = template_for(request.template_id)
    return Job(
        actor,
        template,
        request,
        profile,
        NOW,
        report_window(request, template),
        "Frozen research question",
        report_scope(request, template),
        None,
    )


def fixture_routing(job: Job) -> RoleProfiles:
    profile = job.profile
    route = RoutedModel(
        LlmRole.ASSESSMENT,
        profile.id,
        profile.revision,
        profile.model,
        profile.reasoning_effort,
        profile.max_output_tokens,
        profile.temperature,
        profile.updated_at,
        profile.provider,
    )
    return RoleProfiles(
        ModelRoutingRecord("legacy", job.request.team_id, None, (route,)),
        ((LlmRole.ASSESSMENT, (("api_key_encrypted", PRIVATE_SENTINEL),)),),
    )


def fixture_evidence(label: str = "E1", key: str = "one") -> EvidenceItem:
    return EvidenceItem.from_event(
        label, make_event(key), NOW, source_name="Fixture source", independence_key="fixture"
    )


def private_job() -> Job:
    request = ReportRequest(
        "ask",
        question="Describe this image",
        research_mode=ResearchMode.QUICK,
        research_focus=ResearchFocus.MEDIA,
        research_input_id=INPUT_ID,
    )
    job = fixture_job(request)
    event = replace(
        make_event("private", title="Supplied image location hypothesis"), published_at=None
    )
    return replace(
        job,
        seed_events=(event,),
        direction=Direction("Describe this image"),
        seed_attempts=(
            CollectionAttempt("research-upload", "Private input", CollectionStatus.COMPLETED, 1),
        ),
        scope={
            **job.scope,
            "research_input": {
                "filename": "fixture.png",
                "media_type": "image/png",
                "sha256": "a" * 64,
                "imported_at": NOW.isoformat(),
                "extracted_items": 1,
                "limitations": ["Unverified"],
            },
        },
    )


def private_store() -> InMemoryEventStore:
    return InMemoryEventStore()


def fixture_totals() -> Totals:
    return Totals(
        200,
        50,
        12.0,
        usage=[
            LlmUsage(
                NOW,
                PROFILE_ID,
                ACTOR_ID,
                "report-direction",
                True,
                12.0,
                200,
                50,
                error=PRIVATE_SENTINEL,
                id=99,
            )
        ],
    )

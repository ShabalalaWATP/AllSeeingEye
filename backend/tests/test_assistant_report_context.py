"""Report Q&A stays on an exact, authorised, bounded saved edition."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.api.schemas_assistant import AssistantAnswerIn, AssistantAnswerOut
from ase.application.assistant.report_context import ReportContextReader
from ase.domain.assistant import AssistantQuestion, AssistantReportSelection
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.reports import parse_body
from assistant_helpers import Admission, Gateway, nothing, profile
from helpers import create_user
from report_documents_helpers import document_records
from report_helpers import good_body


async def _seed(container, owner):
    record, first = document_records(owner.id)
    second_body = parse_body(
        good_body(
            key_judgements=[
                {
                    "id": "KJ1",
                    "statement": "Shanghai port traffic is reported to have slowed.",
                    "probability": "likely",
                    "confidence": "low",
                    "confidence_statement": "Limited data.",
                    "supporting_evidence": ["E1"],
                }
            ],
            reporting=[],
            assessment=[],
            gaps=[],
        )
    )
    second = replace(first, id=uuid4(), number=2, body=second_body)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.reports.add(record, first)
        record.latest_version = 2
        await repos.reports.add_version(record, second)
        await repos.uow.commit()
    return record, first, second


def _question(report_id, version, text):
    return AssistantQuestion(
        text, scope="report", report=AssistantReportSelection(report_id, version)
    )


async def test_exact_old_edition_and_bounded_claim_evidence_selection(container, user):
    record, old, newer = await _seed(container, user)
    async with container.session_factory() as session:
        reader = ReportContextReader(container.get_report(session))
        context = await reader.collect(user, _question(record.id, 1, "El Fasher fighting"))
    assert context.report is not None
    assert (context.report.version, context.report.version_id) == (1, old.id)
    assert context.report.version_id != newer.id
    assert context.report.data_cutoff is None
    assert context.sources and len(context.sources) <= 14
    assert all(str(old.id) in row.record_id for row in context.sources)
    assert not any("Shanghai" in row.summary for row in context.sources)
    assert any(row.kind == "report_claim" for row in context.sources)
    assert any(row.kind == "report_evidence" for row in context.sources)
    assert all(row.id == f"E{index}" for index, row in enumerate(context.sources, 1))


async def test_absent_question_abstains_without_model_and_displays_exact_version(container, user):
    record, first, _ = await _seed(container, user)
    gateway = Gateway()
    container.llm = gateway
    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.report_reader = ReportContextReader(container.get_report(session))
        answer = await service.execute(
            user, _question(record.id, 1, "Martian uranium production"), check_session=nothing
        )
    assert answer.model is None and not gateway.calls
    assert answer.paragraphs[0].kind == "gap"
    assert "does not establish absence" in answer.paragraphs[0].text
    payload = AssistantAnswerOut.from_answer(answer).model_dump(mode="json")
    assert payload["report"]["version_id"] == str(first.id)
    assert payload["report"]["version"] == 1
    assert payload["report"]["title"] == record.title
    assert payload["report"]["data_cutoff"] is None


async def test_report_question_model_sees_only_selected_edition_and_no_live_search(container, user):
    record, first, _ = await _seed(container, user)
    await profile(container)
    gateway = Gateway()
    gateway.content = json.dumps(
        {
            "paragraphs": [
                {
                    "kind": "finding",
                    "text": "The report assesses fighting around El Fasher.",
                    "citations": ["E1"],
                },
            ]
        }
    )
    container.llm = gateway
    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.report_reader = ReportContextReader(container.get_report(session))
        answer = await service.execute(
            user, _question(record.id, 1, "El Fasher fighting"), check_session=nothing
        )
    assert answer.context.report and answer.context.report.version_id == first.id
    assert answer.continuation_id is None
    assert len(gateway.calls) == 1
    system, prompt = gateway.calls[0].messages
    assert "separate explicit research action" in system.content
    packet = json.loads(prompt.content)
    assert packet["report"]["version_id"] == str(first.id)
    assert packet["report"]["version"] == 1
    assert all(str(first.id) in source["record_id"] for source in packet["context"]["sources"])
    assert "Shanghai" not in prompt.content


async def test_report_access_and_version_are_rechecked_before_release(container, user):
    record, first, _ = await _seed(container, user)
    other = await create_user(
        container, email="other-report-reader@example.test", password="Pass1234!"
    )
    async with container.session_factory() as session:
        reader = ReportContextReader(container.get_report(session))
        with pytest.raises(NotFound):
            await reader.collect(other, _question(record.id, 1, "El Fasher"))
        context = await reader.collect(user, _question(record.id, 1, "El Fasher"))
        assert context.report and context.report.version_id == first.id
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.reports.delete(record.id)
        await repos.uow.commit()
    async with container.session_factory() as session:
        reader = ReportContextReader(container.get_report(session))
        with pytest.raises(NotFound):
            await reader.require_current(user, context.report)


async def test_deleted_report_during_model_cannot_release_answer(container, user):
    record, _, _ = await _seed(container, user)
    await profile(container)
    gateway = Gateway()

    async def delete_during_answer():
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.reports.delete(record.id)
            await repos.uow.commit()

    gateway.after = delete_during_answer
    container.llm = gateway
    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.report_reader = ReportContextReader(container.get_report(session))
        with pytest.raises(NotFound):
            await service.execute(
                user, _question(record.id, 1, "El Fasher fighting"), check_session=nothing
            )
    assert len(gateway.calls) == 1 and not container.assistant_capacity.active


async def test_disabled_frozen_evidence_source_blocks_release(container, user):
    record, _, _ = await _seed(container, user)
    await profile(container)
    admission = Admission()
    gateway = Gateway()
    container.source_admission = admission
    container.llm = gateway
    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.report_reader = ReportContextReader(container.get_report(session))
        context = await service.report_reader.collect(
            user, _question(record.id, 1, "El Fasher fighting")
        )
        evidence_ids = [row.source_id for row in context.sources if row.kind == "report_evidence"]
        assert evidence_ids
        gateway.after = lambda: _disable(admission, evidence_ids[0])
        with pytest.raises(InvalidRequest, match="disabled"):
            await service.execute(
                user, _question(record.id, 1, "El Fasher fighting"), check_session=nothing
            )
    assert len(gateway.calls) == 1


async def _disable(admission, source_id):
    admission.disabled.add(source_id)


@pytest.mark.parametrize(
    "invalid",
    [
        {"scope": "report"},
        {"scope": "report", "report": {"id": str(uuid4()), "version": 0}},
        {
            "scope": "report",
            "report": {"id": str(uuid4()), "version": 1},
            "continuation_id": "a" * 24,
        },
        {
            "scope": "report",
            "report": {"id": str(uuid4()), "version": 1},
            "source_categories": ["conflict"],
        },
        {"scope": "global", "report": {"id": str(uuid4()), "version": 1}},
    ],
)
def test_report_contract_rejects_ambiguous_or_live_scope(invalid):
    with pytest.raises(ValueError):
        AssistantAnswerIn(question="What happened?", **invalid)

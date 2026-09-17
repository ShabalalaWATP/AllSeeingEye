"""Real-container durable workflow fixtures with a deterministic, network-free model."""

import asyncio
import json
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.domain.llm import LlmResult
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from section_model_helpers import synthesis_body, topic_body


@pytest.fixture(name="settings")
def job_settings(settings, tmp_path):
    # A worker opens independent transactions. StaticPool's single in-memory
    # connection cannot represent their commit/rollback boundaries correctly.
    return settings.model_copy(
        update={"database_url": f"sqlite+aiosqlite:///{(tmp_path / 'jobs.sqlite').as_posix()}"}
    )


POST_DRAFT_STAGES = {
    "report_analysis": {
        "sections": [
            {
                "heading": "What this means",
                "text": "The reporting establishes movement and suggests intent.",
                "evidence": ["E1"],
            }
        ],
        "diagram": None,
    },
    "entailment": {"assessments": []},
    "contradiction_analysis": {"disagreements": []},
}


class JobGateway:
    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail or {}

    async def complete(self, base_url, key, model, request):
        if request.schema_name == "claim_proposals":
            self.calls.append(("claims", request))
            return LlmResult('{"claims": []}', model, 1, 10, 5)
        # The analysis pass and the review passes read the committed draft and only add
        # sections or reasons, so a job test answers them plainly and keeps the stages.
        if request.schema_name in POST_DRAFT_STAGES:
            self.calls.append((request.schema_name, request))
            return LlmResult(json.dumps(POST_DRAFT_STAGES[request.schema_name]), model, 1, 10, 5)
        assert request.schema_name in {"report_topic", "report_judgements", "report_context"}, (
            request.schema_name
        )
        payload = json.loads(request.messages[1].content)
        topic = payload["topic"]
        name = topic["id"] if topic else payload["synthesis_step"]
        self.calls.append((name, request))
        if name in self.fail:
            raise self.fail[name]
        body = topic_body(topic["evidence_labels"]) if topic else synthesis_body(["E1"])
        body = {key: body[key] for key in request.json_schema["properties"]}
        return LlmResult(json.dumps(body), model, 1, 10, 5)


async def prepared(container, client, *, fail=None, count=4):
    await seed_legacy_profile(
        container,
        {
            "name": "Job test profile",
            "base_url": "https://model.test/v1",
            "model": "fixture-model",
            "api_key": "synthetic-job-key",
            "roles": ["assessment"],
            "max_output_tokens": 32000,
            "temperature": 0.1,
        },
    )
    container.store.upsert(
        tuple(
            make_event(
                str(index),
                source_id="usgs_earthquakes",
                title=f"Instrument observation {index}",
                published_at=container.clock.now(),
                observed_at=container.clock.now(),
            )
            for index in range(count)
        )
    )
    gateway = JobGateway(fail)
    container.llm = gateway
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    return gateway, bearer(token)


async def submit(client, headers, *, request_id=None, report=None):
    response = await client.post(
        "/api/report-jobs",
        headers=headers,
        json={
            "request_id": str(request_id or uuid4()),
            "report": report or {"template": "intsum"},
        },
    )
    assert response.status_code == 202, response.text
    return response


async def work(container):
    worker = container.report_job_worker
    await worker.tick()
    tasks = [task for _, task in worker._running.values()]
    assert tasks
    await asyncio.wait_for(asyncio.gather(*tasks), 15)
    await worker.tick()


async def stored(container, job_id):
    async with container.session_factory() as session:
        return await SqlReportJobRepository(session).get(UUID(str(job_id)))

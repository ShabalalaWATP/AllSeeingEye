"""A confirmed invalid topic gets one bounded repair without replaying accepted work."""

import json

import pytest

from ase.application.report_jobs.budget import JobBudgetExhausted
from ase.application.reports.sections import SectionIncomplete
from ase.application.reports.sections.synthesis_contracts import (
    ALTERNATIVES,
    COLLECTION,
    JUDGEMENTS,
)
from section_model_helpers import Checkpoints, Gateway, run, topic_body


class InvalidTopicOnce(Gateway):
    def __init__(self, checkpoints, *, repair_error=None):
        super().__init__(checkpoints)
        self.repair_error = repair_error

    async def complete(self, base_url, key, model, request):
        payload = json.loads(request.messages[1].content)
        topic = payload["topic"]
        if topic and topic["id"] == "S2":
            prior = sum(name == "S2" for name, *_ in self.calls)
            if prior == 0:
                body = topic_body(["E999"])
                body["reporting"][0]["text"] = "private-invalid-output-marker"
                self.overrides["S2"] = json.dumps(body)
            elif self.repair_error:
                self.overrides["S2"] = self.repair_error
            else:
                self.overrides.pop("S2", None)
        return await super().complete(base_url, key, model, request)


async def test_invalid_topic_repairs_once_and_keeps_accepted_sections_and_usage():
    checkpoints = Checkpoints()
    gateway = InvalidTopicOnce(checkpoints)

    draft = await run(gateway, checkpoints)

    assert draft.body and not draft.has_errors
    assert [name for name, *_ in gateway.calls] == [
        "S1",
        "S2",
        "S2",
        "S3",
        JUDGEMENTS,
        ALTERNATIVES,
        COLLECTION,
    ]
    assert draft.attempts == 7 and draft.prompt_tokens == 70 and draft.completion_tokens == 35
    assert "previous step" in gateway.calls[2][1].messages[-1].content
    assert "private-invalid-output-marker" not in repr(checkpoints.rows) + repr(draft)
    writes = [row for _, name, row in checkpoints.writes if name == "S1"]
    assert [row.status for row in writes] == ["running", "completed"]
    assert (await run(gateway, checkpoints)).body == draft.body
    assert len(gateway.calls) == 7


async def test_second_invalid_topic_stops_without_a_retry_loop_or_discarding_saved_work():
    checkpoints = Checkpoints()
    gateway = Gateway(checkpoints, {"S2": json.dumps(topic_body(["E999"]))})

    with pytest.raises(SectionIncomplete) as caught:
        await run(gateway, checkpoints)

    assert caught.value.reason == "invalid_section"
    assert [name for name, *_ in gateway.calls] == ["S1", "S2", "S2"]
    assert caught.value.draft.prompt_tokens == 30 and caught.value.draft.completion_tokens == 15
    states = {name: row for (_, name), row in checkpoints.rows.items()}
    assert states["S1"].status == "completed"
    assert states["S2"].status == "incomplete" and "body" not in states["S2"].payload
    # An explicit resume makes one repair attempt, not another automatic retry pair.
    with pytest.raises(SectionIncomplete):
        await run(gateway, checkpoints)
    assert [name for name, *_ in gateway.calls].count("S2") == 3


async def test_topic_repair_cannot_bypass_the_existing_report_allowance():
    checkpoints = Checkpoints()
    gateway = InvalidTopicOnce(checkpoints, repair_error=JobBudgetExhausted())

    with pytest.raises(JobBudgetExhausted):
        await run(gateway, checkpoints)

    assert [name for name, *_ in gateway.calls] == ["S1", "S2", "S2"]
    assert any(
        name == "S1" and row.status == "completed" for (_, name), row in checkpoints.rows.items()
    )

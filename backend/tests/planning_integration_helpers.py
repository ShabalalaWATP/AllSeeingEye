"""Explicit collection capabilities and schema-dispatched production model fixtures."""

import json
from collections import deque

from ase.application.research.service import ResearchCollectionService
from ase.domain.llm import LlmResult
from post_draft_stage_helpers import POST_DRAFT_STAGES
from production_integration_helpers import StageGateway
from test_operator_research_tasks import Provider


def synthetic_plan(query):
    return ResearchCollectionService(lambda _: [Provider("fixture")]).plan(query)


# The post-draft stages run on every report. A test that is not about them need not
# script them, so the shared plain answers stand in.
REVIEW_DEFAULTS = POST_DRAFT_STAGES


class SchemaGateway:
    def __init__(self, responses):
        self.responses = {name: deque(values) for name, values in responses.items()}
        self.requests = []

    async def complete(self, base_url, api_key, model, request):
        self.requests.append(request)
        scripted = self.responses.get(request.schema_name)
        if not scripted and request.schema_name in REVIEW_DEFAULTS:
            answer = REVIEW_DEFAULTS[request.schema_name]
        else:
            answer = self.responses[request.schema_name].popleft()
        return LlmResult(json.dumps(answer), model, 50, 20, 100)


class PlanningStageGateway(StageGateway):
    async def complete(self, base_url, api_key, model, request):
        if request.schema_name == "research_plan":
            self.calls.append(request.schema_name)
            return LlmResult('{"candidates":[],"tasks":[]}', model, 10, 5, 3)
        return await super().complete(base_url, api_key, model, request)

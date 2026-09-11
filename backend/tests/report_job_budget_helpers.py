"""In-memory atomic mutations and inert provider doubles for report budget tests."""

import asyncio
import copy
from uuid import UUID

from ase.application.report_jobs.budget import ReportCallBudget
from ase.domain.llm import LlmMessage, LlmRequest, LlmResult, ReasoningEffort

PROFILE_ID = UUID("f3712297-843b-4d3e-b06b-b155c355f812")
REQUEST = LlmRequest(
    (LlmMessage("user", "private-question-marker"),),
    32000,
    0.2,
    {"type": "object"},
    "report_section",
    ReasoningEffort.MAX,
)
RESPONSE = LlmResult("private-response-marker", "luna", 10.0, 1000, 800)


class Ledger:
    def __init__(self):
        self.payload = {"calls": []}
        self.writes = 0
        self.checks = 0
        self.fail_write = None
        self.fail_after_commit = False
        self.deny_check = None
        self.wait_write = None
        self.wait_started = asyncio.Event()
        self.wait_release = asyncio.Event()
        self.lock = asyncio.Lock()

    async def mutate(self, callback):
        async with self.lock:
            self.writes += 1
            number = self.writes
            if self.wait_write == number:
                self.wait_started.set()
                await self.wait_release.wait()
            if self.fail_write == number and not self.fail_after_commit:
                raise OSError("private-storage-error-marker")
            updated = copy.deepcopy(self.payload)
            callback(updated)
            self.payload = updated
            if self.fail_write == number:
                raise OSError("private-storage-error-marker")
            return copy.deepcopy(updated)

    async def check(self):
        self.checks += 1
        if self.checks == self.deny_check:
            raise PermissionError("Access revoked")

    def budget(self):
        return ReportCallBudget(self.mutate, self.check, profile_id=PROFILE_ID)


class Gateway:
    def __init__(self, ledger, result=RESPONSE):
        self.ledger = ledger
        self.result = result
        self.error = None
        self.calls = []
        self.entered = asyncio.Event()
        self.release = None

    async def complete(self, base_url, api_key, model, request):
        self.calls.append((base_url, api_key, model, request))
        assert self.ledger.payload["calls"][-1]["status"] == "in_flight"
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        if self.error is not None:
            raise self.error
        return self.result

    async def search(self, api_key, model, request):
        return await self.complete("web", api_key, model, request)


def row(*, status="completed", reserved=32000, completion=1):
    return {
        "id": "test-row",
        "status": status,
        "reserved_output": reserved,
        "completion_tokens": completion,
    }

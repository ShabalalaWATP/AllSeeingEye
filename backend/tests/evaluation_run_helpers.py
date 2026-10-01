"""Scripted gateways and fixtures for administrator evaluation runs. No network is used."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID

from ase.application.admin.evaluations import EvaluationStart
from ase.application.dto import RequestContext
from ase.application.ports.llm import LlmGatewayError
from ase.container import Container
from ase.domain.evaluations import EvaluationRun
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult
from ase.domain.users import User
from evaluation_helpers import EvaluationGateway
from llm_fixture_helpers import seed_legacy_profile

SECRET_KEY = "sk-evaluation-0123456789-secret"  # gitleaks:allow
# A path token stands in for an endpoint whose URL itself is sensitive.
SECRET_PATH = "tenant-7f3c2a9b5d"
SECRET_URL = f"https://model.example.invalid/v1/{SECRET_PATH}"
CORE_CASES = ["conflicting_reports", "unknown_provenance"]

Hook = Callable[[int], Awaitable[None]]


@dataclass
class ScriptedRunGateway:
    """Answers like a model; optional failures and a per-call hook script each test."""

    hook: Hook | None = None
    fail: bool = False
    leak_secrets: bool = False
    calls: list[tuple[str, str, str]] = field(default_factory=list)
    inner: EvaluationGateway = field(default_factory=EvaluationGateway)

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        self.calls.append((base_url, api_key, request.schema_name))
        if self.hook is not None:
            await self.hook(len(self.calls))
        if self.fail:
            detail = f" key={api_key} url={base_url}" if self.leak_secrets else ""
            raise LlmGatewayError(f"The fixture provider failed.{detail}")
        return await self.inner.complete(base_url, api_key, model, request)


async def evaluation_profile(
    container: Container, *, name: str = "Evaluation fixture", roles=("assessment",)
) -> LlmProfile:
    return await seed_legacy_profile(
        container,
        {
            "name": name,
            "base_url": SECRET_URL,
            "model": "fixture-model",
            "api_key": SECRET_KEY,
            "roles": list(roles),
            "max_output_tokens": 4000,
            "temperature": 0.0,
        },
    )


async def start_run(
    container: Container,
    admin: User,
    profile: LlmProfile,
    *,
    cases: list[str] | None = None,
    max_calls: int = 8,
) -> EvaluationRun:
    async with container.session_factory() as session:
        return await container.evaluation_runs(session).start(
            admin, EvaluationStart(profile.id, cases or CORE_CASES[:1], max_calls), RequestContext()
        )


async def finished(container: Container, admin: User, run_id: UUID) -> EvaluationRun:
    await container.evaluation_tasks.drain()
    async with container.session_factory() as session:
        return await container.evaluation_runs(session).get(admin, run_id)


async def artefact(container: Container, admin: User, run_id: UUID) -> bytes:
    async with container.session_factory() as session:
        _, content = await container.evaluation_runs(session).artefact(admin, run_id)
    return content


def unzipped(content: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def assert_no_secrets(*blobs: bytes) -> None:
    for blob in blobs:
        for secret in (SECRET_KEY, SECRET_URL, SECRET_PATH, "model.example.invalid"):
            assert secret.encode() not in blob, secret

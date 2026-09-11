"""Real SQLite access policy and job storage with synthetic preparation callbacks."""

from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.adapters.persistence.audit import SqlAlchemyUnitOfWork
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.teams import SqlTeamRepository
from ase.adapters.persistence.users import SqlUserRepository
from ase.application.access import AccessPolicy
from ase.application.report_jobs.service import ReportJobService
from ase.application.reports.production_types import Job
from ase.application.reports.templates import template_for
from ase.domain.users import Role, User
from report_job_helpers import NOW


def frozen(prepared, _routing):
    return {
        "schema_version": 1,
        "template_id": prepared.template.id,
        "report_id": str(prepared.report_id),
        "routing": {
            "profiles": [
                {
                    "role": prepared.template.role.value,
                    "model": "fixture-model",
                    "reasoning_effort": "max",
                }
            ]
        },
    }


@pytest.fixture(name="service_env")
async def service_environment(job_storage):
    _, factory = job_storage
    user = User(
        uuid4(), "owner@example.test", "Owner", Role.USER, True, None, 0, None, None, NOW, None
    )
    stranger = User(
        uuid4(), "other@example.test", "Other", Role.USER, True, None, 0, None, None, NOW, None
    )
    async with factory() as session:
        users = SqlUserRepository(session)
        await users.add(user)
        await users.add(stranger)
        await session.commit()
    env = SimpleNamespace(factory=factory, user=user, stranger=stranger)

    @asynccontextmanager
    async def service(**overrides):
        async with factory() as session:

            async def prepare(actor, request):
                assert not session.in_transaction()
                return Job(
                    actor,
                    template_for(request.template_id),
                    request,
                    None,
                    NOW,
                    timedelta(hours=24),
                    "Synthetic report",
                    {},
                    None,
                ), None

            repo = SqlReportJobRepository(session)
            values = {
                "repo": repo,
                "access": AccessPolicy(SqlUserRepository(session), SqlTeamRepository(session)),
                "uow": SqlAlchemyUnitOfWork(session),
                "clock": SimpleNamespace(now=lambda: NOW),
                "prepare_job": AsyncMock(side_effect=prepare),
                "freeze": Mock(side_effect=frozen),
                "check_job": AsyncMock(),
                "check_resume": AsyncMock(),
                "cancel": Mock(),
            }
            values.update(overrides)
            instance = ReportJobService(**values)
            yield instance, SimpleNamespace(**values, session=session)

    env.service = service
    return env


def section(packet, identity="topic-1", status="completed"):
    return {
        "packet_digest": packet,
        "section_id": identity,
        "status": status,
        "reason": None,
        "payload": {
            "id": identity,
            "title": "Verified topic",
            "kind": "topic",
            "parent": None,
            "evidence_labels": ["E1"],
            "body": {
                "reporting": [
                    {"text": "A source reports this.", "evidence": ["E1"], "grades": ["B2"]}
                ],
                "assessment": [{"text": "Assessment with limitations.", "evidence": ["E1"]}],
                "gaps": [],
            },
        },
    }


def call(status="in_flight", **changes):
    return {
        "id": str(uuid4()),
        "status": status,
        "reserved_output": 32000,
        "prompt_tokens": None,
        "completion_tokens": None,
        **changes,
    }

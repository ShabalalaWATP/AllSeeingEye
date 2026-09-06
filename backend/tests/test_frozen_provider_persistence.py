"""Saved report provenance carries the selected provider without upgrading old records."""

import json

from sqlalchemy import select

from ase.adapters.persistence.models import ReportVersionRow
from ase.api.schemas_reports import ReportVersionOut
from ase.application.dto import RequestContext
from ase.application.ports.feeds import EventQuery
from ase.application.reports.request import ReportRequest
from ase.domain.llm import LlmProvider
from report_helpers import ScriptedGateway, filled_store, good_body
from test_model_routing import profile
from test_model_routing_integration import save_binding


async def test_generate_freezes_native_provider_and_legacy_read_does_not_rewrite_json(
    container, admin, user
):
    native = profile(
        "Native fixture",
        provider=LlmProvider.BEDROCK,
        base_url="https://bedrock-runtime.eu-west-2.amazonaws.com",
        model="amazon.nova-pro-v1:0",
        api_key_encrypted=container.cipher.encrypt("synthetic-native-key"),
        reasoning_effort=None,
    )
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.add(native)
        await session.commit()
    await save_binding(container, admin, native)
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))
    container.llm = gateway = ScriptedGateway(json.dumps(good_body()))
    async with container.session_factory() as session:
        record, generated = await container.generate_report(session).execute(
            user, ReportRequest("intsum"), RequestContext()
        )
    assert gateway.requests[0].provider is LlmProvider.BEDROCK
    assert all(row.provider is LlmProvider.BEDROCK for row in generated.model_routing.profiles)
    async with container.session_factory() as session:
        saved = await container.repositories(session).reports.get_version(record.id, 1)
        assert saved.model_routing == generated.model_routing
        response = ReportVersionOut.from_version(saved)
        assert all(row.provider is LlmProvider.BEDROCK for row in response.model_routing.profiles)
        # Deliberate historical fixture: older versions recorded the same settings shape
        # without a provider. Reading defaults it, but must not update their stored JSON.
        row = await session.scalar(select(ReportVersionRow).where(ReportVersionRow.id == saved.id))
        historical = json.loads(json.dumps(row.analysis))
        for settings in historical["model_routing"]["profiles"]:
            settings.pop("provider")
        row.analysis = historical
        await session.commit()
    async with container.session_factory() as session:
        historical_version = await container.repositories(session).reports.get_version(record.id, 1)
        assert all(
            settings.provider is LlmProvider.OPENAI_COMPATIBLE
            for settings in historical_version.model_routing.profiles
        )
        raw = await session.scalar(select(ReportVersionRow).where(ReportVersionRow.id == saved.id))
        assert all(
            "provider" not in settings for settings in raw.analysis["model_routing"]["profiles"]
        )

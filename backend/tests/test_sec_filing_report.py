"""Selected SEC content reaches the actual private report path and remains frozen."""

import io
import json
import zipfile
from uuid import UUID

import pytest
from docx import Document
from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_input_helpers import model_setup, report_payload
from sec_filings_helpers import DOCUMENT, SecTransport
from test_sec_filing_api import BASE, selected


async def test_selected_filing_text_is_saved_as_report_evidence_without_public_collection(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
    admin: User,
) -> None:
    collection = await model_setup(client, container, admin)
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    transport.responses[DOCUMENT] = b"<p>" + b"Issuer reported revenue. " * 130 + b"</p>"
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    try:
        key = await selected(client, token)
        imported = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
        assert imported.status_code == 201, imported.text
        original = container.research_inputs.read(user, UUID(imported.json()["id"]))
        target_response = await client.get(
            f"/api/research/inputs/{original.receipt.id}/declaration-targets", headers=bearer(token)
        )
        assert target_response.status_code == 200
        target = target_response.json()["targets"][0]
        assert target["source_dates"][0]["day_start"] == "2026-08-31"
        assert target["source_dates"][0]["basis"] == "source_spec"
        declaration = {
            "sha256": original.receipt.sha256,
            "declarations": [
                {
                    "event_id": target["event_id"],
                    "content_hash": target["content_hash"],
                    "transformations": [
                        {
                            "field": "title",
                            "original_text": target["title"],
                            "transformed_text": "Synthetic Issuer filing",
                            "kind": "transliteration",
                            "source_language": "en",
                            "target_language": "en",
                            "source_script": "Latn",
                            "target_script": "Latn",
                            "method": "Operator transcription fixture",
                        }
                    ],
                }
            ],
        }
        derived_response = await client.post(
            f"/api/research/inputs/{original.receipt.id}/declarations",
            headers=bearer(token),
            json=declaration,
        )
        assert derived_response.status_code == 201, derived_response.text
        derived = container.research_inputs.read(user, UUID(derived_response.json()["id"]))
        assert derived.receipt.parent_input_id == original.receipt.id
        assert container.research_inputs.read(user, original.receipt.id) == original
        for old, new in zip(original.events, derived.events, strict=True):
            assert new.source_dates == old.source_dates
            assert new.content_hash == old.content_hash and new.summary == old.summary
            assert new.attributes == old.attributes
        assert derived.events[0].transformations[0].actor_id == user.id
        assert derived.events[0].transformations[0].origin == "operator"
        refused = await client.post(
            f"/api/research/inputs/{derived.receipt.id}/declarations",
            headers=bearer(token),
            json=declaration,
        )
        assert refused.status_code == 422
        result = await client.post(
            "/api/reports",
            headers=bearer(token),
            json=report_payload(
                research_input_id=derived_response.json()["id"],
            ),
        )
        assert result.status_code == 201, result.text
        evidence = result.json()["version"]["evidence"]
        assert len(evidence) == 3
        assert all(item["url"] == DOCUMENT and item["published_at"] is None for item in evidence)
        assert all(
            {row["key"]: row["value"] for row in item["attributes"]}["record_kind"]
            == "sec_filing_content"
            for item in evidence
        )
        assert all(
            {row["key"]: row["value"] for row in item["attributes"]}["original_sha256"]
            == imported.json()["sha256"]
            for item in evidence
        )
        assert all(item["source_dates"][0]["day_start"] == "2026-08-31" for item in evidence)
        assert all(item["source_dates"][0]["value"] is None for item in evidence)
        assert collection.calls == 0
        assert container.store.stats().total == 0
        saved = await client.get(
            f"/api/reports/{result.json()['report']['id']}", headers=bearer(token)
        )
        assert saved.status_code == 200 and saved.json()["version"]["evidence"] == evidence
        package = await client.get(
            f"/api/reports/{result.json()['report']['id']}/evidence-package", headers=bearer(token)
        )
        assert package.status_code == 200, package.text
        with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
            frozen = json.loads(archive.read("evidence.json"))
            assert frozen[0]["source_dates"] == evidence[0]["source_dates"]
            assert frozen[0]["content_hash"] == evidence[0]["content_hash"]
        doc = await client.get(
            f"/api/reports/{result.json()['report']['id']}/export/docx", headers=bearer(token)
        )
        assert doc.status_code == 200, doc.text

        readable = "\n".join(p.text for p in Document(io.BytesIO(doc.content)).paragraphs)
        assert "2026-08-31" in readable
        assert "filingDate" not in readable and "source_spec" not in readable
    finally:
        await transport.http.aclose()

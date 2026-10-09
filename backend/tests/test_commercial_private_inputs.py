"""Private intake must honour the exact source before reading bodies or calling tools."""

from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from ase.application.access import AccessPolicy
from ase.application.research.inputs import ImportResearchInput
from ase.domain.errors import Forbidden, NotFound
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from photo_helpers import Vision, profile, session_check, upload
from report_input_helpers import actor_headers
from research_input_helpers import Harness, Limiter, extracted
from test_research_input_api import scope, upload_app


def private_policy(*acknowledged: str) -> SourceLicencePolicy:
    return SourceLicencePolicy(
        [
            SourceLicence(source_id, "licence_required", True, "terms")
            for source_id in ("research_import", "research_media")
        ],
        commercial_use=True,
        acknowledgements=frozenset(acknowledged),
    )


async def test_licence_refusal_precedes_every_body_read():
    harness = Harness()
    harness.service = ImportResearchInput(
        AccessPolicy(harness.identity, harness.identity),
        harness.extractor,
        harness.store,
        harness.clock,
        Limiter(),
        harness.uow,
        licences=private_policy(),
    )
    messages = []

    async def receive() -> dict[str, Any]:
        raise AssertionError("A licence-denied upload must not read its body")

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await upload_app(harness)(scope(), receive, send)
    assert messages[0]["status"] == 403
    assert harness.extractor.calls == 0


@pytest.mark.parametrize(
    ("filename", "acknowledged", "status"),
    [
        ("notes.txt", (), 403),
        ("notes.txt", ("research_import",), 201),
        ("notes.txt", ("research_media",), 403),
        ("photo.PNG", ("research_import",), 403),
        ("photo.PNG", ("research_media",), 201),
        ("clip.mp4", ("research_import",), 403),
    ],
)
async def test_upload_requires_exact_permission_before_extraction(
    client, container, user, filename, acknowledged, status
):
    headers = await actor_headers(client, user)
    container.source_licences = private_policy(*acknowledged)
    extraction = extracted()
    if filename != "notes.txt":
        extraction = replace(
            extraction,
            filename=filename,
            media_type="video/mp4" if filename.endswith(".mp4") else "image/png",
            events=tuple(replace(event, source_id="research_media") for event in extraction.events),
        )
    extract = AsyncMock(return_value=extraction)
    container.research_importer.extract = extract
    response = await client.post(
        "/api/research/inputs",
        params={"filename": filename},
        content=b"Untrusted fixture input",
        headers={**headers, "content-type": "application/octet-stream"},
    )
    assert response.status_code == status, response.text[:500]
    assert extract.await_count == (1 if status == 201 else 0)
    if status == 403:
        assert "licence terms" in response.text


async def test_reserved_upload_rechecks_policy_and_releases_capacity(container, user):
    async with container.session_factory() as session:
        reservation = await container.import_research_input(session).reserve(user, "notes.txt")
    container.source_licences = private_policy()
    extract = AsyncMock(return_value=extracted())
    container.research_importer.extract = extract
    async with container.session_factory() as session:
        with pytest.raises(Forbidden, match="licence terms"):
            await container.import_research_input(session).execute_reserved(
                user, reservation, b"Private content"
            )
    extract.assert_not_awaited()
    with pytest.raises(NotFound):
        container.research_inputs.require_pending(reservation)


async def test_photo_analysis_requires_media_permission_but_preview_and_discard_remain(
    client, container, user
):
    await profile(container)
    input_id = upload(container, user)
    vision = Vision()
    container.llm = vision
    container.source_licences = private_policy("research_import")
    response = await client.post(
        f"/api/research/inputs/{input_id}/geolocation",
        headers=await actor_headers(client, user),
        json={"consent_to_send_image": True},
    )
    assert response.status_code == 403, response.text
    assert vision.calls == []
    async with container.session_factory() as session:
        service = container.import_research_input(session)
        assert service.previews(user, input_id)
        await service.discard(user, input_id, before_discard=session_check)
    with pytest.raises(NotFound):
        container.research_inputs.read(user, input_id)


async def test_media_acknowledgement_allows_photo_analysis(client, container, user):
    await profile(container)
    input_id = upload(container, user)
    vision = Vision()
    container.llm = vision
    container.source_licences = private_policy("research_media")
    response = await client.post(
        f"/api/research/inputs/{input_id}/geolocation",
        headers=await actor_headers(client, user),
        json={"consent_to_send_image": True},
    )
    assert response.status_code == 201, response.text
    assert len(vision.calls) == 1

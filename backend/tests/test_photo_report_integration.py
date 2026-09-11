"""Derived photo hypotheses become frozen private report evidence without retained pixels."""

import json

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from photo_helpers import Vision, upload
from report_input_helpers import CallbackGateway, actor_headers, model_setup, report_payload


async def test_photo_assessment_report_survives_working_receipt_discard(
    client: AsyncClient,
    container: Container,
    admin: User,
    user: User,
) -> None:
    collection = await model_setup(client, container, admin)
    original_id = upload(container, user)
    headers = await actor_headers(client, user)
    container.llm = Vision()
    analysed = await client.post(
        f"/api/research/inputs/{original_id}/geolocation",
        headers=headers,
        json={"consent_to_send_image": True},
    )
    assert analysed.status_code == 201, analysed.text
    derived_id = analysed.json()["input"]["id"]
    container.llm = CallbackGateway()
    report = await client.post(
        "/api/reports",
        headers=headers,
        json=report_payload(research_focus="media", research_input_id=derived_id),
    )
    assert report.status_code == 201, report.text
    frozen = report.json()["version"]["evidence"]
    assert frozen and collection.calls == 0
    text = json.dumps(frozen)
    assert "UNVERIFIED AI VISUAL HYPOTHESIS" in text
    assert "returned-vision-fixture" in text
    assert "png_base64" not in report.text and "data:image" not in report.text
    assert derived_id not in report.text and str(original_id) not in report.text
    assert "Private EXIF" not in report.text
    discarded = await client.delete(f"/api/research/inputs/{original_id}", headers=headers)
    assert discarded.status_code == 204
    saved = await client.get(f"/api/reports/{report.json()['report']['id']}", headers=headers)
    assert saved.status_code == 200
    assert saved.json()["version"]["evidence"] == frozen

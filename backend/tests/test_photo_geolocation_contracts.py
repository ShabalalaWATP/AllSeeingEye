"""True image payloads and strict uncertain-location output validation."""

import base64
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.bedrock import build_payload as bedrock_payload
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway, build_payload
from ase.api.schemas_photo_geolocation import PhotoGeolocationIn
from ase.application.ports.llm import LlmGatewayError
from ase.application.research.photo_evidence import photo_events
from ase.domain.errors import NotFound
from ase.domain.llm import LlmImage, LlmMessage, LlmProvider, LlmRequest
from ase.domain.photo_geolocation import PhotoAssessment, PhotoProvenance
from photo_helpers import UNKNOWN
from research_input_helpers import NOW, Harness, extracted

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + b"\x00\x00\x00\x01" * 2
REQUEST = LlmRequest((LlmMessage("user", "Analyse scene", (LlmImage(PNG),)),), 1000, 0.1)


def test_image_payload_is_structured_on_both_providers_and_repr_hides_bytes() -> None:
    content = build_payload("vision", REQUEST)["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "Analyse scene"}
    encoded = content[1]["image_url"]["url"].split(",", 1)[1]
    assert base64.b64decode(encoded) == PNG
    assert content[1]["image_url"]["detail"] == "high"
    native = bedrock_payload(REQUEST)["messages"][0]["content"][1]["image"]
    assert native["format"] == "png" and base64.b64decode(native["source"]["bytes"]) == PNG
    assert "PNG" not in repr(REQUEST) and "PNG" not in repr(LlmImage(PNG))
    text = replace(REQUEST, messages=(LlmMessage("user", "Plain text"),))
    assert build_payload("vision", text)["messages"][0]["content"] == "Plain text"


@pytest.mark.parametrize("case", ["format", "size", "role", "message_count", "request_count"])
def test_images_are_bounded_and_only_in_user_messages(case: str) -> None:
    with pytest.raises(ValueError):
        if case == "format":
            LlmImage(b"untrusted raw upload")
        elif case == "size":
            LlmImage(PNG + b"x" * 1024 * 1024)
        elif case == "role":
            LlmMessage("system", "system", (LlmImage(PNG),))
        elif case == "message_count":
            LlmMessage("user", "user", (LlmImage(PNG), LlmImage(PNG)))
        else:
            replace(REQUEST, messages=REQUEST.messages * 7)


@pytest.mark.parametrize("native", [False, True])
async def test_unsupported_vision_is_explicit_and_never_falls_back(native: bool) -> None:
    calls = []

    def reject(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(400, text="Provider body containing sensitive private hints")

    async with httpx.AsyncClient(transport=httpx.MockTransport(reject)) as client:
        gateway = (
            BedrockConverseGateway(client=client)
            if native
            else OpenAiCompatibleGateway(client=client)
        )
        base = (
            "https://bedrock-runtime.us-east-1.amazonaws.com"
            if native
            else "https://api.openai.com/v1"
        )
        with pytest.raises(LlmGatewayError, match="rejected image analysis") as error:
            await gateway.complete(base, "private-key", "text-only-fixture", REQUEST)
    assert len(calls) == 1 and "sensitive" not in str(error.value)
    assert "private-key" not in str(error.value)


def candidate() -> dict:
    return {
        "label": "Synthetic city",
        "country_iso": "GB",
        "precision": "city",
        "supporting_clues": ["A public landmark resembles the synthetic city."],
        "contradictions": ["The surrounding street cannot be identified."],
        "coordinates": {
            "latitude": 51.5,
            "longitude": -0.1,
            "uncertainty_radius_km": 5,
            "basis": "Approximate city centre only.",
        },
    }


def test_candidates_remain_hypotheses_without_certainty_fields() -> None:
    body = {**UNKNOWN, "status": "candidates", "candidates": [candidate()]}
    assessment = PhotoAssessment.model_validate(body)
    assert assessment.candidates[0].coordinates.uncertainty_radius_km == 5
    assert "confidence" not in assessment.model_dump_json()
    assert PhotoAssessment.model_validate(UNKNOWN).status == "unknown"
    provenance = PhotoProvenance(
        profile_id=uuid4(),
        profile_revision=1,
        provider=LlmProvider.OPENAI_COMPATIBLE,
        configured_model="fixture",
        returned_model="fixture-returned",
        analysed_at=NOW,
        original_sha256="a" * 64,
        image_sha256="b" * 64,
    )
    events = photo_events(assessment, provenance)
    assert any("Unverified candidate:" in event.title for event in events)
    assert all(event.point is None and event.country_iso is None for event in events)
    assert all(event.grade == "F6" for event in events)
    assert any("fixture-returned" in event.summary for event in events)


@pytest.mark.parametrize(
    "invalid", ["status", "too_many", "nan", "precision", "empty", "huge", "extra"]
)
def test_untrusted_model_output_rejects_overclaim_and_malformed_fields(invalid: str) -> None:
    body = deepcopy({**UNKNOWN, "status": "candidates", "candidates": [candidate()]})
    if invalid == "status":
        body["status"] = "unknown"
    elif invalid == "too_many":
        body["candidates"] *= 4
    elif invalid == "nan":
        body["candidates"][0]["coordinates"]["latitude"] = float("nan")
    elif invalid == "precision":
        body["candidates"][0]["coordinates"]["uncertainty_radius_km"] = 0.1
    elif invalid == "empty":
        body["visual_clues"] = [" "]
    elif invalid == "huge":
        body["verification_steps"] = ["x" * 501]
    else:
        body["candidates"][0]["confidence"] = 99
    with pytest.raises(ValidationError):
        PhotoAssessment.model_validate(body)


@pytest.mark.parametrize("consent", [None, False, "yes", 0])
def test_api_requires_explicit_image_consent(consent: object) -> None:
    with pytest.raises(ValidationError):
        PhotoGeolocationIn.model_validate({"consent_to_send_image": consent})


async def test_derived_receipts_inherit_original_deadline() -> None:
    harness = Harness()
    original = await harness.service.execute(harness.actor, "notes.txt", b"Original text")
    harness.clock.advance(timedelta(minutes=4))
    reservation = harness.store.reserve(harness.actor, "notes.txt")
    derived = harness.store.put(reservation, replace(extracted(), parent_input_id=original.id))
    assert derived.receipt.expires_at == original.expires_at
    harness.clock.advance(timedelta(minutes=12))
    with pytest.raises(NotFound):
        harness.store.read(harness.actor, derived.receipt.id)


async def test_missing_parent_does_not_leave_a_derived_slot() -> None:
    harness = Harness()
    reservation = harness.store.reserve(harness.actor, "notes.txt")
    with pytest.raises(NotFound):
        harness.store.put(reservation, replace(extracted(), parent_input_id=uuid4()))
    harness.store.release(reservation)
    assert not harness.store._reservations

"""Multi-photo vision binds every image, inference and expiring receipt to its owner."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.llm.bedrock import build_payload as bedrock_payload
from ase.adapters.llm.openai_compatible import build_payload
from ase.adapters.llm.openai_responses import build_responses_payload
from ase.application.research.photo_inputs import read_photos
from ase.container import Container
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from photo_helpers import UNKNOWN, Vision, profile, session_check, upload
from research_input_helpers import Harness, extracted


def assessment(count: int) -> dict:
    return {
        **UNKNOWN,
        "photos": [
            {
                "photo_id": f"photo-{index}",
                "visual_clues": [f"photo-{index} contains a synthetic test label."],
                "limitations": ["No real geographic feature is visible."],
            }
            for index in range(1, count + 1)
        ],
        "cross_photo_analysis": "Matching labels do not establish a shared real location.",
    }


async def test_six_photo_http_analysis_preserves_labels_hashes_and_all_parents(
    client: AsyncClient, container: Container, user: User
) -> None:
    await profile(container)
    ids = [upload(container, user)]
    container.clock.advance(timedelta(minutes=2))
    ids += [upload(container, user) for _ in range(5)]
    originals = [container.research_inputs.read(user, value) for value in ids]
    vision = Vision()
    vision.content = json.dumps(assessment(6))
    container.llm = vision
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.post(
        f"/api/research/inputs/{ids[0]}/geolocation",
        headers=bearer(token),
        json={"consent_to_send_image": True, "additional_input_ids": list(map(str, ids[1:]))},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["photos"]) == len(body["provenance"]["photos"]) == 6
    assert body["input"]["parent_input_ids"] == list(map(str, ids))
    assert body["input"]["parent_input_id"] == str(ids[0])
    assert "png_base64" not in response.text and "private-fixture-key" not in response.text
    request = vision.calls[0][3]
    assert set(request.json_schema["required"]) == set(request.json_schema["properties"])
    assert len(request.messages) == 7
    for index, message in enumerate(request.messages[1:]):
        assert json.loads(message.content)["photo_id"] == f"photo-{index + 1}"
        assert message.images[0].png == originals[index].frames[0].png
        assert body["provenance"]["photos"][index]["input_id"] == str(ids[index])
    # All three provider serialisers preserve the six separately labelled image parts.
    for payload, key in (
        (build_payload("vision", request), "messages"),
        (bedrock_payload(request), "messages"),
        (build_responses_payload("vision", request), "input"),
    ):
        assert len([row for row in payload[key] if row["role"] == "user"]) == 6
    derived = container.research_inputs.read(user, UUID(body["input"]["id"]))
    assert derived.receipt.expires_at == originals[0].receipt.expires_at
    assert not derived.frames
    assert all(str(input_id) not in event.summary for input_id in ids for event in derived.events)
    assert any(event.title == "Cross-photo analysis" for event in derived.events)
    assert all(event.point is None and event.grade == "F6" for event in derived.events)
    container.research_inputs.discard(user, ids[-1])
    with pytest.raises(NotFound):
        container.research_inputs.read(user, derived.receipt.id)
    assert container.research_inputs.read(user, ids[0])


@pytest.mark.parametrize("invalid", ["duplicate", "too_many", "foreign", "derived", "digest"])
async def test_every_input_is_validated_before_any_image_disclosure(
    invalid: str, container: Container, user: User
) -> None:
    await profile(container)
    first, second = upload(container, user), upload(container, user)
    store = container.research_inputs
    extra = (second,)
    if invalid == "duplicate":
        extra = (first,)
    elif invalid == "too_many":
        extra = tuple(uuid4() for _ in range(6))
    elif invalid == "foreign":
        foreign = replace(user, id=uuid4())
        extra = (upload(container, foreign),)
    elif invalid == "derived":
        original = store._ready[second]
        store._ready[second] = replace(
            original, receipt=replace(original.receipt, parent_input_ids=(first,))
        )
    else:
        original = store._ready[second]
        store._ready[second] = replace(
            original, frames=(replace(original.frames[0], sha256="0" * 64),)
        )
    vision = Vision()
    container.llm = vision
    async with container.session_factory() as session:
        with pytest.raises(NotFound if invalid == "foreign" else InvalidRequest):
            await container.photo_geolocation(session).execute(
                user,
                first,
                additional_input_ids=extra,
                consent_to_send_image=True,
                check_session=session_check,
            )
    assert not vision.calls


@pytest.mark.parametrize("change", ["discard", "expiry", "before_send"])
async def test_secondary_photo_revocation_stops_disclosure_or_retention(
    change: str, container: Container, user: User
) -> None:
    await profile(container)
    first, second = upload(container, user), upload(container, user)
    vision = Vision()
    vision.content = json.dumps(assessment(2))
    container.llm = vision
    checks = 0

    async def check() -> None:
        nonlocal checks
        checks += 1
        if change == "before_send" and checks == 2:
            container.research_inputs.discard(user, second)

    async def revoke() -> None:
        if change == "discard":
            container.research_inputs.discard(user, second)
        elif change == "expiry":
            container.clock.advance(timedelta(minutes=16))

    vision.after = revoke
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.photo_geolocation(session).execute(
                user,
                first,
                additional_input_ids=(second,),
                consent_to_send_image=True,
                check_session=check,
            )
    assert len(vision.calls) == (0 if change == "before_send" else 1)
    assert all(
        not row.receipt.parent_input_ids for row in container.research_inputs._ready.values()
    )
    assert not container.photo_admission.locked()


@pytest.mark.parametrize("invalid", ["missing_photo", "wrong_id", "no_comparison", "duplicate"])
async def test_batch_output_must_cover_exact_photos_and_compare_them(
    invalid: str, container: Container, user: User
) -> None:
    await profile(container)
    ids = [upload(container, user) for _ in range(2)]
    body = assessment(2)
    if invalid == "missing_photo":
        body["photos"].pop()
    elif invalid == "wrong_id":
        body["photos"][1]["photo_id"] = "photo-6"
    elif invalid == "duplicate":
        body["photos"][1]["photo_id"] = "photo-1"
    else:
        body["cross_photo_analysis"] = None
    vision = Vision()
    vision.content = json.dumps(body)
    container.llm = vision
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="invalid geolocation"):
            await container.photo_geolocation(session).execute(
                user,
                ids[0],
                additional_input_ids=(ids[1],),
                consent_to_send_image=True,
                check_session=session_check,
            )
    assert len(container.research_inputs._ready) == 2


@pytest.mark.parametrize("invalid", ["dimension", "bytes"])
def test_batch_rechecks_sanitised_image_bounds(
    invalid: str, container: Container, user: User
) -> None:
    input_id = upload(container, user)
    original = container.research_inputs._ready[input_id]
    frame = original.frames[0]
    data = frame.png
    if invalid == "dimension":
        data = data[:16] + (513).to_bytes(4, "big") + data[20:]
    else:
        data += b"x" * (1024 * 1024)
    container.research_inputs._ready[input_id] = replace(
        original, frames=(replace(frame, png=data, sha256=hashlib.sha256(data).hexdigest()),)
    )
    with pytest.raises(InvalidRequest):
        read_photos(container.research_inputs, user, (input_id,))


def test_multi_parent_store_rejects_foreign_generation_and_excess_parents() -> None:
    harness = Harness()
    parent = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(parent, extracted())
    for actor, ids, error in (
        (replace(harness.actor, id=uuid4()), (parent.id,), NotFound),
        (replace(harness.actor, security_version=1), (parent.id,), NotFound),
        (harness.actor, tuple(uuid4() for _ in range(7)), InvalidRequest),
    ):
        pending = harness.store.reserve(actor, "notes.txt")
        with pytest.raises(error):
            harness.store.put(pending, replace(extracted(), parent_input_ids=ids))
        harness.store.release(pending)


def test_secondary_parent_controls_derived_expiry_and_descendant_deletion() -> None:
    harness = Harness()
    early = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(early, extracted())
    harness.clock.advance(timedelta(minutes=3))
    main = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(main, extracted())
    pending = harness.store.reserve(harness.actor, "notes.txt")
    combined = harness.store.put(
        pending, replace(extracted(), parent_input_id=main.id, parent_input_ids=(main.id, early.id))
    )
    descendant = harness.store.put(
        harness.store.reserve(harness.actor, "notes.txt"),
        replace(extracted(), parent_input_id=combined.receipt.id),
    )
    assert combined.receipt.expires_at == descendant.receipt.expires_at == early.expires_at
    harness.store.discard(harness.actor, early.id)
    assert list(harness.store._ready) == [main.id]

"""Bind a small ordered photograph set to sanitised images and current private receipts."""

import hashlib
import json
from uuid import UUID

from ase.application.ports.research_inputs import (
    MAX_PREVIEW_BYTES,
    ResearchInputStore,
    StoredResearchInput,
)
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmImage, LlmMessage
from ase.domain.photo_geolocation import PhotoImageProvenance
from ase.domain.users import User

MAX_PHOTOS = 6
MAX_PHOTO_SET_BYTES = MAX_PHOTOS * MAX_PREVIEW_BYTES
MAX_PHOTO_SET_PIXELS = MAX_PHOTOS * 512 * 512


def photo_ids(input_id: UUID, additional_input_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    ids = (input_id, *additional_input_ids)
    if len(ids) > MAX_PHOTOS or len(set(ids)) != len(ids):
        raise InvalidRequest("Choose up to six different uploaded photographs.")
    return ids


def read_photos(
    store: ResearchInputStore, actor: User, ids: tuple[UUID, ...]
) -> tuple[StoredResearchInput, ...]:
    originals = tuple(store.read(actor, input_id) for input_id in ids)
    total_bytes = total_pixels = 0
    for original in originals:
        if (
            not original.receipt.media_type.startswith("image/")
            or len(original.frames) != 1
            or original.receipt.parent_input_id is not None
            or original.receipt.parent_input_ids
        ):
            raise InvalidRequest("Upload original photographs for visual geolocation.")
        frame = original.frames[0]
        data = frame.png
        if (
            len(data) < 24
            or len(data) > MAX_PREVIEW_BYTES
            or data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR"
            or hashlib.sha256(data).hexdigest() != frame.sha256
        ):
            raise InvalidRequest("The sanitised image does not match its preview receipt.")
        width, height = int.from_bytes(data[16:20]), int.from_bytes(data[20:24])
        if not (1 <= width <= 512 and 1 <= height <= 512):
            raise InvalidRequest("A sanitised photo exceeds the 512-pixel preview limit.")
        total_bytes += len(data)
        total_pixels += width * height
    if total_bytes > MAX_PHOTO_SET_BYTES or total_pixels > MAX_PHOTO_SET_PIXELS:
        raise InvalidRequest("The photographs exceed the combined analysis size limit.")
    return originals


def photo_messages(
    originals: tuple[StoredResearchInput, ...], question: str, hints: str
) -> tuple[LlmMessage, ...]:
    # One clearly labelled image per user message works with every supported vision adapter.
    return tuple(
        LlmMessage(
            "user",
            json.dumps(
                {
                    "question": question,
                    "unverified_hints": hints,
                    "photo_id": f"photo-{index}",
                    "photo_count": len(originals),
                }
            ),
            images=(LlmImage(original.frames[0].png),),
        )
        for index, original in enumerate(originals, 1)
    )


def image_provenance(originals: tuple[StoredResearchInput, ...]) -> list[PhotoImageProvenance]:
    return [
        PhotoImageProvenance(
            photo_id=f"photo-{index}",
            input_id=original.receipt.id,
            original_sha256=original.receipt.sha256,
            image_sha256=original.frames[0].sha256,
        )
        for index, original in enumerate(originals, 1)
    ]

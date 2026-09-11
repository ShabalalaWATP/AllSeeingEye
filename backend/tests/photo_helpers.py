"""Synthetic sanitised photo inputs and deterministic model responses."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from uuid import UUID

from ase.adapters.research_media import MediaTools, extract_media
from ase.adapters.research_media.events import events_from_media
from ase.application.ports.research_inputs import InputExtraction, InputPreviewFrame
from ase.container import Container
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult
from ase.domain.users import User
from llm_fixture_helpers import seed_legacy_profile
from media_helpers import synthetic_image

UNKNOWN = {
    "status": "unknown",
    "summary": "The synthetic image has no geographical context.",
    "visual_clues": ["A synthetic test label is visible."],
    "candidates": [],
    "verification_steps": ["Ask the uploader for the original source."],
    "limitations": ["No recognisable geographic feature is visible."],
}


def upload(container: Container, user: User) -> UUID:
    media = extract_media(synthetic_image(metadata=True), "fixture.png", MediaTools())
    extraction = InputExtraction(
        media.filename,
        media.media_type,
        media.sha256,
        events_from_media(media, container.clock.now()),
        media.limitations,
        tuple(InputPreviewFrame(frame.seconds, frame.sha256, frame.png) for frame in media.frames),
    )
    reservation = container.research_inputs.reserve(user, media.filename)
    return container.research_inputs.put(reservation, extraction).receipt.id


async def profile(container: Container, model: str = "vision-fixture") -> LlmProfile:
    return await seed_legacy_profile(
        container,
        {
            "name": model,
            "base_url": "https://vision.example.invalid/v1",
            "model": model,
            "api_key": "private-fixture-key",
            "roles": ["assessment"],
            "max_output_tokens": 4000,
            "temperature": 0.2,
        },
    )


async def session_check() -> None:
    return None


class Vision:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str, LlmRequest]] = []
        self.content = json.dumps(UNKNOWN)
        self.error: BaseException | None = None
        self.after: Callable[[], Awaitable[None]] = session_check
        self.started = asyncio.Event()

    async def complete(
        self,
        base_url: str,
        api_key: str,
        model: str,
        request: LlmRequest,
    ) -> LlmResult:
        self.calls.append((base_url, api_key, model, request))
        self.started.set()
        await self.after()
        if self.error:
            raise self.error
        return LlmResult(self.content, "returned-vision-fixture", 10, 400, 100)

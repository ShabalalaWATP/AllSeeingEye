"""Bridge the isolated document runner to framework-free extracted input records."""

from datetime import datetime
from pathlib import PurePath

from ase.adapters.research_imports import events_from_extraction
from ase.adapters.research_imports.models import ImportRejected
from ase.adapters.research_imports.runner import DocumentImportRunner
from ase.adapters.research_media import MEDIA_TYPES
from ase.adapters.research_media.events import events_from_media
from ase.application.ports.research_inputs import (
    MAX_PREVIEW_BYTES,
    InputExtraction,
    InputPreviewFrame,
)
from ase.domain.errors import InvalidRequest


class DocumentResearchImporter:
    def __init__(self, runner: DocumentImportRunner) -> None:
        self._runner = runner

    async def extract(self, data: bytes, filename: str, captured_at: datetime) -> InputExtraction:
        try:
            if PurePath(filename).suffix.lower() in MEDIA_TYPES:
                media = await self._runner.run_media(data, filename)
                frames: list[InputPreviewFrame] = []
                used_bytes = 0
                for frame in media.frames:
                    if len(frames) < 3 and used_bytes + len(frame.png) <= MAX_PREVIEW_BYTES:
                        frames.append(InputPreviewFrame(frame.seconds, frame.sha256, frame.png))
                        used_bytes += len(frame.png)
                limitations = media.limitations
                if len(frames) != len(media.frames):
                    limitations += ("Some previews were omitted to meet the 1 MiB preview budget.",)
                return InputExtraction(
                    media.filename,
                    media.media_type,
                    media.sha256,
                    events_from_media(media, captured_at),
                    limitations,
                    tuple(frames),
                )
            result = await self._runner.run(data, filename)
            return InputExtraction(
                result.filename,
                result.media_type,
                result.sha256,
                events_from_extraction(result, captured_at),
                result.limitations,
            )
        except ImportRejected as exc:
            raise InvalidRequest(str(exc)) from None

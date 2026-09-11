"""Compose private input intake with trusted, operator-selected local media tools."""

import asyncio
import shutil
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.research.runs import ResearchRunStore
from ase.adapters.research_imports.runner import DocumentImportRunner
from ase.adapters.research_inputs.importer import DocumentResearchImporter
from ase.adapters.research_inputs.memory import BoundedResearchInputStore
from ase.adapters.research_media.models import MediaTools
from ase.application.access import AccessPolicy
from ase.application.model_routing import ModelRouting
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research_inputs import DocumentImportPort, ResearchInputStore
from ase.application.ports.services import Clock, RateLimiter
from ase.application.research.inputs import ImportResearchInput
from ase.application.research.photo_geolocation import PhotoGeolocation
from ase.container.research_sources import research_source_specs
from ase.domain.llm import LlmUsage
from ase.infrastructure.settings import Settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from ase.container.repositories import Repositories


def input_services(
    settings: Settings, clock: Clock
) -> tuple[ResearchInputStore, DocumentImportPort]:
    tools = MediaTools(
        tesseract=shutil.which(settings.research_tesseract_path or "tesseract"),
        ffmpeg=shutil.which(settings.research_ffmpeg_path or "ffmpeg"),
        ffprobe=shutil.which(settings.research_ffprobe_path or "ffprobe"),
    )
    return BoundedResearchInputStore(clock), DocumentResearchImporter(
        DocumentImportRunner(media_tools=tools)
    )


class ResearchInputWiring:
    if TYPE_CHECKING:
        research_inputs: ResearchInputStore
        research_importer: DocumentImportPort
        clock: Clock
        limiter: RateLimiter
        cipher: SecretCipher
        llm: LlmGateway
        session_factory: async_sessionmaker[AsyncSession]

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def access_policy(self, session: AsyncSession) -> AccessPolicy: ...

    def initialise_research_inputs(self, settings: Settings) -> None:
        self.photo_admission = asyncio.Semaphore(2)
        self.research_runs = ResearchRunStore(self.clock)
        self.research_sources = research_source_specs(tuple(settings.disabled_feed_ids))
        self.research_inputs, self.research_importer = input_services(settings, self.clock)

    def import_research_input(self, session: AsyncSession) -> ImportResearchInput:
        return ImportResearchInput(
            self.access_policy(session),
            self.research_importer,
            self.research_inputs,
            self.clock,
            self.limiter,
            self.repositories(session).uow,
        )

    def photo_geolocation(self, session: AsyncSession) -> PhotoGeolocation:
        repos = self.repositories(session)

        async def record_usage(usage: LlmUsage) -> None:
            async with asyncio.timeout(5), self.session_factory() as usage_session:
                usage_repos = self.repositories(usage_session)
                await usage_repos.llm_usage.add(usage)
                await usage_repos.uow.commit()

        return PhotoGeolocation(
            self.access_policy(session),
            ModelRouting(repos.llm_profiles, repos.llm_bindings),
            self.research_inputs,
            self.llm,
            self.cipher,
            self.clock,
            self.limiter,
            repos.uow,
            self.photo_admission,
            record_usage,
        )

"""Ukraine war tracker: packaged snapshots plus the shared live store, no per-request network."""

from functools import cached_property
from typing import TYPE_CHECKING, cast
from uuid import UUID

from ase.adapters.feeds.ukraine_frontline import FrontlineProviders
from ase.adapters.geo.ukraine import load_control_snapshot, load_oblast_outlines
from ase.adapters.geo.ukraine_figures import load_civilian_harm, load_confirmed_losses
from ase.adapters.geo.ukraine_reference import load_reference_catalogue, load_reference_image
from ase.adapters.persistence.ukraine_digest import SqlUkraineDigestStore
from ase.application.auditing import Auditor
from ase.application.model_routing import ModelRouting
from ase.application.ukraine import UkraineBoardService
from ase.application.ukraine_digest import UkraineDigestService
from ase.application.ukraine_digest_writer import DigestWriter
from ase.domain.audit import AuditAction
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.ukraine.confirmed import CivilianHarm, ConfirmedLosses
from ase.domain.ukraine.control import ControlSnapshot, NamedOutline
from ase.domain.ukraine.reference import ReferenceCatalogue

if TYPE_CHECKING:
    from ase.container import Container


class GlobalDigestModel:
    """The digest is one shared page, so it only ever uses the globally assigned model."""

    def __init__(self, container: "Container") -> None:
        self._container = container

    async def profile(self) -> LlmProfile | None:
        if not self._container.cipher.available:
            return None
        async with self._container.session_factory() as session:
            repos = self._container.repositories(session)
            try:
                routing = await ModelRouting(repos.llm_profiles, repos.llm_bindings).snapshot()
                return routing.required(LlmRole.ASSESSMENT)
            except NoModelAvailable:
                return None


class UkraineWiring:
    @cached_property
    def ukraine_control(self) -> ControlSnapshot | None:
        return load_control_snapshot()

    @cached_property
    def ukraine_outlines(self) -> tuple[NamedOutline, ...]:
        return load_oblast_outlines()

    @cached_property
    def ukraine_reference(self) -> ReferenceCatalogue | None:
        return load_reference_catalogue()

    def ukraine_image(self, image_id: str) -> bytes | None:
        return load_reference_image(image_id)

    @cached_property
    def ukraine_confirmed(self) -> ConfirmedLosses | None:
        return load_confirmed_losses()

    @cached_property
    def ukraine_civilian_harm(self) -> CivilianHarm | None:
        return load_civilian_harm()

    @cached_property
    def ukraine_providers(self) -> FrontlineProviders:
        container = cast("Container", self)
        settings = container.settings
        return FrontlineProviders(
            container.http,
            container.clock,
            deepstate=settings.ukraine_deepstate_access == "granted",
            ocha=settings.ukraine_ocha_humanitarian,
            spotted=settings.ukraine_warspotting,
        )

    def ukraine(self) -> UkraineBoardService:
        container = cast("Container", self)
        return UkraineBoardService(
            container.store,
            container.clock,
            container.conflicts,
            self.ukraine_control,
            self.ukraine_confirmed,
            self.ukraine_civilian_harm,
        )

    @cached_property
    def ukraine_digest(self) -> UkraineDigestService:
        """One shared fortnightly digest; the service holds the cadence and the guard."""
        container = cast("Container", self)

        async def record_usage(usage: LlmUsage) -> None:
            async with container.session_factory() as session:
                await container.repositories(session).llm_usage.add(usage)
                await session.commit()

        async def record_refresh(actor_id: UUID, ip: str | None) -> None:
            async with container.session_factory() as session:
                repos = container.repositories(session)
                await Auditor(repos.audit, container.clock).record(
                    AuditAction.UKRAINE_DIGEST_REFRESH_REQUESTED,
                    actor=actor_id,
                    subject="ukraine",
                    ip=ip,
                )
                await session.commit()

        return UkraineDigestService(
            lambda: self.ukraine().board(),
            SqlUkraineDigestStore(container.session_factory),
            GlobalDigestModel(container),
            DigestWriter(
                # The shared system budget: unattended work no single account asked for.
                container.system_llm_gateway(),
                container.cipher,
                container.clock,
                record_usage,
            ),
            container.clock,
            container.source_admission,
            container.limiter,
            record_refresh,
        )

"""Explicit personal catalogue queries, reauthorised after external work."""

from collections.abc import Awaitable, Callable

from ase.application.dto import RequestContext
from ase.application.ports import Clock, RateLimiter
from ase.application.ports.footprints import FootprintProvider
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.errors import RateLimited, Unauthenticated
from ase.domain.footprints import FootprintCollection, FootprintQuery
from ase.domain.users import User


class FootprintSearchUseCase:
    source_id = "research-copernicus-footprints"

    def __init__(
        self,
        provider: FootprintProvider,
        limiter: RateLimiter,
        clock: Clock,
        admission: SourceAdmission | None = None,
    ) -> None:
        self.provider, self.limiter = provider, limiter
        self.clock, self.admission = clock, admission

    def _disabled(self) -> FootprintCollection:
        return FootprintCollection(
            (),
            "unavailable",
            False,
            "This catalogue source is disabled by the administrator; no results were admitted.",
            self.clock.now(),
        )

    async def execute(
        self,
        actor: User,
        query: FootprintQuery,
        context: RequestContext,
        revalidate: Callable[[], Awaitable[None]],
    ) -> FootprintCollection:
        if not actor.is_active:
            raise Unauthenticated()
        await revalidate()
        if self.admission is not None and not await self.admission.enabled(self.source_id):
            return self._disabled()
        for key in (f"footprint:user:{actor.id}", f"footprint:ip:{context.ip}"):
            retry = self.limiter.hit(key, 5, 300)
            if retry is not None:
                raise RateLimited(retry)
        result = await self.provider.search(query)
        if self.admission is not None:
            async with self.admission.guard():
                await revalidate()
                return result if await self.admission.enabled(self.source_id) else self._disabled()
        await revalidate()
        return result

"""Explicit, rate-limited public-name disclosure to a single registry."""

import asyncio
import re
from uuid import UUID

from ase.application.ports import RateLimiter
from ase.application.ports.lei_candidates import LeiCandidate, LeiCandidateLookup
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.errors import InvalidRequest, RateLimited


class FindLeiCandidates:
    def __init__(
        self, lookup: LeiCandidateLookup, limiter: RateLimiter, admission: SourceAdmission
    ) -> None:
        self.lookup, self.limiter, self.admission = lookup, limiter, admission

    async def require_enabled(self) -> None:
        if not await self.admission.enabled("research-gleif-profile"):
            raise InvalidRequest("GLEIF research is disabled by the administrator.")

    async def search(
        self, user_id: UUID, name: str, country: str | None
    ) -> tuple[LeiCandidate, ...]:
        name = name.strip()
        if not 2 <= len(name) <= 200 or any(ord(char) < 32 for char in name):
            raise InvalidRequest("Enter a company name of 2 to 200 characters.")
        if country is not None and not re.fullmatch(r"[A-Z]{2}", country):
            raise InvalidRequest("Choose a two-letter country code.")
        await self.require_enabled()
        retry = self.limiter.hit(f"lei-candidates:{user_id}", 20, 900)
        if retry is not None:
            raise RateLimited(retry)
        try:
            async with asyncio.timeout(20):
                return (await self.lookup.search(name, country))[:10]
        except TimeoutError:
            raise InvalidRequest("GLEIF lookup timed out. No retry was made.") from None

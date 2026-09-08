"""Explicit SEC listing and selected-document execution over one shared paced client."""

import asyncio
from datetime import date

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.research_imports.runner import _settle
from ase.adapters.research_records.sec_client import SecClient
from ase.adapters.research_records.sec_document import document_url, extract
from ase.adapters.research_records.sec_history import identity, page
from ase.application.ports import Clock
from ase.application.ports.research_inputs import InputExtraction
from ase.domain.errors import InvalidRequest
from ase.domain.sec_filings import SecFiling, SecFilingPage


async def _join_parser(task: asyncio.Task[InputExtraction]) -> None:
    await asyncio.gather(task, return_exceptions=True)


class SecDocuments:
    def __init__(self, client: SecClient, clock: Clock) -> None:
        self.client, self.clock = client, clock

    async def list(
        self, cik: str, since: date, until: date, archive_page: int, offset: int
    ) -> SecFilingPage:
        try:
            self.client.require_configured()
        except FeedFetchError as exc:
            raise InvalidRequest(str(exc)) from None
        try:
            return await page(self.client, identity(cik), since, until, archive_page, offset)
        except (FeedFetchError, ValueError, TypeError, KeyError, OverflowError, RecursionError):
            raise InvalidRequest(
                "SEC listing is unavailable or invalid. No retry was made."
            ) from None

    async def fetch(self, filing: SecFiling) -> tuple[InputExtraction, bytes]:
        try:
            data = await self.client.get_bytes(document_url(filing))
            # Bound work and join the parser before cancellation releases its reserved memory.
            task = asyncio.create_task(asyncio.to_thread(extract, data, filing, self.clock.now()))
            try:
                result = await asyncio.shield(task)
            finally:
                if not task.done():
                    _, interrupted = await _settle(asyncio.create_task(_join_parser(task)))
                    if interrupted:
                        raise asyncio.CancelledError
            return result, data
        except (FeedFetchError, ValueError, TypeError, UnicodeError):
            raise InvalidRequest(
                "SEC filing unavailable, unsupported or exceeds extraction limits. "
                "No retry was made."
            ) from None

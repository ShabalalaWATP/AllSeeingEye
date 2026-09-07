"""Selected package delivery performs fresh checks and shares render capacity."""

import asyncio
from threading import Event
from unittest.mock import AsyncMock

import pytest

from ase.adapters.reports.claim_evidence_package import SelectedClaimPackageRenderer
from ase.application.reports.claim_export_selection import ClaimExportReference, SelectClaimExport
from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.application.reports.export_claim_package import ExportClaimPackage
from ase.domain.errors import Conflict, NotFound, RateLimited
from test_claim_repository import seed
from test_saved_map_views import claims_for


@pytest.mark.parametrize("revoked", [False, True])
async def test_package_delivered_only_after_successful_recheck(client, container, user, revoked):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        selector = SelectClaimExport(
            container.report_claims(session), repositories.reports, repositories.uow
        )
        checked = AsyncMock(wraps=selector.recheck, side_effect=NotFound() if revoked else None)
        selector.recheck = checked
        exporter = ExportClaimPackage(selector, SelectedClaimPackageRenderer())
        references = (ClaimExportReference(revision.claim_id, revision.id),)
        if revoked:
            with pytest.raises(NotFound):
                await exporter.execute(actor, report.id, 1, references)
        else:
            result = await exporter.execute(actor, report.id, 1, references)
            assert result.content.startswith(b"PK")
        checked.assert_awaited_once()


async def test_saturated_shared_package_workers_reject_export(client, container, user):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    async with container.session_factory() as session:
        repositories = container.repositories(session)
        exporter = ExportClaimPackage(
            SelectClaimExport(
                container.report_claims(session), repositories.reports, repositories.uow
            ),
            SelectedClaimPackageRenderer(),
        )
        assert _PACKAGE_SLOTS.acquire(blocking=False)
        assert _PACKAGE_SLOTS.acquire(blocking=False)
        try:
            with pytest.raises(RateLimited):
                await exporter.execute(
                    actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
                )
        finally:
            _PACKAGE_SLOTS.release()
            _PACKAGE_SLOTS.release()


async def test_cancelled_download_keeps_slot_until_compression_finishes(client, container, user):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)
    entered, finish, ended = Event(), Event(), Event()

    class SlowRenderer:
        def render(self, record, version, revisions):
            entered.set()
            try:
                assert finish.wait(5)
                return b"zip"
            finally:
                ended.set()

    async with container.session_factory() as session:
        repositories = container.repositories(session)
        selector = SelectClaimExport(
            container.report_claims(session), repositories.reports, repositories.uow
        )
        checked = AsyncMock(wraps=selector.recheck)
        selector.recheck = checked
        exporter = ExportClaimPackage(selector, SlowRenderer())
        task = asyncio.create_task(
            exporter.execute(
                actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
            )
        )
        try:
            assert await asyncio.to_thread(entered.wait, 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            checked.assert_not_awaited()
            assert _PACKAGE_SLOTS.acquire(blocking=False)
            try:
                assert not _PACKAGE_SLOTS.acquire(blocking=False)
            finally:
                _PACKAGE_SLOTS.release()
        finally:
            finish.set()
            assert await asyncio.to_thread(ended.wait, 5)
            async with asyncio.timeout(5):
                while True:
                    recovered = 0
                    try:
                        while recovered < 2 and _PACKAGE_SLOTS.acquire(blocking=False):
                            recovered += 1
                    finally:
                        for _ in range(recovered):
                            _PACKAGE_SLOTS.release()
                    if recovered == 2:
                        break
                    await asyncio.sleep(0.01)


async def test_renderer_content_mutation_prevents_delivery(client, container, user):
    actor = await claims_for(client, container, user)
    report, _, revision = await seed(container, user)

    class MutatingRenderer:
        def render(self, record, version, revisions):
            version.markdown = "Unexpected replacement"
            return b"zip"

    async with container.session_factory() as session:
        repositories = container.repositories(session)
        exporter = ExportClaimPackage(
            SelectClaimExport(
                container.report_claims(session), repositories.reports, repositories.uow
            ),
            MutatingRenderer(),
        )
        with pytest.raises(Conflict):
            await exporter.execute(
                actor, report.id, 1, (ClaimExportReference(revision.claim_id, revision.id),)
            )

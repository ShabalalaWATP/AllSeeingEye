"""Application factory."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ase import __version__
from ase.api.errors import register_error_handlers
from ase.api.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from ase.api.router import api_router
from ase.application.ports import Clock, EmailSender, RateLimiter
from ase.application.ports.feeds import FeedConnector
from ase.container import Container
from ase.container.annotation_monitor_worker import build_annotation_monitor_worker
from ase.container.original_asset_expiry import expire_original_assets
from ase.infrastructure.logging import configure_logging
from ase.infrastructure.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    if container.settings.feeds_enabled:
        await container.scheduler.start()
        await container.aviation_monitor.start()
        await container.evaluator.start()
        await container.translation_queue.start()
        await container.conflict_screening.start()
        await container.social_monitor.start()
    await container.schedule_runner.start()
    asset_expiry = asyncio.create_task(
        expire_original_assets(container.session_factory, container.clock)
    )
    annotation_monitoring = asyncio.create_task(build_annotation_monitor_worker(container).run())
    await container.report_job_worker.start()
    try:
        yield
    finally:
        await container.schedule_runner.stop()
        await container.report_job_worker.stop()
        annotation_monitoring.cancel()
        await asyncio.gather(annotation_monitoring, return_exceptions=True)
        asset_expiry.cancel()
        await asyncio.gather(asset_expiry, return_exceptions=True)
        await container.social_monitor.stop()
        await container.translation_queue.stop()
        await container.conflict_screening.stop()
        await container.evaluator.stop()
        await container.aviation_monitor.stop()
        await container.scheduler.stop()
        await container.dispose()


def create_app(
    settings: Settings | None = None,
    *,
    clock: Clock | None = None,
    limiter: RateLimiter | None = None,
    email_sender: EmailSender | None = None,
    connectors: Sequence[FeedConnector] | None = None,
) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)
    container = Container(
        settings,
        clock=clock,
        limiter=limiter,
        email_sender=email_sender,
        connectors=connectors,
    )
    app = FastAPI(
        title="The All Seeing Eye API",
        version=__version__,
        docs_url="/api/docs" if settings.is_dev else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.is_dev else None,
        lifespan=lifespan,
    )
    app.state.container = container
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    register_error_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()

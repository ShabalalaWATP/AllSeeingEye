"""Application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ase import __version__
from ase.api.errors import register_error_handlers
from ase.api.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from ase.api.router import api_router
from ase.application.ports import Clock, EmailSender, RateLimiter
from ase.container import Container
from ase.infrastructure.logging import configure_logging
from ase.infrastructure.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    container: Container = app.state.container
    await container.dispose()


def create_app(
    settings: Settings | None = None,
    *,
    clock: Clock | None = None,
    limiter: RateLimiter | None = None,
    email_sender: EmailSender | None = None,
) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)
    container = Container(settings, clock=clock, limiter=limiter, email_sender=email_sender)
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

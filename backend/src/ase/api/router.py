"""Aggregates every router under the /api prefix."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.routers import (
    admin_audit,
    admin_requests,
    admin_sources,
    admin_users,
    auth,
    capabilities,
    countries,
    events,
    health,
    me,
    stream,
    tiles,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(events.router)
api_router.include_router(countries.router)
api_router.include_router(capabilities.router)
api_router.include_router(tiles.router)
api_router.include_router(stream.router)
api_router.include_router(admin_requests.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_audit.router)
api_router.include_router(admin_sources.router)

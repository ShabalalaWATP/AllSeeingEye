"""Aggregates every router under the /api prefix."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.routers import (
    account,
    admin_audit,
    admin_llm,
    admin_requests,
    admin_sources,
    admin_users,
    auth,
    capabilities,
    countries,
    direction,
    events,
    health,
    me,
    report_documents,
    report_search,
    reports,
    schedules,
    social,
    stream,
    teams,
    tiles,
    totp,
    trackers,
    warning,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(totp.router)
api_router.include_router(teams.router)
api_router.include_router(me.router)
api_router.include_router(account.router)
api_router.include_router(events.router)
api_router.include_router(countries.router)
api_router.include_router(capabilities.router)
api_router.include_router(tiles.router)
api_router.include_router(reports.router)
api_router.include_router(report_documents.router)
api_router.include_router(report_search.router)
api_router.include_router(social.router)
api_router.include_router(stream.router)
api_router.include_router(trackers.router)
api_router.include_router(direction.router)
api_router.include_router(warning.router)
api_router.include_router(schedules.router)
api_router.include_router(admin_requests.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_audit.router)
api_router.include_router(admin_sources.router)
api_router.include_router(admin_llm.router)

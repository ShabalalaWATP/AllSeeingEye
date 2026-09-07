"""Aggregates every router under the /api prefix."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.routers import (
    account,
    account_sessions,
    admin_audit,
    admin_llm,
    admin_llm_discovery,
    admin_requests,
    admin_sources,
    admin_users,
    annotation_comparisons,
    annotation_monitors,
    auth,
    capabilities,
    claims,
    countries,
    direction,
    events,
    footprints,
    health,
    identities,
    map_image,
    map_views,
    me,
    mfa,
    original_assets,
    profile,
    recovery,
    relationships,
    report_documents,
    report_methodology,
    report_search,
    reports,
    research_inputs,
    research_library,
    research_runs,
    schedules,
    social,
    sources,
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
api_router.include_router(mfa.router)
api_router.include_router(teams.router)
api_router.include_router(me.router)
api_router.include_router(account.router)
api_router.include_router(profile.router)
api_router.include_router(account_sessions.router)
api_router.include_router(recovery.router)
api_router.include_router(events.router)
api_router.include_router(footprints.router)
api_router.include_router(map_views.router)
api_router.include_router(map_image.router)
api_router.include_router(original_assets.router)
api_router.include_router(claims.router)
api_router.include_router(identities.router)
api_router.include_router(annotation_comparisons.router)
api_router.include_router(annotation_monitors.router)
api_router.include_router(relationships.router)
api_router.include_router(research_library.router)
api_router.include_router(countries.router)
api_router.include_router(capabilities.router)
api_router.include_router(tiles.router)
api_router.include_router(reports.router)
api_router.include_router(research_inputs.router)
api_router.include_router(research_runs.router)
api_router.include_router(report_documents.router)
api_router.include_router(report_methodology.router)
api_router.include_router(report_search.router)
api_router.include_router(social.router)
api_router.include_router(sources.router)
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
api_router.include_router(admin_llm_discovery.router)

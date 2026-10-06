"""Independent public registration oracle, preserving the pre-KAN-71 include order."""

import ast
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from starlette.convertors import CONVERTOR_TYPES

from ase import __version__
from ase.api import router as aggregate
from ase.api.errors import register_error_handlers
from ase.api.schemas_errors import ErrorEnvelope

ORIGINAL = [
    "report_stix",
    "csp_reports",
    "cyber",
    "economy",
    "economy_news",
    "daily_briefing",
    "report_jobs",
    "assistant",
    "assistant_history",
    "ai_usage",
    "research_usage",
    "health",
    "navigation",
    "terrain",
    "radio",
    "auth",
    "totp",
    "mfa",
    "teams",
    "team_board",
    "team_dashboard",
    "bell",
    "team_invitations",
    "me",
    "account",
    "private_feed",
    "notification_preferences",
    "web_push",
    "notification_alert",
    "notification_digest",
    "profile",
    "directory",
    "account_sessions",
    "recovery",
    "events",
    "footprints",
    "map_views",
    "map_workspace",
    "map_image",
    "original_assets",
    "original_passages",
    "claims",
    "identities",
    "annotation_comparisons",
    "annotation_monitors",
    "relationships",
    "report_ledgers",
    "forecast_watches",
    "research_library",
    "countries",
    "capabilities",
    "cameras",
    "tiles",
    "reports",
    "report_team_copies",
    "research_briefs",
    "research_preflight",
    "research_presets",
    "research_inputs",
    "sec_filings",
    "lei_candidates",
    "research_runs",
    "report_documents",
    "report_methodology",
    "report_search",
    "social",
    "sources",
    "source_track_record",
    "source_reviews",
    "citation_verdicts",
    "stream",
    "trackers",
    "direction",
    "warning",
    "alert_routing",
    "schedules",
    "subscription_usage",
    "admin_requests",
    "admin_runtime",
    "admin_users",
    "admin_audit",
    "admin_sources",
    "admin_subscription_diagnostics",
    "admin_llm",
    "admin_llm_discovery",
    "admin_evaluations",
    "admin_ai_usage",
    "admin_research_quality",
    "admin_firms_credentials",
    "infrastructure",
    "figures",
    "reference",
    "ukraine",
]


def registered_owners() -> list[str]:
    """Read the literal public include calls, refusing hidden registration options."""
    tree = ast.parse(Path(aggregate.__file__).read_text(encoding="utf-8"))
    owners = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        assert isinstance(call.func, ast.Attribute)
        assert ast.unparse(call.func) == "api_router.include_router"
        assert len(call.args) == 1 and not call.keywords
        target = call.args[0]
        assert isinstance(target, ast.Attribute) and target.attr == "router"
        assert isinstance(target.value, ast.Name)
        owners.append(target.value.id)
    return owners


def reference_router() -> APIRouter:
    reference = APIRouter()
    for owner in ORIGINAL:
        reference.include_router(getattr(aggregate, owner).router)
    return reference


def application(router: APIRouter) -> FastAPI:
    result = FastAPI(
        title="The All Seeing Eye API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        responses={422: {"model": ErrorEnvelope}, "default": {"model": ErrorEnvelope}},
    )
    register_error_handlers(result)
    result.include_router(router, prefix="/api")
    return result


def routes(app: FastAPI) -> Iterator[Any]:
    # Same inspection seam as the existing session-fence architecture audit. It is
    # used only in tests; production registration uses include_router unchanged.
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route
        else:
            assert hasattr(route, "effective_route_contexts")
            for context in route.effective_route_contexts():
                assert isinstance(context.original_route, APIRoute)
                yield context


def path_parameters(route: Any) -> dict[str, Any]:
    values = {
        "str": "sample",
        "path": "sample/child",
        "int": 1,
        "float": 1.5,
        "uuid": UUID("00000000-0000-4000-8000-000000000001"),
    }
    result = {}
    for name, convertor in route.param_convertors.items():
        kinds = [kind for kind, known in CONVERTOR_TYPES.items() if type(convertor) is type(known)]
        assert len(kinds) == 1 and kinds[0] in values, "Review a new path convertor"
        result[name] = values[kinds[0]]
    return result


def concrete_path(route: Any) -> str:
    values = path_parameters(route)
    return route.path_format.format(
        **{name: route.param_convertors[name].to_string(value) for name, value in values.items()}
    )

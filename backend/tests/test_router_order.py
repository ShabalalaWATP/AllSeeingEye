"""Route grouping must preserve matching, reverse lookup and the complete API contract."""

import ast
import json
from itertools import combinations
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from starlette.responses import JSONResponse
from starlette.types import Receive, Scope, Send

from ase.api import router as aggregate
from router_order_reference import (
    ORIGINAL,
    application,
    concrete_path,
    path_parameters,
    reference_router,
    registered_owners,
    routes,
)


@pytest.fixture(scope="module")
def pair() -> tuple[FastAPI, FastAPI]:
    return application(reference_router()), application(aggregate.api_router)


def test_all_owners_once_and_every_overlap_and_name_edge_preserved() -> None:
    actual = registered_owners()
    assert len(actual) == len(set(actual)) == len(ORIGINAL) == 94
    assert set(actual) == set(ORIGINAL)
    families: dict[str, set[str]] = {}
    names: dict[str, set[str]] = {}
    count = 0
    for owner in ORIGINAL:
        current = list(routes(application(getattr(aggregate, owner).router)))
        count += len(current)
        families[owner] = set()
        names[owner] = set()
        for route in current:
            first = route.path.removeprefix("/api/").split("/")[0]
            assert first and "{" not in first, "Review dynamic leading-path matching"
            families[owner].add(first)
            names[owner].add(route.name)
    assert count == 352
    for before, after in combinations(ORIGINAL, 2):
        if families[before] & families[after] or names[before] & names[after]:
            assert actual.index(before) < actual.index(after), (before, after)


def test_no_order_sensitive_router_lifecycle_or_custom_registration() -> None:
    forbidden = {"lifespan", "on_startup", "on_shutdown", "route_class", "routes"}
    directory = Path(aggregate.__file__).parent / "routers"
    for path in directory.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id == "APIRouter":
                assert not any(key.arg is None or key.arg in forbidden for key in node.keywords)
            if isinstance(node.func, ast.Attribute):
                assert node.func.attr not in {"on_event", "add_event_handler", "add_route", "mount"}


def test_full_openapi_structure_and_operation_identifiers_are_equal(pair) -> None:
    original, candidate = (app.openapi() for app in pair)
    # JSON object ordering is deliberately not an API semantic. All arrays,
    # schemas, operation IDs, security, responses and dependency order are exact.
    assert candidate == original
    assert json.dumps(candidate, sort_keys=True) == json.dumps(original, sort_keys=True)
    # Do not silently claim byte-identical exports: the public exporter preserves
    # path insertion order, which follows this deliberately changed registration.
    assert set(candidate["paths"]) == set(original["paths"])


def test_every_reverse_name_and_parameter_signature_keeps_its_winner(pair) -> None:
    original, candidate = pair
    for route in routes(original):
        parameters = path_parameters(route)
        assert candidate.url_path_for(route.name, **parameters) == original.url_path_for(
            route.name, **parameters
        ), (route.name, parameters)


def test_effective_routes_keep_endpoint_dependencies_provider_and_metadata(pair) -> None:
    original, candidate = pair
    expected = {(r.path, tuple(sorted(r.methods))): r for r in routes(original)}
    actual = {(r.path, tuple(sorted(r.methods))): r for r in routes(candidate)}
    assert actual.keys() == expected.keys()
    for key, route in actual.items():
        prior = expected[key]
        assert route.original_route is prior.original_route
        assert route.endpoint is prior.endpoint
        assert route.dependencies == prior.dependencies
        assert route.tags == prior.tags
        assert route.responses == prior.responses
        assert route.response_model is prior.response_model
        assert route.response_class is prior.response_class
        assert route.dependency_overrides_provider is candidate
        assert prior.dependency_overrides_provider is original


async def test_all_http_matches_methods_redirects_and_missing_paths(pair, monkeypatch) -> None:
    original, candidate = pair
    real_handle = APIRoute.handle

    async def matched(route: APIRoute, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["method"] not in route.methods:
            await real_handle(route, scope, receive, send)
            return
        response = JSONResponse(
            {
                "endpoint": f"{route.endpoint.__module__}.{route.endpoint.__qualname__}",
                "path": scope["route"].path,
                "parameters": {key: str(value) for key, value in scope["path_params"].items()},
            }
        )
        await response(scope, receive, send)

    monkeypatch.setattr(APIRoute, "handle", matched)
    cases = set()
    for route in routes(original):
        path = concrete_path(route)
        cases.update((method, path) for method in route.methods)
        cases.add(("BREW", path))
        cases.add(("GET", path.rstrip("/") + "/"))
    cases.update(
        ("GET", path)
        for path in (
            "/api/does-not-exist",
            "/api/auth/does-not-exist",
            "/api/reports/sample/missing",
        )
    )
    async with (
        AsyncClient(transport=ASGITransport(app=original), base_url="http://test") as old,
        AsyncClient(transport=ASGITransport(app=candidate), base_url="http://test") as new,
    ):
        for method, path in sorted(cases):
            left, right = await old.request(method, path), await new.request(method, path)
            assert (right.status_code, right.content) == (left.status_code, left.content), (
                method,
                path,
            )
            for header in ("allow", "location", "content-type"):
                assert right.headers.get(header) == left.headers.get(header), (method, path)

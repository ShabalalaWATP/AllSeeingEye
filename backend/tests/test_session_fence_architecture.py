"""The release fence is the only way routes re-validate a session, and nobody forgets it."""

import ast
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute

from ase.api.deps import get_access_claims, get_admin_user, get_current_user
from ase.api.session_fence import request_fence

API = Path(__file__).resolve().parents[1] / "src" / "ase" / "api"
ALLOWLIST = Path(__file__).parent / "fixtures" / "routes_without_release_fence.txt"
AUTHENTICATED = {get_current_user, get_access_claims, get_admin_user}
# Start-of-request authentication and the fence itself read the session directly; the
# stream re-validates with its own transaction when due and before every alert.
DIRECT_SESSION_READERS = {"deps.py", "session_fence.py", "stream.py"}
SESSION_READER = "ase.application.auth.current_session"


def _calls(dependant: Any) -> Iterator[Callable[..., Any]]:
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _calls(dependency)


def _routes(app: FastAPI) -> Iterator[Any]:
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "effective_route_contexts"):
            yield from route.effective_route_contexts()


def _unfenced_authenticated(app: FastAPI) -> set[str]:
    unfenced = set()
    for route in _routes(app):
        found = set(_calls(route.dependant))
        if found & AUTHENTICATED and request_fence not in found:
            for method in route.methods - {"HEAD", "OPTIONS"}:
                unfenced.add(f"{method} {route.path}")
    return unfenced


def _allowlist() -> set[str]:
    lines = ALLOWLIST.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def test_every_authenticated_route_is_fenced_or_explicitly_exempt(app: FastAPI) -> None:
    unfenced = _unfenced_authenticated(app)
    allowed = _allowlist()
    assert sorted(unfenced - allowed) == [], "take FenceDep or justify an allowlist entry"
    assert sorted(allowed - unfenced) == [], "remove stale allowlist entries"


def test_routes_re_validate_only_through_the_fence() -> None:
    offenders = []
    for path in sorted(API.rglob("*.py")):
        if path.name in DIRECT_SESSION_READERS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == SESSION_READER:
                offenders.append(f"{path.name}:{node.lineno}")
    assert offenders == []


def test_no_websocket_route_escapes_the_fence_check() -> None:
    # The route check above inspects HTTP routes only; extend it before adding sockets.
    sockets = [
        f"{path.name}:{node.lineno}"
        for path in sorted(API.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, ast.Attribute) and node.attr in {"websocket", "websocket_route"}
    ]
    assert sockets == []

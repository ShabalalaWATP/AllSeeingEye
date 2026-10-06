"""Grouping keeps fresh application state and avoids unrelated cold-route construction."""

from collections.abc import AsyncIterator
from typing import Annotated, Any

import fastapi.routing
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from ase.api import router as aggregate
from ase.api.schemas_errors import ErrorEnvelope
from router_order_reference import application, reference_router


async def test_broad_login_then_family_requests_construct_fewer_unrelated_routes(
    monkeypatch,
    record_property,
) -> None:
    # These families span the authoritative selected corpus, not just the local
    # 16-case diagnostic. This counts work only; it is not a timing assertion.
    targets = (
        ("GET", "/api/me"),
        ("GET", "/api/reports"),
        ("GET", "/api/admin/users"),
        ("POST", "/api/research/inputs"),
        ("GET", "/api/schedules"),
        ("GET", "/api/report-jobs"),
    )
    create_field = fastapi.routing.create_model_field
    fields: list[str] = []

    def observe(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("type_") is ErrorEnvelope:
            fields.append(kwargs["name"])
        return create_field(*args, **kwargs)

    async def matched(route: APIRoute, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["method"] in route.methods
        await Response(status_code=204)(scope, receive, send)

    monkeypatch.setattr(fastapi.routing, "create_model_field", observe)
    monkeypatch.setattr(APIRoute, "handle", matched)
    totals = []
    for router in (reference_router(), aggregate.api_router):
        fields.clear()
        for method, path in targets:
            current = application(router)
            async with AsyncClient(
                transport=ASGITransport(app=current), base_url="http://test"
            ) as client:
                assert (await client.post("/api/auth/login")).status_code == 204
                assert (await client.request(method, path)).status_code == 204
        totals.append(len(fields))
    record_property("original_error_fields", totals[0])
    record_property("candidate_error_fields", totals[1])
    assert totals[1] < totals[0], {"original_fields": totals[0], "candidate_fields": totals[1]}


@pytest.mark.parametrize("denied_status", [401, 403])
async def test_fresh_overrides_validation_order_and_yield_cleanup(denied_status: int) -> None:
    applications = [application(reference_router()), application(aggregate.api_router)]
    entries: list[FastAPI] = []
    exits: list[FastAPI] = []

    async def permitted() -> str:
        raise HTTPException(denied_status, "denied", headers={"X-Reason": "scope"})

    async def endpoint(value: int, actor: Annotated[str, Depends(permitted)]) -> dict[str, str]:
        return {"actor": actor, "value": str(value)}

    for current in applications:
        # Bind each provider separately, as the normal production factory does.
        def scope_factory(app: FastAPI):
            async def scoped() -> AsyncIterator[None]:
                entries.append(app)
                try:
                    yield
                finally:
                    exits.append(app)

            return scoped

        current.add_api_route(
            "/precedence", endpoint, dependencies=[Depends(scope_factory(current))]
        )

    for index, current in enumerate(applications):
        async with AsyncClient(
            transport=ASGITransport(app=current), base_url="http://test"
        ) as client:
            response = await client.get("/precedence?value=invalid")
            assert response.status_code == denied_status
            assert response.headers["x-reason"] == "scope"
            assert response.json()["error"]["message"] == "denied"
            assert entries == exits
            assert entries[-1] is current

            current.dependency_overrides[permitted] = lambda: "current app"
            invalid = await client.get("/precedence?value=invalid")
            assert invalid.status_code == 422
            assert invalid.json()["error"]["code"] == "validation_error"
            assert (await client.get("/precedence?value=1")).json() == {
                "actor": "current app",
                "value": "1",
            }
            assert entries == exits
        if index == 0:
            assert applications[1].dependency_overrides == {}


def test_new_routes_invalidate_only_the_owning_apps_schema() -> None:
    first, other = application(aggregate.api_router), application(aggregate.api_router)
    before = first.openapi()
    untouched = other.openapi()

    async def extra() -> dict[str, str]:
        return {"status": "current"}

    first.add_api_route("/extra", extra, tags=["extra"], deprecated=True)
    assert first.openapi() is not before
    assert "/extra" in first.openapi()["paths"]
    assert other.openapi() is untouched
    assert "/extra" not in untouched["paths"]

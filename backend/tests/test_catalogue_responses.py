"""Catalogue caches preserve authentication, revocation and response validators."""

from dataclasses import replace

import pytest
from pydantic import BaseModel

from ase.api.catalogue_responses import CatalogueResponses
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


class Catalogue(BaseModel):
    name: str


def test_serialised_bytes_reused_until_snapshot_replaced():
    cache = CatalogueResponses()
    first, second = object(), object()
    count = 0

    def build():
        nonlocal count
        count += 1
        return Catalogue(name=str(count))

    old = cache.get("/api/countries", first, build)
    assert cache.get("/api/countries", first, build) is old and count == 1
    fresh = cache.get("/api/countries", second, build)
    assert fresh.etag != old.etag and count == 2
    for validator in (
        old.etag,
        old.etag.removeprefix("W/"),
        "*",
        f'"other", {old.etag}',
        f'"other,quoted", {old.etag}',
        " * ",
    ):
        response = old.response(validator)
        assert response.status_code == 304 and response.body == b""
    for invalid in (None, "invalid", old.etag + ", invalid", '"other"'):
        assert old.response(invalid).status_code == 200


@pytest.mark.parametrize("route", ["/api/map-infrastructure", "/api/countries"])
async def test_conditional_catalogue_authentication_and_revocation(client, container, user, route):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    response = await client.get(route, headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-cache"
    assert "Accept-Encoding" in response.headers["vary"]
    etag = response.headers["etag"]
    conditional = headers | {"if-none-match": etag}
    repeated = await client.get(route, headers=conditional)
    assert repeated.status_code == 304 and repeated.content == b""
    anonymous = await client.get(route, headers={"if-none-match": etag})
    assert anonymous.status_code == 401 and "no-store" in anonymous.headers["cache-control"]
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.users.save(replace(user, is_active=False))
        await repos.uow.commit()
    revoked = await client.get(route, headers=conditional)
    assert revoked.status_code == 401 and "no-store" in revoked.headers["cache-control"]

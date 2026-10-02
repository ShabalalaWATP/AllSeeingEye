"""The STIX endpoint fences exact version and session changes after rendering."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.reports.stix import ExportStix
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_stix_export import cyber_records


@pytest.mark.parametrize("change", [None, "expiry", "version"])
async def test_release_fence(client, container, user, clock, monkeypatch, change):
    record, version = cyber_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    execute = ExportStix.execute
    rendered = []

    async def finish(self, *args):
        result = await execute(self, *args)
        rendered.append(result.content)
        if change == "expiry":
            clock.advance(timedelta(minutes=16))
        if change == "version":
            result = replace(result, report_version_id=uuid4())
        return result

    monkeypatch.setattr(ExportStix, "execute", finish)
    path = f"/api/reports/{record.id}/stix?version=1&tlp=amber"
    assert (await client.get(path)).status_code == 401
    response = await client.get(path, headers=bearer(token))
    assert len(rendered) == 1
    if change is None:
        assert response.status_code == 200
        assert response.content == rendered[0]
        assert response.headers["content-type"] == "application/stix+json"
        assert response.headers["cache-control"] == "private, no-store"
    else:
        assert response.status_code == (401 if change == "expiry" else 409)
        assert response.content != rendered[0]
        assert "content-disposition" not in response.headers

"""Schedule reads and updates keep the original session valid through release."""

from datetime import timedelta
from unittest.mock import patch
from uuid import UUID

from ase.application.auditing import Auditor
from ase.application.schedules.manage import ListSchedulesUseCase
from ase.domain.audit import AuditAction
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

_BODY = {"name": "Session fence", "template_id": "intsum"}


async def test_schedule_list_rechecks_expiry_after_authorised_read(client, container, user) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    original = ListSchedulesUseCase.execute

    async def delayed(self, actor):
        result = await original(self, actor)
        container.clock.advance(timedelta(days=1))
        return result

    with patch.object(ListSchedulesUseCase, "execute", delayed):
        response = await client.get("/api/schedules", headers=bearer(token))
    assert response.status_code == 401
    assert "items" not in response.json()


async def test_schedule_update_rolls_back_if_session_expires_before_commit(
    client, container, user
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post("/api/schedules", json=_BODY, headers=bearer(token))
    assert created.status_code == 201, created.text
    schedule_id = created.json()["id"]
    original = Auditor.record

    async def delayed(self, action, **kwargs):
        result = await original(self, action, **kwargs)
        if action is AuditAction.SCHEDULE_UPDATED:
            container.clock.advance(timedelta(days=1))
        return result

    with patch.object(Auditor, "record", delayed):
        response = await client.put(
            f"/api/schedules/{schedule_id}",
            json={**_BODY, "name": "Should roll back"},
            headers=bearer(token),
        )
    assert response.status_code == 401
    async with container.session_factory() as session:
        stored = await container.repositories(session).schedules.get(UUID(schedule_id))
    assert stored is not None and stored.name == "Session fence"

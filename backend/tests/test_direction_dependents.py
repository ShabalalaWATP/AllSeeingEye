"""KAN-199: areas and plans in use are not deleted out from under their dependents."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from ase.adapters.persistence.models import CollectionPlanRow
from ase.application.direction.dependents import linked_names, refuse_plan_in_use
from ase.container import Container
from ase.domain.collection import LinkedRecords
from ase.domain.errors import Conflict
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

AREA = {"name": "Eastern Ukraine", "kind": "bbox", "bbox": [30, 44, 41, 53]}
PLAN = {"name": "Kharkiv axis", "countries": ["ua"], "pirs": [{"text": "What changed?"}]}
RULE = {"name": "Kharkiv strikes", "countries": ["UA"], "keywords": ["Kharkiv"], "threshold": 2}


async def _post(client: AsyncClient, token: str, path: str, body: dict[str, Any]) -> Any:
    response = await client.post(path, json=body, headers=bearer(token))
    assert response.status_code == 201, response.text
    return response.json()


async def test_area_used_by_a_plan_is_refused_until_the_plan_changes(
    client: AsyncClient, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    area = await _post(client, token, "/api/direction/aois", AREA)
    plan = await _post(client, token, "/api/direction/plans", {**PLAN, "aoi_id": area["id"]})
    refused = await client.delete(f"/api/direction/aois/{area['id']}", headers=bearer(token))
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["message"] == (
        "This area is used by 1 collection plan: Kharkiv axis. Choose another area for those "
        "plans or delete them, then delete this area."
    )
    evidence = await client.get(f"/api/direction/plans/{plan['id']}", headers=bearer(token))
    assert evidence.status_code == 200 and evidence.json()["aoi"]["name"] == AREA["name"]
    unlinked = await client.put(
        f"/api/direction/plans/{plan['id']}",
        json={**PLAN, "expected_updated_at": plan["updated_at"]},
        headers=bearer(token),
    )
    assert unlinked.status_code == 200 and unlinked.json()["aoi_id"] is None
    deleted = await client.delete(f"/api/direction/aois/{area['id']}", headers=bearer(token))
    assert deleted.status_code == 204
    after = await client.get(f"/api/direction/plans/{plan['id']}", headers=bearer(token))
    assert after.status_code == 200, after.text


async def test_a_hidden_linked_plan_is_counted_but_never_named(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    area = await _post(client, token, "/api/direction/aois", AREA)
    now = container.clock.now()
    async with container.session_factory() as session:
        # A legacy cross-scope link that current validation would refuse to create.
        session.add(
            CollectionPlanRow(
                id=uuid4(),
                name="Administrator private plan",
                description="",
                aoi_id=UUID(area["id"]),
                countries=[],
                pirs=[],
                enabled=True,
                created_by=admin.id,
                created_at=now,
                updated_at=now,
                team_id=None,
            )
        )
        await session.commit()
    refused = await client.delete(f"/api/direction/aois/{area['id']}", headers=bearer(token))
    assert refused.status_code == 409
    message = refused.json()["error"]["message"]
    assert "1 collection plan: 1 that you cannot open." in message
    assert "Administrator" not in message


async def test_plan_linked_to_an_alert_rule_is_refused_until_the_rule_changes(
    client: AsyncClient, user: User
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    plan = await _post(client, token, "/api/direction/plans", PLAN)
    rule = await _post(client, token, "/api/warning/indicators", {**RULE, "plan_id": plan["id"]})
    refused = await client.delete(f"/api/direction/plans/{plan['id']}", headers=bearer(token))
    assert refused.status_code == 409, refused.text
    assert refused.json()["error"]["message"] == (
        "This plan is used by 1 alert rule: Kharkiv strikes. Remove the plan from those alert "
        "rules or delete them, then delete this plan."
    )
    edit = {key: rule[key] for key in (*RULE, "bbox", "enabled", "team_id")}
    unlinked = await client.put(
        f"/api/warning/indicators/{rule['id']}",
        json=edit | {"plan_id": None, "expected_updated_at": rule["updated_at"]},
        headers=bearer(token),
    )
    assert unlinked.status_code == 200, unlinked.text
    deleted = await client.delete(f"/api/direction/plans/{plan['id']}", headers=bearer(token))
    assert deleted.status_code == 204


def test_linked_names_limit_and_plural_wording() -> None:
    names = tuple(f"Rule {index}" for index in range(5))
    assert linked_names(LinkedRecords(7, names)) == ", ".join(names) + " and 2 more"
    assert linked_names(LinkedRecords(2, ("Alpha", "Beta"))) == "Alpha, Beta"
    refuse_plan_in_use(LinkedRecords(0))
    with pytest.raises(Conflict, match="used by 3 alert rules: Alpha and 2 more"):
        refuse_plan_in_use(LinkedRecords(3, ("Alpha",)))

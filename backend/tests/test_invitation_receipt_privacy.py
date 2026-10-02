"""Full sender and recipient flows keep hidden and unknown submissions indistinguishable."""

from dataclasses import replace
from datetime import timedelta

import pytest
from httpx import AsyncClient

from ase.application.teams import invitation_sender
from ase.container import Container
from ase.domain.users import User
from helpers import USER_PASSWORD, FakeClock, bearer, create_user, login_token
from test_directory_handle_invitations import _handle, _team_with_manager


async def test_modern_delivery_id_cannot_bypass_sender_receipt_withdrawal(
    client: AsyncClient, container: Container, admin: User
) -> None:
    team, manager = await _team_with_manager(client, container, admin)
    hidden = await create_user(
        container, email="modern-private@example.com", password=USER_PASSWORD
    )
    await _handle(client, hidden, "modern_private", discoverable=False)
    recipient = bearer(await login_token(client, hidden.email, USER_PASSWORD))
    path = f"/api/teams/{team}/invitations"
    assert (
        await client.post(
            path + "/by-username", headers=manager, json={"username": "modern_private"}
        )
    ).status_code == 202
    delivery = (await client.get("/api/me/team-invitations", headers=recipient)).json()["items"][0]
    before = (await client.get(path, headers=manager)).json()
    assert before["items"][0]["id"] != delivery["id"]
    assert (await client.delete(path + "/" + delivery["id"], headers=manager)).status_code == 204
    assert (await client.get(path, headers=manager)).json() == before
    accepted = await client.post(
        f"/api/me/team-invitations/{delivery['id']}/accept", headers=recipient, json={}
    )
    assert accepted.status_code == 200


@pytest.mark.parametrize("transition", ["decline", "expire", "withdraw", "accept"])
async def test_sender_receipt_flow_preserves_privacy_until_consent(
    client: AsyncClient, container: Container, admin: User, clock: FakeClock, transition: str
) -> None:
    team, manager = await _team_with_manager(client, container, admin)
    hidden = await create_user(
        container, email="private-recipient@example.com", password=USER_PASSWORD
    )
    await _handle(client, hidden, "private_recipient", discoverable=False)
    recipient_headers = bearer(await login_token(client, hidden.email, USER_PASSWORD))
    sender_path = f"/api/teams/{team}/invitations"
    for name in ("private_recipient", "unregistered_recipient"):
        assert (
            await client.post(
                sender_path + "/by-username", headers=manager, json={"username": name}
            )
        ).status_code == 202
    before = (await client.get(sender_path, headers=manager)).json()
    assert before["total"] == 2
    comparable = [
        {key: value for key, value in item.items() if key != "id"} for item in before["items"]
    ]
    assert comparable[0] == comparable[1]
    assert comparable[0]["recipient_id"] is None
    delivery = (await client.get("/api/me/team-invitations", headers=recipient_headers)).json()[
        "items"
    ][0]
    if transition in {"decline", "accept"}:
        response = await client.post(
            f"/api/me/team-invitations/{delivery['id']}/{transition}",
            headers=recipient_headers,
            json={"expected_revision": 1},
        )
        assert response.status_code == 200, response.text
    # Later identity changes must not affect pending, declined, expired or accepted receipts.
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.users.get_by_id(hidden.id)
        profile = await repos.directory_profiles.get(hidden.id)
        assert current and profile
        await repos.users.save(replace(current, display_name="Changed private name"))
        await repos.directory_profiles.save(replace(profile, username="changed_private_handle"))
        await session.commit()
    if transition == "expire":
        clock.advance(timedelta(days=8))
        manager = bearer(await login_token(client, "handles@example.com", USER_PASSWORD))
    if transition == "withdraw":
        for item in before["items"]:
            response = await client.delete(
                sender_path + "/" + item["id"], headers=manager, params={"expected_revision": 1}
            )
            assert response.status_code == 204
    if transition == "decline":
        after = (await client.get(sender_path, headers=manager)).json()
        assert after == before
        # The recipient revision changed, but both sender withdrawals still accept revision one.
        for item in before["items"]:
            assert (
                await client.delete(
                    sender_path + "/" + item["id"], headers=manager, params={"expected_revision": 1}
                )
            ).status_code == 204
    elif transition == "accept":
        accepted = (
            await client.get(sender_path, headers=manager, params={"status": "accepted"})
        ).json()
        assert accepted["total"] == 1
        assert accepted["items"][0]["recipient_id"] == str(hidden.id)
        assert accepted["items"][0]["recipient_username"] == "private_recipient"
        assert accepted["items"][0]["recipient_display_name"] == hidden.display_name
    else:
        status = "expired" if transition == "expire" else "withdrawn"
        after = (
            await client.get(sender_path, headers=manager, params={"status": status, "limit": 1})
        ).json()
        assert after["total"] == 2 and len(after["items"]) == 1 and after["next_offset"] == 1
        assert after["items"][0]["recipient_id"] is None
        assert after["items"][0]["recipient_display_name"] is None
        assert after["items"][0]["recipient_username"] is None
    declined = (
        await client.get(sender_path, headers=manager, params={"status": "declined"})
    ).json()
    assert declined["total"] == 0


async def test_private_decline_does_not_free_capacity_for_sibling_uuid_submission(
    client: AsyncClient, container: Container, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(invitation_sender, "MAX_PENDING_INVITATIONS", 2)
    team, manager = await _team_with_manager(client, container, admin)
    hidden = await create_user(
        container, email="capacity-hidden@example.com", password=USER_PASSWORD
    )
    visible = await create_user(
        container, email="capacity-visible@example.com", password=USER_PASSWORD
    )
    await _handle(client, hidden, "capacity_hidden", discoverable=False)
    await _handle(client, visible, "capacity_visible", discoverable=True)
    path = f"/api/teams/{team}/invitations"
    for name in ("capacity_hidden", "capacity_unknown"):
        assert (
            await client.post(path + "/by-username", headers=manager, json={"username": name})
        ).status_code == 202
    recipient = bearer(await login_token(client, hidden.email, USER_PASSWORD))
    delivery = (await client.get("/api/me/team-invitations", headers=recipient)).json()["items"][0]
    assert (
        await client.post(
            f"/api/me/team-invitations/{delivery['id']}/decline", headers=recipient, json={}
        )
    ).status_code == 200
    rejected = await client.post(path, headers=manager, json={"recipient_id": str(visible.id)})
    assert rejected.status_code == 422 and "limit" in rejected.text
    receipts = (await client.get(path, headers=manager)).json()
    assert receipts["total"] == 2
    receipt = receipts["items"][0]
    assert (
        await client.delete(
            path + "/" + receipt["id"], headers=manager, params={"expected_revision": 2}
        )
    ).status_code == 409
    assert (
        await client.delete(
            path + "/" + receipt["id"], headers=manager, params={"expected_revision": 1}
        )
    ).status_code == 204
    assert (
        await client.post(path, headers=manager, json={"recipient_id": str(visible.id)})
    ).status_code == 201

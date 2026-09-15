"""Team board permissions, replies, moderation and revision safety."""

from datetime import timedelta

from httpx import AsyncClient

from ase.container import Container
from ase.domain.audit import AuditAction
from board_helpers import board_desk, post
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def test_team_board_lifecycle_and_membership_boundary(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    payload = await post(client, desk, desk.user, "Handover: review the satellite imagery.")
    assert payload["author_name"] == "User"
    assert payload["edited_at"] is None and payload["removal"] is None
    reply = await post(client, desk, desk.user, "I will take that review.", parent_id=payload["id"])

    listed = await client.get(desk.posts(), headers=desk.user)
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [payload["id"]]
    assert [item["id"] for item in body["replies"]] == [reply["id"]]

    container.clock.advance(timedelta(minutes=1))  # type: ignore[attr-defined]
    edited = await client.patch(
        desk.posts(f"/{payload['id']}"),
        json={"text": "Updated handover.", "expected_revision": payload["revision"]},
        headers=desk.user,
    )
    assert edited.status_code == 200
    assert edited.json()["text"] == "Updated handover."
    assert edited.json()["edited_at"] is not None
    assert edited.json()["created_at"] == payload["created_at"]

    pinned = await client.post(
        desk.posts(f"/{payload['id']}/pin"),
        json={
            "pinned": True,
            "expected_revision": edited.json()["revision"],
            "reason": "Current handover",
        },
        headers=desk.admin,
    )
    assert pinned.status_code == 200 and pinned.json()["is_pinned"] is True
    assert pinned.json()["edited_at"] == edited.json()["edited_at"]

    stale = await client.patch(
        desk.posts(f"/{payload['id']}"),
        json={"text": "Stale edit.", "expected_revision": 1},
        headers=desk.user,
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "conflict"

    removed = await client.delete(
        desk.posts(f"/{payload['id']}?expected_revision={pinned.json()['revision']}"),
        headers=desk.user,
    )
    assert removed.status_code == 204
    after = (await client.get(desk.posts(), headers=desk.user)).json()["items"][0]
    assert after["text"] == "[Removed by author]" and after["removal"] == "author"
    assert after["is_pinned"] is False


async def test_team_board_requires_joined_member(
    client: AsyncClient, admin: object, user: object
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    created = await client.post(
        "/api/teams", json={"name": "Private board"}, headers=bearer(admin_token)
    )
    team_id = created.json()["id"]
    response = await client.get(f"/api/teams/{team_id}/board/posts", headers=bearer(user_token))
    assert response.status_code == 404
    read = await client.post(
        f"/api/teams/{team_id}/board/read",
        json={"last_seen_post_id": team_id},
        headers=bearer(user_token),
    )
    assert read.status_code == 404


async def test_only_the_author_can_edit_even_for_managers_and_admins(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    by_admin = await post(client, desk, desk.admin, "Administrator guidance.")
    by_user = await post(client, desk, desk.user, "Member note.")
    for target, headers in ((by_admin, desk.manager), (by_user, desk.manager)):
        response = await client.patch(
            desk.posts(f"/{target['id']}"),
            json={"text": "Rewritten.", "expected_revision": target["revision"]},
            headers=headers,
        )
        assert response.status_code == 403
    response = await client.patch(
        desk.posts(f"/{by_user['id']}"),
        json={"text": "Rewritten by admin.", "expected_revision": by_user["revision"]},
        headers=desk.admin,
    )
    assert response.status_code == 403
    items = (await client.get(desk.posts(), headers=desk.user)).json()["items"]
    assert {item["text"] for item in items} == {"Administrator guidance.", "Member note."}


async def test_moderator_removal_requires_reason_and_keeps_it_in_audit_only(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    by_admin = await post(client, desk, desk.admin, "Administrator guidance.")
    by_user = await post(client, desk, desk.user, "Member note.")

    # Members cannot moderate other people's posts at all.
    refused = await client.post(
        desk.posts(f"/{by_admin['id']}/remove"),
        json={"expected_revision": 1, "reason": "I disagree"},
        headers=desk.user,
    )
    assert refused.status_code == 403
    # A reason is required, and the URL-based author delete cannot moderate.
    no_reason = await client.post(
        desk.posts(f"/{by_user['id']}/remove"), json={"expected_revision": 1}, headers=desk.manager
    )
    assert no_reason.status_code == 422
    via_delete = await client.delete(
        desk.posts(f"/{by_user['id']}?expected_revision=1"), headers=desk.manager
    )
    assert via_delete.status_code == 422

    # A Manager may hide an Administrator's post, but not rewrite it.
    removed = await client.post(
        desk.posts(f"/{by_admin['id']}/remove"),
        json={"expected_revision": 1, "reason": "Contains a stale access code"},
        headers=desk.manager,
    )
    assert removed.status_code == 200, removed.text
    tombstone = removed.json()
    assert tombstone["text"] == "[Removed by a moderator]"
    assert tombstone["removal"] == "moderator"
    assert tombstone["author_id"] == by_admin["author_id"]
    assert "stale access code" not in str(
        (await client.get(desk.posts(), headers=desk.user)).json()
    )

    again = await client.post(
        desk.posts(f"/{by_admin['id']}/remove"),
        json={"expected_revision": tombstone["revision"], "reason": "Duplicate"},
        headers=desk.admin,
    )
    assert again.status_code == 409

    async with container.session_factory() as session:
        entries = await container.repositories(session).audit.list_before(None, 50)
    removal = next(e for e in entries if e.action is AuditAction.TEAM_BOARD_POST_REMOVED)
    assert removal.subject == by_admin["id"]
    assert removal.details["reason"] == "Contains a stale access code"
    assert removal.details["moderation"] is True


async def test_pins_need_moderators_reasons_and_respect_the_cap(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    posts = [await post(client, desk, desk.user, f"Note {index}") for index in range(4)]
    reply = await post(client, desk, desk.user, "Reply", parent_id=posts[0]["id"])

    member_pin = await client.post(
        desk.posts(f"/{posts[0]['id']}/pin"),
        json={"pinned": True, "expected_revision": 1, "reason": "Useful"},
        headers=desk.user,
    )
    assert member_pin.status_code == 403
    missing_reason = await client.post(
        desk.posts(f"/{posts[0]['id']}/pin"),
        json={"pinned": True, "expected_revision": 1},
        headers=desk.manager,
    )
    assert missing_reason.status_code == 422
    reply_pin = await client.post(
        desk.posts(f"/{reply['id']}/pin"),
        json={"pinned": True, "expected_revision": 1, "reason": "Useful"},
        headers=desk.manager,
    )
    assert reply_pin.status_code == 422
    for item in posts[:3]:
        pinned = await client.post(
            desk.posts(f"/{item['id']}/pin"),
            json={"pinned": True, "expected_revision": 1, "reason": "Standing order"},
            headers=desk.manager,
        )
        assert pinned.status_code == 200, pinned.text
    over = await client.post(
        desk.posts(f"/{posts[3]['id']}/pin"),
        json={"pinned": True, "expected_revision": 1, "reason": "Standing order"},
        headers=desk.manager,
    )
    assert over.status_code == 409
    listed = (await client.get(desk.posts(), headers=desk.user)).json()["items"]
    assert [item["is_pinned"] for item in listed] == [True, True, True, False]


async def test_archived_team_board_is_read_only(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    desk = await board_desk(client, container)
    note = await post(client, desk, desk.user, "Before archive.")
    archived = await client.patch(
        f"/api/teams/{desk.team_id}", json={"is_active": False}, headers=desk.admin
    )
    assert archived.status_code == 200, archived.text
    response = await client.post(desk.posts(), json={"text": "After"}, headers=desk.user)
    assert response.status_code == 422
    edit = await client.patch(
        desk.posts(f"/{note['id']}"),
        json={"text": "After", "expected_revision": 1},
        headers=desk.user,
    )
    assert edit.status_code == 422
    assert (await client.get(desk.posts(), headers=desk.user)).status_code == 200

"""Board mentions reach only current active teammates and follow the post's lifecycle."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from board_helpers import post
from mention_helpers import BELL, deactivate, mention_desk, mentions, set_handle


def _names(body: dict[str, Any]) -> list[str]:
    return [item["display_name"] for item in body["notified"]]


async def _edit(
    client: AsyncClient, url: str, headers: dict[str, str], text: str, revision: int
) -> Any:
    return await client.patch(
        url, json={"text": text, "expected_revision": revision}, headers=headers
    )


async def test_mentions_resolve_current_teammates_only_and_reveal_nothing_else(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    md = await mention_desk(client, container)
    desk = md.desk
    created = await post(
        client,
        desk,
        desk.admin,
        "@Analyst and @analyst, check with @desk_lead, @outsider_one and @nobody_here.",
    )
    assert _names(created) == ["Lead", "User"]
    # Unknown and outside handles are simply not notified; the response says nothing else.
    assert set(created) >= {"id", "text", "notified"}
    analyst = await mentions(client, desk.user)
    assert analyst["unread"] == 1 and analyst["muted"] is False
    notice = analyst["items"][0]
    assert notice["post_id"] == created["id"] == notice["thread_id"]
    assert notice["team_name"] == "Board desk" and notice["author_name"] == "Admin"
    assert notice["snippet"].startswith("@Analyst and @analyst, check with")
    assert (await mentions(client, md.outsider))["unread"] == 0
    assert (await mentions(client, desk.admin))["unread"] == 0

    reply = await post(
        client, desk, desk.user, "@analyst noted, @site_admin", parent_id=created["id"]
    )
    assert _names(reply) == ["Admin"]  # Never yourself.
    admin_items = (await mentions(client, desk.admin))["items"]
    assert admin_items[0]["thread_id"] == created["id"] and admin_items[0]["post_id"] == reply["id"]

    too_many = " ".join(f"@handle_{n}" for n in range(11))
    refused = await client.post(desk.posts(), json={"text": too_many}, headers=desk.admin)
    assert refused.status_code == 422
    assert "up to 10" in refused.json()["error"]["fields"]["text"]

    await deactivate(container, md.peer_id)
    inactive = await post(client, desk, desk.admin, "@peer_one are you there?")
    assert inactive["notified"] == []


async def test_edits_keep_unchanged_mentions_clear_removed_ones_and_never_redirect(
    client: AsyncClient, container: Container, admin: object, user: object
) -> None:
    md = await mention_desk(client, container)
    desk = md.desk
    created = await post(client, desk, desk.admin, "@analyst please look")
    url = desk.posts(f"/{created['id']}")
    opened = await client.post(f"{BELL}/mentions/{created['id']}/open", headers=desk.user)
    assert opened.status_code == 200
    assert opened.json() == {
        "team_id": desk.team_id,
        "post_id": created["id"],
        "thread_id": created["id"],
    }
    assert (await mentions(client, desk.user))["unread"] == 0

    unrelated = await _edit(client, url, desk.admin, "@analyst please look again", 1)
    assert unrelated.status_code == 200 and unrelated.json()["notified"] == []
    assert (await mentions(client, desk.user))["unread"] == 0  # Not re-alerted.

    added = await _edit(client, url, desk.admin, "@analyst and @desk_lead please look", 2)
    assert _names(added.json()) == ["Lead"]
    assert (await mentions(client, desk.manager))["unread"] == 1
    removed = await _edit(client, url, desk.admin, "@analyst please look", 3)
    assert removed.status_code == 200
    assert (await mentions(client, desk.manager))["unread"] == 0

    stale = await _edit(client, url, desk.admin, "@desk_lead stale", 3)
    assert stale.status_code == 409
    assert (await mentions(client, desk.manager))["unread"] == 0  # No phantom notice.

    # The analyst renames; the peer takes the old handle. The stored mention stays put.
    await set_handle(client, desk.user, "analyst_two")
    await set_handle(client, md.peer, "analyst")
    kept = await _edit(client, url, desk.admin, "@analyst please look, thanks", 4)
    assert kept.json()["notified"] == []
    assert (await mentions(client, md.peer))["unread"] == 0
    assert (
        await client.post(f"{BELL}/mentions/{created['id']}/open", headers=desk.user)
    ).status_code == 200


async def test_read_state_removal_membership_and_archive_rechecks(
    client: AsyncClient, container: Container, admin: object, user: User
) -> None:
    md = await mention_desk(client, container)
    desk = md.desk
    first = await post(client, desk, desk.admin, "@analyst @desk_lead handover")
    # One member's reads never clear another's notice.
    await client.post(
        f"/api/teams/{desk.team_id}/board/read",
        json={"last_seen_post_id": first["id"]},
        headers=desk.user,
    )
    read = await client.post(
        f"{BELL}/mentions/read", json={"post_ids": [first["id"]]}, headers=desk.user
    )
    assert read.status_code == 200 and read.json() == {"unread": 0}
    assert (await mentions(client, desk.manager))["unread"] == 1
    # Marking another person's mention read is a harmless no-op.
    assert (
        await client.post(
            f"{BELL}/mentions/read", json={"post_ids": [first["id"]]}, headers=md.outsider
        )
    ).json() == {"unread": 0}

    moderated = await post(client, desk, desk.user, "@desk_lead and @site_admin, a question")
    assert (await mentions(client, desk.manager))["unread"] == 2
    gone = await client.post(
        desk.posts(f"/{moderated['id']}/remove"),
        json={"expected_revision": 1, "reason": "Duplicate question"},
        headers=desk.manager,
    )
    assert gone.status_code == 200
    assert (await mentions(client, desk.manager))["unread"] == 1
    assert (await mentions(client, desk.admin))["unread"] == 0
    assert (
        await client.post(f"{BELL}/mentions/{moderated['id']}/open", headers=desk.admin)
    ).status_code == 404

    own = await post(client, desk, desk.manager, "@analyst a fresh note")
    deleted = await client.delete(
        desk.posts(f"/{own['id']}?expected_revision=1"), headers=desk.manager
    )
    assert deleted.status_code == 204
    second = await post(client, desk, desk.manager, "@analyst for you")
    assert (await mentions(client, desk.user))["unread"] == 1

    left = await client.delete(f"/api/teams/{desk.team_id}/members/{user.id}", headers=desk.admin)
    assert left.status_code == 204
    hidden = await mentions(client, desk.user)
    assert hidden == {"items": [], "unread": 0, "muted": False}
    assert (
        await client.post(f"{BELL}/mentions/{second['id']}/open", headers=desk.user)
    ).status_code == 404
    container.clock.advance(timedelta(minutes=5))  # type: ignore[attr-defined]
    rejoined = await client.put(
        f"/api/teams/{desk.team_id}/members",
        json={"email": "user@example.com", "role": "member"},
        headers=desk.admin,
    )
    assert rejoined.status_code == 200
    # Mentions from before the current membership stay hidden after rejoining.
    assert (await mentions(client, desk.user))["unread"] == 0

    archived = await client.patch(
        f"/api/teams/{desk.team_id}", json={"is_active": False}, headers=desk.admin
    )
    assert archived.status_code == 200
    assert (await mentions(client, desk.manager))["unread"] == 0
    assert (
        await client.post(f"{BELL}/mentions/{first['id']}/open", headers=desk.manager)
    ).status_code == 404

    muted = await client.put(
        f"{BELL}/preferences", json={"muted_kinds": ["mentions"]}, headers=desk.manager
    )
    assert muted.status_code == 200
    assert (await mentions(client, desk.manager)) == {"items": [], "unread": 0, "muted": True}

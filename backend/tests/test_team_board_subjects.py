"""Board posts may name one same-team report version, saved area or drawing collection."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from httpx import AsyncClient

from ase.container import Container
from ase.domain.users import User
from board_helpers import BoardDesk, board_desk, post
from board_subject_helpers import (
    move_report,
    report_subject,
    seed_area,
    seed_document,
    seed_report,
)


async def _other_team(client: AsyncClient, desk: BoardDesk, *, with_user: bool) -> str:
    created = await client.post("/api/teams", json={"name": "Other desk"}, headers=desk.admin)
    assert created.status_code == 201, created.text
    team_id: str = created.json()["id"]
    if with_user:
        added = await client.put(
            f"/api/teams/{team_id}/members",
            json={"email": "user@example.com", "role": "member"},
            headers=desk.admin,
        )
        assert added.status_code == 200, added.text
    return team_id


async def _create(
    client: AsyncClient, desk: BoardDesk, headers: dict[str, str], subject: dict[str, Any]
) -> Any:
    return await client.post(
        desk.posts(), json={"text": "Discuss this.", "subject": subject}, headers=headers
    )


async def test_team_report_version_subject_is_shown_as_a_title_card(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    report_id = await seed_report(container, user.id, desk.team_id, "Port activity review")
    created = await post(
        client,
        desk,
        desk.user,
        "Is the port judgement still right?",
        subject=report_subject(report_id),
    )
    assert created["subject"] == {
        "kind": "report_version",
        "id": str(report_id),
        "version": 1,
        "available": True,
        "title": "Port activity review",
    }
    listed = (await client.get(desk.posts(), headers=desk.manager)).json()
    assert listed["items"][0]["subject"]["title"] == "Port activity review"

    plain = await post(client, desk, desk.user, "No subject here.")
    assert plain["subject"] is None
    reply = await client.post(
        desk.posts(),
        json={"text": "Reply", "parent_id": created["id"], "subject": report_subject(report_id)},
        headers=desk.user,
    )
    assert reply.status_code == 422
    missing_version = await _create(client, desk, desk.user, report_subject(report_id, 2))
    assert missing_version.status_code == 422
    no_version = await _create(
        client, desk, desk.user, {"kind": "report_version", "id": str(report_id)}
    )
    assert no_version.status_code == 422


async def test_saved_area_and_drawing_collection_subjects(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    area_id = await seed_area(container, admin.id, desk.team_id, "Northern approaches")
    drawings_id = await seed_document(container, user.id, desk.team_id, "Patrol sketches")
    area = await post(
        client, desk, desk.user, "Area", subject={"kind": "saved_area", "id": str(area_id)}
    )
    drawings = await post(
        client,
        desk,
        desk.manager,
        "Drawings",
        subject={"kind": "drawing_collection", "id": str(drawings_id)},
    )
    assert area["subject"]["title"] == "Northern approaches"
    assert drawings["subject"]["title"] == "Patrol sketches"
    radio_id = await seed_document(container, user.id, desk.team_id, "Radio plan", kind="radio")
    radio = await _create(
        client, desk, desk.user, {"kind": "drawing_collection", "id": str(radio_id)}
    )
    assert radio.status_code == 422
    versioned_area = await _create(
        client, desk, desk.user, {"kind": "saved_area", "id": str(area_id), "version": 1}
    )
    assert versioned_area.status_code == 422


async def test_cross_team_and_personal_subjects_are_rejected(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    shared_other = await _other_team(client, desk, with_user=True)
    personal = await seed_report(container, user.id, None, "My private notes")
    other_report = await seed_report(container, user.id, shared_other, "Other team report")
    other_area = await seed_area(container, user.id, shared_other)
    personal_drawings = await seed_document(container, user.id, None)
    rejected = [
        (desk.user, report_subject(personal)),
        (desk.user, report_subject(other_report)),
        (desk.admin, report_subject(other_report)),
        (desk.admin, report_subject(personal)),
        (desk.user, {"kind": "saved_area", "id": str(other_area)}),
        (desk.user, {"kind": "drawing_collection", "id": str(personal_drawings)}),
    ]
    for headers, subject in rejected:
        response = await _create(client, desk, headers, subject)
        assert response.status_code == 422, (subject, response.text)
        assert "My private notes" not in response.text

    # A subject the caller cannot read is refused without confirming that it exists.
    private_other = await _other_team(client, desk, with_user=False)
    hidden = await seed_report(container, admin.id, private_other, "Hidden title")
    for subject_id in (hidden, desk.team_id):
        response = await _create(client, desk, desk.user, report_subject(subject_id))  # type: ignore[arg-type]
        assert response.status_code == 422
        assert "Hidden title" not in response.text
        assert response.json()["error"]["message"] == "The linked item is not available."
    assert (await client.get(desk.posts(), headers=desk.user)).json()["total"] == 0


async def test_archived_team_cannot_start_a_subject_thread(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    report_id = await seed_report(container, user.id, desk.team_id)
    thread = await post(
        client, desk, desk.user, "Before archive", subject=report_subject(report_id)
    )
    archived = await client.patch(
        f"/api/teams/{desk.team_id}", json={"is_active": False}, headers=desk.admin
    )
    assert archived.status_code == 200, archived.text
    for headers in (desk.user, desk.admin):
        response = await _create(client, desk, headers, report_subject(report_id))
        assert response.status_code == 422
    listed = (await client.get(desk.posts(), headers=desk.user)).json()
    assert listed["items"][0]["id"] == thread["id"]
    assert listed["items"][0]["subject"]["available"] is True


async def test_lost_subject_access_renders_unavailable_without_its_title(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    other = await _other_team(client, desk, with_user=False)
    moved = await seed_report(container, user.id, desk.team_id, "Moved assessment")
    deleted = await seed_report(container, user.id, desk.team_id, "Deleted assessment")
    await post(client, desk, desk.user, "About the moved one", subject=report_subject(moved))
    await post(client, desk, desk.user, "About the deleted one", subject=report_subject(deleted))
    await move_report(container, moved, other)
    async with container.session_factory() as session:
        await container.repositories(session).reports.delete(deleted)
        await session.commit()
    for headers in (desk.user, desk.admin):
        response = await client.get(desk.posts(), headers=headers)
        assert response.status_code == 200
        subjects = [item["subject"] for item in response.json()["items"]]
        assert (
            subjects
            == [
                {
                    "kind": "report_version",
                    "id": None,
                    "version": 1,
                    "available": False,
                    "title": None,
                }
            ]
            * 2
        )
        assert "Moved assessment" not in response.text
        assert "Deleted assessment" not in response.text
        assert str(moved) not in response.text

    # Moving it to a personal scope also hides it, even from its own author.
    await move_report(container, moved, None)
    listed = (await client.get(desk.posts(), headers=desk.user)).text
    assert "Moved assessment" not in listed


async def test_moderation_tombstones_and_revisions_are_unchanged_by_subjects(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    report_id = await seed_report(container, user.id, desk.team_id, "Linked report")
    thread = await post(client, desk, desk.user, "Original", subject=report_subject(report_id))
    stale = await client.patch(
        desk.posts(f"/{thread['id']}"),
        json={"text": "Stale", "expected_revision": 2},
        headers=desk.user,
    )
    assert stale.status_code == 409
    relink = await client.patch(
        desk.posts(f"/{thread['id']}"),
        json={"text": "Edited", "expected_revision": 1, "subject": None},
        headers=desk.user,
    )
    assert relink.status_code == 422
    edited = await client.patch(
        desk.posts(f"/{thread['id']}"),
        json={"text": "Edited", "expected_revision": 1},
        headers=desk.user,
    )
    assert edited.status_code == 200
    assert edited.json()["subject"]["title"] == "Linked report"
    pinned = await client.post(
        desk.posts(f"/{thread['id']}/pin"),
        json={"pinned": True, "expected_revision": 2, "reason": "Current review"},
        headers=desk.manager,
    )
    assert pinned.status_code == 200 and pinned.json()["subject"]["available"] is True
    removed = await client.post(
        desk.posts(f"/{thread['id']}/remove"),
        json={"expected_revision": 3, "reason": "Off topic thread"},
        headers=desk.manager,
    )
    assert removed.status_code == 200
    tombstone = removed.json()
    assert tombstone["text"] == "[Removed by a moderator]" and tombstone["subject"] is None
    listed = (await client.get(desk.posts(), headers=desk.user)).json()["items"][0]
    assert listed["subject"] is None and "Linked report" not in str(listed)


async def test_report_team_discussion_counts_live_threads_for_readers(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    desk = await board_desk(client, container)
    report_id = await seed_report(container, user.id, desk.team_id)
    path = f"/api/reports/{report_id}/team-discussion"
    empty = await client.get(path, headers=desk.user)
    assert empty.status_code == 200, empty.text
    assert empty.json() == {
        "team_id": desk.team_id,
        "count": 0,
        "latest_post_id": None,
        "can_post": True,
    }
    first = await post(client, desk, desk.user, "v1", subject=report_subject(report_id))
    await post(client, desk, desk.user, "Reply", parent_id=first["id"])
    container.clock.advance(timedelta(minutes=1))  # type: ignore[attr-defined]
    second = await post(client, desk, desk.manager, "Again", subject=report_subject(report_id))
    container.clock.advance(timedelta(minutes=1))  # type: ignore[attr-defined]
    gone = await post(client, desk, desk.user, "Gone", subject=report_subject(report_id))
    removed = await client.delete(
        desk.posts(f"/{gone['id']}?expected_revision=1"), headers=desk.user
    )
    assert removed.status_code == 204
    counted = (await client.get(path, headers=desk.manager)).json()
    assert counted["count"] == 2 and counted["latest_post_id"] == second["id"]
    assert response_headers_no_store(await client.get(path, headers=desk.user))

    personal = await seed_report(container, user.id, None)
    own = (await client.get(f"/api/reports/{personal}/team-discussion", headers=desk.user)).json()
    assert own == {"team_id": None, "count": 0, "latest_post_id": None, "can_post": False}
    other = await _other_team(client, desk, with_user=False)
    hidden = await seed_report(container, admin.id, other)
    refused = await client.get(f"/api/reports/{hidden}/team-discussion", headers=desk.user)
    missing = await client.get(f"/api/reports/{desk.team_id}/team-discussion", headers=desk.user)
    # Only per-request correlation differs; the complete stable answer preserves privacy.
    assert refused.status_code == missing.status_code == 404
    refused_body, missing_body = refused.json(), missing.json()
    for response, body in ((refused, refused_body), (missing, missing_body)):
        identifier = body["error"].pop("request_id")
        assert re.fullmatch(r"[a-f0-9]{32}", identifier)
        assert identifier == response.headers["X-Request-ID"]
    assert refused.headers["X-Request-ID"] != missing.headers["X-Request-ID"]
    assert (
        refused_body
        == missing_body
        == {"error": {"code": "not_found", "message": "The requested item does not exist."}}
    )
    archived = await client.patch(
        f"/api/teams/{desk.team_id}", json={"is_active": False}, headers=desk.admin
    )
    assert archived.status_code == 200
    read_only = (await client.get(path, headers=desk.user)).json()
    assert read_only["count"] == 2 and read_only["can_post"] is False


def response_headers_no_store(response: Any) -> bool:
    return bool(response.headers.get("cache-control") == "no-store")

"""Avatar upload, removal and display-name-equivalent visibility through the API."""

from __future__ import annotations

import io

from httpx import AsyncClient
from PIL import Image

from ase.container import Container
from ase.domain.directory_avatar import MAX_AVATAR_UPLOAD_BYTES
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_PASSWORD, bearer, create_user, login_token

OCTET = {"Content-Type": "application/octet-stream"}
AVATAR_PATH = "/api/me/directory-profile/avatar"


def _jpeg_with_exif() -> bytes:
    exif = Image.Exif()
    exif[0x013B] = "Hidden-Artist-Name"
    buffer = io.BytesIO()
    Image.new("RGB", (300, 300), "green").save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


async def _headers(client: AsyncClient, user: User) -> dict[str, str]:
    return bearer(await login_token(client, user.email, USER_PASSWORD))


async def test_owner_uploads_reads_and_removes_avatar(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="avatar@example.com", password=USER_PASSWORD)
    headers = await _headers(client, owner)

    uploaded = await client.put(
        AVATAR_PATH, headers={**headers, **OCTET}, content=_jpeg_with_exif()
    )
    assert uploaded.status_code == 200, uploaded.text
    avatar_url = uploaded.json()["avatar_url"]
    assert avatar_url.startswith(f"/api/directory/users/{owner.id}/avatar?v=")
    assert uploaded.headers["cache-control"] == "no-store"

    served = await client.get(avatar_url, headers=headers)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/webp"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert served.headers["cache-control"] == "private, max-age=300"
    assert served.headers["etag"].startswith('"')
    assert b"Hidden-Artist-Name" not in served.content
    with Image.open(io.BytesIO(served.content)) as decoded:
        assert decoded.size == (256, 256)
        assert len(decoded.getexif()) == 0

    removed = await client.delete(AVATAR_PATH, headers=headers)
    assert removed.status_code == 200
    assert removed.json()["avatar_url"] is None
    assert (await client.get(avatar_url, headers=headers)).status_code == 404
    again = await client.delete(AVATAR_PATH, headers=headers)
    assert again.status_code == 200
    assert again.json()["revision"] == removed.json()["revision"]


async def test_avatar_visibility_matches_display_name_visibility(
    client: AsyncClient, container: Container, admin: User
) -> None:
    owner = await create_user(container, email="private@example.com", password=USER_PASSWORD)
    stranger = await create_user(container, email="stranger@example.com", password=USER_PASSWORD)
    teammate = await create_user(container, email="teammate@example.com", password=USER_PASSWORD)
    owner_headers = await _headers(client, owner)
    stranger_headers = await _headers(client, stranger)
    teammate_headers = await _headers(client, teammate)
    admin_headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    uploaded = await client.put(
        AVATAR_PATH, headers={**owner_headers, **OCTET}, content=_jpeg_with_exif()
    )
    url = uploaded.json()["avatar_url"]

    # Not discoverable and no shared team: indistinguishable from a missing avatar.
    assert (await client.get(url, headers=stranger_headers)).status_code == 404
    assert (await client.get(url, headers=teammate_headers)).status_code == 404
    assert (await client.get(url)).status_code == 401
    assert (await client.get(url, headers=admin_headers)).status_code == 200

    team = await client.post("/api/teams", json={"name": "Avatar desk"}, headers=admin_headers)
    assert team.status_code == 201, team.text
    for member in (owner, teammate):
        added = await client.put(
            f"/api/teams/{team.json()['id']}/members",
            headers=admin_headers,
            json={"email": member.email, "role": "member"},
        )
        assert added.status_code in {200, 201, 204}, added.text
    assert (await client.get(url, headers=teammate_headers)).status_code == 200
    assert (await client.get(url, headers=stranger_headers)).status_code == 404

    published = await client.patch(
        "/api/me/directory-profile",
        headers=owner_headers,
        json={"username": "avatar_owner", "is_discoverable": True},
    )
    assert published.status_code == 200, published.text
    assert (await client.get(url, headers=stranger_headers)).status_code == 200
    found = await client.get(
        "/api/directory/users", headers=stranger_headers, params={"q": "avatar_owner"}
    )
    assert found.json()["items"][0]["avatar_url"] == published.json()["avatar_url"]


async def test_avatar_upload_rejects_oversize_garbage_and_wrong_encoding(
    client: AsyncClient, container: Container
) -> None:
    owner = await create_user(container, email="reject@example.com", password=USER_PASSWORD)
    headers = await _headers(client, owner)

    oversize = await client.put(
        AVATAR_PATH, headers={**headers, **OCTET}, content=b"\xff" * (MAX_AVATAR_UPLOAD_BYTES + 1)
    )
    assert oversize.status_code == 413

    garbage = await client.put(
        AVATAR_PATH, headers={**headers, **OCTET}, content=b"<svg onload=alert(1)>"
    )
    assert garbage.status_code == 422
    assert garbage.json()["error"]["code"] == "invalid_request"

    buffer = io.BytesIO()
    Image.new("L", (5000, 5000), 0).save(buffer, format="PNG", optimize=True)
    huge = await client.put(AVATAR_PATH, headers={**headers, **OCTET}, content=buffer.getvalue())
    assert huge.status_code == 422

    wrong_type = await client.put(
        AVATAR_PATH, headers={**headers, "Content-Type": "image/jpeg"}, content=_jpeg_with_exif()
    )
    assert wrong_type.status_code == 422

    profile = await client.get("/api/me/directory-profile", headers=headers)
    assert profile.json()["avatar_url"] is None
    assert profile.json()["revision"] == 1


async def test_avatar_routes_require_authentication(client: AsyncClient) -> None:
    assert (await client.put(AVATAR_PATH, headers=OCTET, content=b"x")).status_code == 401
    assert (await client.delete(AVATAR_PATH)).status_code == 401

"""Handle changes cannot reveal hidden accounts or be used as an unbounded probe."""

from typing import Any

from httpx import AsyncClient, Response

from ase.application.account.directory_profile import HANDLE_CHANGES_PER_WINDOW
from ase.container import Container
from helpers import USER_PASSWORD, bearer, create_user, login_token

PATH = "/api/me/directory-profile"


async def _headers(client: AsyncClient, container: Container, email: str) -> dict[str, str]:
    account = await create_user(container, email=email, password=USER_PASSWORD)
    return bearer(await login_token(client, account.email, USER_PASSWORD))


def _without_request_id(response: Response) -> dict[str, Any]:
    error = dict(response.json()["error"])
    error.pop("request_id", None)
    return error


async def test_hidden_and_discoverable_handles_answer_identically(
    client: AsyncClient, container: Container
) -> None:
    hidden = await _headers(client, container, "hidden@example.com")
    visible = await _headers(client, container, "visible@example.com")
    prober = await _headers(client, container, "prober@example.com")
    claimed = await client.patch(PATH, headers=hidden, json={"username": "quiet_one"})
    assert claimed.status_code == 200 and claimed.json()["is_discoverable"] is False
    listed = await client.patch(
        PATH, headers=visible, json={"username": "loud_one", "is_discoverable": True}
    )
    assert listed.status_code == 200

    answers = [
        await client.patch(PATH, headers=prober, json={"username": handle})
        for handle in ("quiet_one", "LOUD_ONE")
    ]

    assert [answer.status_code for answer in answers] == [409, 409]
    first, second = (_without_request_id(answer) for answer in answers)
    assert first == second
    assert first["code"] == "username_unavailable"
    assert "quiet_one" not in str(first) and "hidden" not in first["message"].lower()
    # A refused claim leaves the prober's own profile untouched.
    mine = await client.get(PATH, headers=prober)
    assert mine.json()["username"] is None


async def test_handle_changes_share_a_per_account_budget(
    client: AsyncClient, container: Container
) -> None:
    prober = await _headers(client, container, "budget@example.com")
    other = await _headers(client, container, "unaffected@example.com")
    held = await client.patch(PATH, headers=other, json={"username": "held_name"})
    assert held.status_code == 200

    statuses = []
    for attempt in range(HANDLE_CHANGES_PER_WINDOW):
        # Refused probes and successful changes draw on the same allowance.
        handle = "held_name" if attempt % 2 else f"probe_{attempt}"
        statuses.append(
            (await client.patch(PATH, headers=prober, json={"username": handle})).status_code
        )
    assert set(statuses) == {200, 409}

    limited = await client.patch(PATH, headers=prober, json={"username": "held_name"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
    assert limited.headers.get("retry-after")

    # Other profile fields and re-saving the current handle are not handle probes.
    current = (await client.get(PATH, headers=prober)).json()["username"]
    unchanged = await client.patch(
        PATH, headers=prober, json={"username": current, "biography": "Still editable."}
    )
    assert unchanged.status_code == 200, unchanged.text
    # Each account has its own allowance.
    assert (
        await client.patch(PATH, headers=other, json={"username": "fresh_name"})
    ).status_code == 200

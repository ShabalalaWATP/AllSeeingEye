"""Original refresh-family revocation and expiry block private declaration release."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.research.inputs import ImportResearchInput
from helpers import CSRF_COOKIE, USER_PASSWORD, bearer, login_token
from research_input_helpers import extracted


@pytest.mark.parametrize("transition", ["logout", "expiry", "input_expiry"])
async def test_target_release_rechecks_original_family_after_initial_auth(
    client,
    container,
    user,
    clock,
    monkeypatch,
    transition,
):
    token = await login_token(client, user.email, USER_PASSWORD)
    reservation = container.research_inputs.reserve(user, "notes.txt")
    stored = container.research_inputs.put(
        reservation, extracted(text=b"Private original passage.")
    )
    original = ImportResearchInput.declaration_targets
    changed = False

    async def interrupted(self, actor, input_id, **kwargs):
        nonlocal changed
        if not changed:
            changed = True
            if transition == "logout":
                response = await client.post(
                    "/api/auth/logout",
                    headers={
                        "X-CSRF-Token": client.cookies[CSRF_COOKIE],
                    },
                )
                assert response.status_code == 204
            elif transition == "expiry":
                clock.advance(
                    container.issuer.verify(token).expires_at - clock.now() + timedelta(seconds=1)
                )
            else:
                # Keep this family/token alive while only the input expires.
                container.research_inputs._reservations[input_id] = replace(
                    reservation,
                    expires_at=clock.now(),
                )
        return await original(self, actor, input_id, **kwargs)

    monkeypatch.setattr(ImportResearchInput, "declaration_targets", interrupted)
    result = await client.get(
        f"/api/research/inputs/{stored.receipt.id}/declaration-targets", headers=bearer(token)
    )
    assert result.status_code == (404 if transition == "input_expiry" else 401)
    assert "Private original passage" not in result.text


async def test_derived_receipt_logout_after_retention_releases_no_preview(
    client, container, user, monkeypatch
):
    token = await login_token(client, user.email, USER_PASSWORD)
    reservation = container.research_inputs.reserve(user, "notes.txt")
    stored = container.research_inputs.put(reservation, extracted(text=b"Private date 2025-03-21."))
    event = stored.events[0]
    original = ImportResearchInput.declare

    async def interrupted(self, *args, **kwargs):
        receipt = await original(self, *args, **kwargs)
        response = await client.post(
            "/api/auth/logout",
            headers={
                "X-CSRF-Token": client.cookies[CSRF_COOKIE],
            },
        )
        assert response.status_code == 204
        return receipt

    monkeypatch.setattr(ImportResearchInput, "declare", interrupted)
    response = await client.post(
        f"/api/research/inputs/{stored.receipt.id}/declarations",
        headers=bearer(token),
        json={
            "sha256": stored.receipt.sha256,
            "declarations": [
                {
                    "event_id": event.id,
                    "content_hash": event.content_hash,
                    "source_dates": [
                        {
                            "field": "summary",
                            "raw_text": "2025-03-21",
                            "role": "publication",
                            "calendar": "gregorian",
                        }
                    ],
                }
            ],
        },
    )
    assert response.status_code == 401
    assert "Private date" not in response.text

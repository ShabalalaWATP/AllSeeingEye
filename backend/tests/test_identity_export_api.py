"""Identity-only offline downloads use deliberate exact revisions and private responses."""

import json
from uuid import uuid4

import pytest

from helpers import USER_PASSWORD, bearer, login_token
from test_identity_export_selection import prepared
from test_selected_claim_package import files


def selection(revision):
    return {
        "version_number": 1,
        "identity_revisions": [
            {
                "decision_id": str(revision.decision_id),
                "revision_id": str(revision.id),
            }
        ],
    }


async def test_identity_only_download_keeps_original_source_attributes(client, container, user):
    _, report, _, revision = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        f"/api/reports/{report.id}/selected-evidence-package",
        headers=headers,
        json=selection(revision),
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "selected-annotations.zip" in response.headers["content-disposition"]
    exported = files(response.content)
    manifest = json.loads(exported["manifest.json"])
    assert manifest["schema_version"] == "ase-evidence-package-v3"
    assert manifest["selected_identity_revision_ids"] == [str(revision.id)]
    value = json.loads(exported["identity-revisions.json"])["revisions"][0]
    assert value["candidate"]["attributes"]
    assert value["id"] == str(revision.id)


@pytest.mark.parametrize("change", ["empty", "too_many", "unknown", "wrong_root"])
async def test_identity_export_boundary_rejects_bad_selection(client, container, user, change):
    _, report, _, revision = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = selection(revision)
    expected = 422
    if change == "empty":
        payload["identity_revisions"] = []
    elif change == "too_many":
        payload["identity_revisions"] *= 21
    elif change == "unknown":
        payload["identity_revisions"][0]["subject"] = "Forged scope"
    else:
        payload["identity_revisions"][0]["decision_id"] = str(uuid4())
        expected = 404
    response = await client.post(
        f"/api/reports/{report.id}/selected-evidence-package", headers=headers, json=payload
    )
    assert response.status_code == expected, response.text

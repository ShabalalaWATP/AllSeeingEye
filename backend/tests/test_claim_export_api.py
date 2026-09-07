"""Selected-revision download contract and access isolation."""

import io
import json
import zipfile
from dataclasses import replace
from uuid import uuid4

import pytest

from helpers import USER_PASSWORD, bearer, login_token
from test_claim_repository import seed


def selection(revision):
    return {
        "version_number": 1,
        "revisions": [{"claim_id": str(revision.claim_id), "revision_id": str(revision.id)}],
    }


async def test_download_preserves_exact_selected_revision(client, container, user):
    report, _, revision = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        f"/api/reports/{report.id}/claim-evidence-package",
        headers=headers,
        json=selection(revision),
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["selected_revision_ids"] == [str(revision.id)]


async def test_other_persons_claim_export_is_hidden(client, container, user):
    report, _, revision = await seed(container, replace(user, id=uuid4()))
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        f"/api/reports/{report.id}/claim-evidence-package",
        headers=headers,
        json=selection(revision),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("version_number", True),
        ("version_number", 2**40),
        ("revisions", []),
        ("unexpected", "ignored?"),
    ],
)
async def test_export_rejects_invalid_selection_boundary(client, container, user, field, value):
    report, _, revision = await seed(container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    response = await client.post(
        f"/api/reports/{report.id}/claim-evidence-package",
        headers=headers,
        json={**selection(revision), field: value},
    )
    assert response.status_code == 422

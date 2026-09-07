"""HTTP comparison requests cannot supply snapshots or unbounded selections."""

import json
from dataclasses import asdict

import pytest
from pydantic import TypeAdapter

from annotation_comparison_helpers import prepared
from ase.domain.claim_revisions import ClaimRevision
from helpers import USER_PASSWORD, bearer, login_token


async def test_preview_and_exact_manifest_export_are_private_and_replayable(
    client, container, user
):
    _, _, _, revision, request = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = json.loads(json.dumps(asdict(request), default=str))
    preview = await client.post("/api/annotation-comparisons", headers=headers, json=payload)
    assert preview.status_code == 200, preview.text
    result = preview.json()
    assert result["before"]["revisions"][0]["id"] == str(revision.id)
    assert result["annotation_changes"][0]["correspondence"] == "same_root"
    assert preview.headers["cache-control"] == "private, no-store"
    exported = await client.post(
        "/api/annotation-comparisons/export",
        headers=headers,
        json={**payload, "expected_comparison_sha256": result["comparison_sha256"]},
    )
    assert exported.status_code == 200, exported.text
    assert exported.headers["content-type"] == "application/json"
    assert exported.headers["x-content-type-options"] == "nosniff"
    assert exported.json()["comparison_sha256"] == result["comparison_sha256"]
    adapter = TypeAdapter(list[ClaimRevision])
    assert adapter.validate_python(
        exported.json()["before"]["revisions"]
    ) == adapter.validate_python(result["before"]["revisions"])
    assert result["compared_by"] == str(user.id)


@pytest.mark.parametrize(
    "fault",
    [
        "actor",
        "snapshot",
        "version_bool",
        "too_many",
        "cross_kind",
        "duplicate_root",
        "export_no_digest",
    ],
)
async def test_invalid_comparison_requests_do_not_claim_correspondence(
    client, container, user, fault
):
    _, _, _, revision, request = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = json.loads(json.dumps(asdict(request), default=str))
    path, expected = "/api/annotation-comparisons", 422
    if fault == "actor":
        payload["compared_by"] = str(user.id)
    elif fault == "snapshot":
        payload["before"]["evidence"] = []
    elif fault == "version_bool":
        payload["before"]["version_number"] = True
    elif fault == "too_many":
        payload["before"]["revisions"] *= 21
    elif fault == "cross_kind":
        payload["correspondences"] = [
            {
                "kind": "identity",
                "before_revision_id": str(revision.id),
                "after_revision_id": str(revision.id),
                "rationale": "Invent correspondence",
            }
        ]
    elif fault == "duplicate_root":
        payload["before"]["revisions"] *= 2
    else:
        path += "/export"
    response = await client.post(path, headers=headers, json=payload)
    assert response.status_code == expected, response.text

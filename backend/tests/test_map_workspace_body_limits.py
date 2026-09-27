"""The workspace payload allowance covers JSON envelopes but no adjacent routes."""

import pytest

from ase.api.middleware import MAP_WORKSPACE_MAX_BODY_BYTES
from test_map_body_limits import send_body


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/map/workspaces"),
        ("PATCH", "/api/map/workspaces/7d3f2a9c-4b1e-4c8d-9a6f-1e2b3c4d5e6f"),
    ],
)
@pytest.mark.parametrize("declared", [False, True])
async def test_exact_limit_allowed_and_one_byte_over_rejected(method, path, declared):
    limit = MAP_WORKSPACE_MAX_BODY_BYTES
    chunks = [b"x" * 64000, b"y" * (limit - 64000)]
    status, seen = await send_body(path, method, chunks, limit if declared else None)
    assert status == 204 and seen == chunks
    status, seen = await send_body(path, method, [*chunks, b"z"], limit + 1 if declared else None)
    assert status == 413 and seen == []


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/map/workspaces"),
        ("POST", "/api/map/workspaces/extra"),
        ("PATCH", "/api/map/workspaces/not-a-uuid"),
        ("PATCH", "/api/map/workspaces/2c8e6f1a-9d4b-4e3c-8f7a-6b5c4d3e2f1a/extra"),
        ("DELETE", "/api/map/workspaces/9a1b2c3d-4e5f-4a6b-8c7d-0e1f2a3b4c5d"),
    ],
)
async def test_allowance_does_not_widen_nearby_endpoints(method, path):
    status, seen = await send_body(path, method, [b"x" * 65537])
    assert status == 413 and seen == []

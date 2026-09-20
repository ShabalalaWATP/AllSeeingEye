"""The workspace payload allowance covers JSON envelopes but no adjacent routes."""

from uuid import uuid4

import pytest

from ase.api.middleware import MAP_WORKSPACE_MAX_BODY_BYTES
from test_map_body_limits import send_body


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/map/workspaces"),
        ("PATCH", f"/api/map/workspaces/{uuid4()}"),
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
        ("PATCH", f"/api/map/workspaces/{uuid4()}/extra"),
        ("DELETE", f"/api/map/workspaces/{uuid4()}"),
    ],
)
async def test_allowance_does_not_widen_nearby_endpoints(method, path):
    status, seen = await send_body(path, method, [b"x" * 65537])
    assert status == 413 and seen == []

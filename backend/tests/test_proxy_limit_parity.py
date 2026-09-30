"""Keep the production proxy's exact upload routes and outer limits aligned."""

import re
from pathlib import Path

from ase.api.middleware import (
    AVATAR_MAX_BODY_BYTES,
    DEFAULT_MAX_BODY_BYTES,
    MAP_WORKSPACE_MAX_BODY_BYTES,
)


def test_caddy_upload_allowances_match_api_caps() -> None:
    source = (Path(__file__).resolve().parents[2] / "infra" / "Caddyfile").read_text()
    for name, size in (
        ("ordinary", DEFAULT_MAX_BODY_BYTES),
        ("avatar", AVATAR_MAX_BODY_BYTES),
        ("map_workspace", MAP_WORKSPACE_MAX_BODY_BYTES),
    ):
        found = re.search(r"request_body @" + name + r" \{\s*max_size (\d+)\s*\}", source)
        assert found and int(found.group(1)) == size
    assert "method PUT\n\t\tpath /api/me/directory-profile/avatar" in source
    assert "{method} == 'POST' && path('/api/map/workspaces')" in source
    assert "{method} == 'PATCH' && path_regexp('^/api/map/workspaces/" in source
    for maximum in ("8MiB", "12MiB", "7MiB"):
        assert f"max_size {maximum}" in source

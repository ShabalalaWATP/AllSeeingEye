"""Operational startup observability does not load the application for migrations."""

import json
import os
import subprocess
import sys

from structlog.testing import capture_logs

from ase.infrastructure.startup import record_startup_phase


def test_migration_cli_does_not_import_application_wiring(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ase.cli import app; import json, sys; app(['migrate'], standalone_mode=False); "
            "print(json.dumps([k for k in sys.modules if k == 'ase' or k.startswith('ase.')]))",
        ],
        env=os.environ
        | {"ASE_ENV": "test", "ASE_DATABASE_URL": f"sqlite+aiosqlite:///{tmp_path}/migrate.db"},
        check=True,
        capture_output=True,
        text=True,
    )
    modules = json.loads(result.stdout.splitlines()[-1])
    assert "ase.container" not in modules
    assert "ase.app_factory" not in modules
    assert not any(
        name.startswith(("ase.adapters.feeds.", "ase.adapters.llm.")) for name in modules
    )
    assert not {
        "ase.adapters.geo.infrastructure_import",
        "ase.adapters.geo.infrastructure_notes",
        "ase.adapters.geo.sites_import",
    }.intersection(modules)
    assert len(modules) < 200


def test_startup_phase_emits_duration_without_runtime_configuration(monkeypatch):
    monkeypatch.setattr("ase.infrastructure.startup.perf_counter", lambda: 1.125)
    with capture_logs() as rows:
        record_startup_phase("snapshot_restore", 1.0)
    assert rows == [
        {
            "event": "startup.phase",
            "phase": "snapshot_restore",
            "duration_ms": 125.0,
            "log_level": "info",
        }
    ]

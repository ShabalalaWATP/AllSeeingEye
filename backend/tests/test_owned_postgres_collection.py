"""Exercise the real pytest registration and the post-collection admission boundary."""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FILES = (
    "tests/test_rekey_migration_history.py",
    "tests/test_notification_migration_guards_postgres.py",
    "tests/test_notification_migration_postgres.py",
)


def run_pytest(tmp_path, *arguments, plugin=None):
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ASE_", "PG", "COVERAGE", "PYTEST_"))
    }
    if plugin:
        (tmp_path / "admission_probe.py").write_text(plugin, encoding="utf-8")
        environment["PYTHONPATH"] = str(tmp_path)
    return subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(BACKEND / "pyproject.toml"),
            "--no-cov",
            "-q",
            "-o",
            "pythonpath=. tests",
            "-p",
            "owned_postgres",
            *arguments,
        ],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_real_collection_moves_only_the_21_original_cases(tmp_path):
    target = tmp_path / "selected.txt"
    result = run_pytest(
        tmp_path,
        "--collect-only",
        "-m",
        "owned_migration",
        f"--record-nodeids={target}",
        *FILES,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    selected = target.read_text(encoding="utf-8").splitlines()
    assert len(selected) == len(set(selected)) == 21
    assert {name: sum(node.startswith(name + "::") for node in selected) for name in FILES} == {
        FILES[0]: 15,
        FILES[1]: 4,
        FILES[2]: 2,
    }
    assert sum("[postgres" in node for node in selected) == 7
    assert sum("[sqlite" in node for node in selected) == 7


def test_changed_identity_fails_before_any_database_fixture(tmp_path):
    plugin = """
import pytest

@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    config.option.owned_migrations = True
    definition = items[0]._fixtureinfo.name2fixturedefs["owned_migration_service"][0]
    definition.func = lambda request, isolated_postgres_database: None
    assert items[0].get_closest_marker("owned_migration")
"""
    result = run_pytest(
        tmp_path,
        "-p",
        "admission_probe",
        FILES[0] + "::test_rekey_graph_keeps_released_history_and_has_one_head",
        plugin=plugin,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Owned migration identities changed after collection" in result.stdout
    assert "1 error" in result.stdout
    assert "skipped" not in result.stdout


def test_service_lifetime_encloses_async_disposal_and_ends_before_next_case(tmp_path):
    # Synthetic child fixture tests pytest's real finaliser ordering only. It does
    # not replace native migration or admission checks and never contacts a DB.
    plugin = """
import os
import pytest
import owned_postgres

URL = "postgresql+asyncpg://localhost/ase_test_" + "a" * 32 + "_gw0"
events = []

def pytest_collection_modifyitems(config, items):
    config.option.owned_migrations = True
    owned_postgres.admitted = lambda item: True

@pytest.fixture(scope="session")
def isolated_postgres_database():
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ASE_TEST_DATABASE_URL", URL)
        yield URL

@pytest.fixture
async def child():
    assert os.environ[owned_postgres.SERVICE_VARIABLE] == URL
    events.append("child setup")
    try:
        yield
    finally:
        assert os.environ[owned_postgres.SERVICE_VARIABLE] == URL
        events.append("child disposed")

def pytest_sessionfinish():
    print("LIFETIME_EVENTS", events)
    assert owned_postgres.SERVICE_VARIABLE not in os.environ
"""
    tests = tmp_path / "test_lifetime.py"
    tests.write_text(
        """
import asyncio
import os
import pytest
from admission_probe import events
from owned_postgres import SERVICE_VARIABLE

@pytest.mark.owned_migration
async def test_cancelled_child(child):
    raise asyncio.CancelledError("synthetic cancellation")

def test_following_case():
    assert SERVICE_VARIABLE not in os.environ
    events.append("following case")
""",
        encoding="utf-8",
    )
    result = run_pytest(tmp_path, "-p", "admission_probe", str(tests), plugin=plugin)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 failed, 1 passed" in result.stdout
    assert "synthetic cancellation" in result.stdout
    assert "['child setup', 'child disposed', 'following case']" in result.stdout
    assert "INTERNALERROR" not in result.stdout

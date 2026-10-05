"""Explicit process-parallel admission for three audited UUID migration modules.

This permission never replaces fresh databases or the ordinary template guard.
The service URL is made available only while an admitted test owns its fixtures.
"""

import os
import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio.plugin as asyncio_plugin
import xdist.plugin as xdist_plugin
from _pytest import python as pytest_python
from _pytest import tmpdir as pytest_tmpdir
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

import notification_migration_helpers as migration
import postgres_isolation
import postgres_templates

ROOT = Path(__file__).resolve().parent
SERVICE_VARIABLE = "ASE_NOTIFICATION_MIGRATION_POSTGRES_URL"
MARKER = "owned_migration"
_REGISTERED = pytest.StashKey[bool]()
_APPROVED = {
    "test_rekey_migration_history": {
        "test_rekey_graph_keeps_released_history_and_has_one_head",
        "test_fresh_rekey_upgrade_is_complete_unenrolled_and_repeatable",
        "test_populated_main0081_upgrade_preserves_released_features",
        "test_main0081_corrupt_checkpoint_upgrade_is_repairable",
        "test_rekeyed_privacy_barrier_keeps_main_and_receipt_state",
        "test_rekeyed_frozen_ratio_barrier_preserves_main_features",
        "test_rekey_preserves_frozen_origins_and_full_summary_allowance",
    },
    "test_notification_migration_guards_postgres": {
        "test_corrupt_legacy_checkpoint_refuses_without_partial_postgres_ddl",
        "test_frozen_alert_baselines_refuse_downgrade_after_rule_changes",
        "test_feedback_and_privacy_barriers_preserve_schema_and_retained_rows",
    },
    "test_notification_migration_postgres": {
        "test_empty_combined_upgrade_roundtrip_and_model_parity",
        "test_legacy_upgrade_constraints_and_explicit_notification_rollback",
    },
}
_TESTS: dict[Callable, tuple[object, object]] = {}
_HELPERS = {
    name: (value, getattr(value, "__code__", None))
    for name, value in vars(migration).items()
    if getattr(value, "__module__", None) == migration.__name__
}
_METHODS = {
    name: (
        getattr(migration.MigrationDatabase, name),
        getattr(migration.MigrationDatabase, name).__code__,
    )
    for name in ("migrate", "run")
}
_FIXTURES = {
    "migration_database": (migration.migration_database, "function", (), None),
    "isolated_postgres_database": (
        postgres_isolation.isolated_postgres_database,
        "session",
        ("request", "worker_id"),
        None,
    ),
    "template_database": (postgres_templates.template_database, "function", ("request",), None),
    "worker_id": (xdist_plugin.worker_id, "session", ("request",), None),
    "event_loop_policy": (asyncio_plugin.event_loop_policy, "session", (), None),
    "tmp_path": (pytest_tmpdir.tmp_path, "function", ("request", "tmp_path_factory"), None),
    "tmp_path_factory": (pytest_tmpdir.tmp_path_factory, "session", ("request",), None),
}
_FIXTURE_CODES = {
    wrapper: wrapper._get_wrapped_function().__code__ for wrapper, *_rest in _FIXTURES.values()
}
_PARAMETER_FUNCTION = pytest_python.get_direct_param_fixture_func
_PARAMETER_CODE = _PARAMETER_FUNCTION.__code__


def owned_migration_test(function: Callable) -> Callable:
    """Annotate exact reviewed tests without changing their bodies or pytest IDs."""
    module = sys.modules[function.__module__]
    if (
        function.__name__ not in _APPROVED.get(function.__module__, ())
        or Path(function.__code__.co_filename).resolve() != ROOT / f"{function.__module__}.py"
    ):
        raise ValueError("Only the reviewed migration tests may request owned admission")
    rekey = getattr(module, "rekey_database", None)
    if rekey is not None:
        _FIXTURE_CODES[rekey] = rekey._get_wrapped_function().__code__
    _TESTS[function] = function.__code__, rekey
    return function


def helpers_unchanged() -> bool:
    for name, (original, code) in _HELPERS.items():
        current = getattr(migration, name, None)
        if current is not original or getattr(current, "__code__", None) is not code:
            return False
    return all(
        getattr(migration.MigrationDatabase, name, None) is original and original.__code__ is code
        for name, (original, code) in _METHODS.items()
    )


def admitted(item: Any) -> bool:
    """Require exact test/helper identities and every effective fixture definition."""
    function = getattr(item, "obj", None)
    registered = _TESTS.get(function)
    if registered is None or function.__code__ is not registered[0] or not helpers_unchanged():
        return False
    expected = dict(_FIXTURES)
    expected["owned_migration_service"] = (
        owned_migration_service,
        "function",
        ("request", "isolated_postgres_database"),
        None,
    )
    if registered[1] is not None:
        expected["rekey_database"] = (
            registered[1],
            "function",
            ("request", "tmp_path"),
            ("sqlite", "postgres"),
        )
    definitions = dict(getattr(getattr(item, "_fixtureinfo", None), "name2fixturedefs", {}))
    if not literal_parameters(item, definitions):
        return False
    if "owned_migration_service" not in definitions or set(definitions) - expected.keys():
        return False
    # rekey_database obtains this fixture dynamically, so verify that resolution too.
    definitions["migration_database"] = item.session._fixturemanager.getfixturedefs(
        "migration_database", item
    )
    for name, candidates in definitions.items():
        wrapper, scope, arguments, parameters = expected[name]
        if not candidates or len(candidates) != 1:
            return False
        definition = candidates[0]
        if (
            definition.func is not wrapper._get_wrapped_function()
            or definition.func.__code__ is not _FIXTURE_CODES[wrapper]
            or definition.scope != scope
            or definition.argnames != arguments
            or definition.params != parameters
        ):
            return False
    return True


def literal_parameters(item: Any, definitions: dict) -> bool:
    """Only the existing literal boolean and rekey backend parameters are admitted."""
    parameters = getattr(getattr(item, "callspec", None), "params", {})
    if set(parameters) - {"deleted", "rekey_database"}:
        return False
    if "rekey_database" in parameters and parameters["rekey_database"] not in (
        "sqlite",
        "postgres",
    ):
        return False
    if "deleted" not in definitions:
        return "deleted" not in parameters
    candidates = definitions.pop("deleted")
    if len(candidates) != 1 or type(parameters.get("deleted")) is not bool:
        return False
    definition = candidates[0]
    return (
        definition.func is _PARAMETER_FUNCTION
        and definition.func.__code__ is _PARAMETER_CODE
        and definition.scope == "function"
        and definition.argnames == ("request",)
        and definition.params is None
    )


def register_marker(config: pytest.Config) -> None:
    if not config.stash.get(_REGISTERED, False):
        config.addinivalue_line(
            "markers", f"{MARKER}: exact audited per-case UUID migration fixtures"
        )
        config.stash[_REGISTERED] = True


def mark_owned(item: pytest.Item) -> None:
    if admitted(item):
        register_marker(item.config)
        item.add_marker(MARKER)


def service_url(value: str, *, worker: bool = False) -> str:
    """Validate without reflecting credentials or attacker-supplied URLs in errors."""
    try:
        url = make_url(value)
        valid = (
            url.drivername == "postgresql+asyncpg"
            and url.host in {"127.0.0.1", "localhost", "::1"}
            and not url.query
            and bool(url.database)
            and (
                not worker
                or re.fullmatch(r"ase_test_[a-f0-9]{32}_(?:gw[0-9]+|master)", url.database)
            )
        )
    except (ArgumentError, TypeError, ValueError):
        valid = False
    if not valid:
        raise pytest.UsageError("Owned migrations require a query-free loopback PostgreSQL service")
    return value


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--owned-migrations", action="store_true", help="Admit reviewed UUID migrations"
    )


def pytest_configure(config: pytest.Config) -> None:
    register_marker(config)
    if config.getoption("--owned-migrations"):
        if not getattr(config.option, "isolated_postgres", False):
            raise pytest.UsageError("--owned-migrations requires --isolated-postgres")
        service_url(os.environ.get("ASE_TEST_DATABASE_URL", ""))


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    if (
        item.config.getoption("--owned-migrations")
        and item.get_closest_marker(MARKER)
        and not admitted(item)
    ):
        raise pytest.UsageError("Owned migration identities changed after collection")


@pytest.fixture(autouse=True)
def owned_migration_service(
    request: pytest.FixtureRequest, isolated_postgres_database: str | None
) -> Iterator[None]:
    if not request.config.getoption("--owned-migrations") or not request.node.get_closest_marker(
        MARKER
    ):
        yield
        return
    if not admitted(request.node) or isolated_postgres_database is None:
        raise pytest.UsageError("Owned migration admission was not established")
    value = service_url(isolated_postgres_database, worker=True)
    if os.environ.get("ASE_TEST_DATABASE_URL") != value or SERVICE_VARIABLE in os.environ:
        raise pytest.UsageError("Owned migration service environment changed unexpectedly")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv(SERVICE_VARIABLE, value)
        yield


_FIXTURE_CODES[owned_migration_service] = owned_migration_service._get_wrapped_function().__code__

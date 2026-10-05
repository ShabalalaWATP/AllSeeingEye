"""Only audited test/fixture identities receive the UUID service capability."""

import asyncio
import os
from functools import wraps
from types import SimpleNamespace

import pytest

import owned_postgres as owned
import test_rekey_migration_history as rekey
from pytest_support import refuse_shared_databases_in_parallel


def item_for():
    wrappers = dict(owned._FIXTURES)
    wrappers["owned_migration_service"] = (
        owned.owned_migration_service,
        "function",
        ("request", "isolated_postgres_database"),
        None,
    )
    wrappers["rekey_database"] = (
        rekey.rekey_database,
        "function",
        ("request", "tmp_path"),
        ("sqlite", "postgres"),
    )
    definitions = {
        name: [
            SimpleNamespace(
                func=wrapper._get_wrapped_function(),
                scope=scope,
                argnames=arguments,
                params=parameters,
            )
        ]
        for name, (wrapper, scope, arguments, parameters) in wrappers.items()
    }
    manager = SimpleNamespace(getfixturedefs=lambda name, _item: definitions.get(name))
    return SimpleNamespace(
        obj=rekey.test_fresh_rekey_upgrade_is_complete_unenrolled_and_repeatable,
        _fixtureinfo=SimpleNamespace(name2fixturedefs=definitions),
        session=SimpleNamespace(_fixturemanager=manager),
    )


def test_original_graph_is_admitted_but_unknown_test_is_not():
    item = item_for()
    assert owned.admitted(item)
    item.obj = lambda: None
    assert not owned.admitted(item)
    with pytest.raises(ValueError, match="reviewed"):
        owned.owned_migration_test(item.obj)


@pytest.mark.parametrize("name", ["migration_database", "rekey_database", "tmp_path"])
def test_same_name_or_wrapped_fixture_override_cannot_inherit_admission(name):
    item = item_for()
    definition = item._fixtureinfo.name2fixturedefs[name][0]
    original = definition.func

    @wraps(original)
    def override(*args, **kwargs):
        return original(*args, **kwargs)

    definition.func = override
    assert not owned.admitted(item)


@pytest.mark.parametrize("change", ["scope", "arguments", "parameters", "chain", "autouse"])
def test_changed_fixture_graph_is_rejected(change):
    item = item_for()
    definitions = item._fixtureinfo.name2fixturedefs
    definition = definitions["rekey_database"][0]
    if change == "scope":
        definition.scope = "session"
    elif change == "arguments":
        definition.argnames = ("request", "container")
    elif change == "parameters":
        definition.params = ("sqlite", "postgres", "shared")
    elif change == "chain":
        definitions["rekey_database"].append(definition)
    else:
        definitions["unexpected_service"] = [definition]
    assert not owned.admitted(item)


@pytest.mark.parametrize("method", ["run", "migrate"])
def test_replaced_database_method_is_not_trusted(monkeypatch, method):
    monkeypatch.setattr(owned.migration.MigrationDatabase, method, lambda *_args: None)
    assert not owned.admitted(item_for())


def test_dynamic_migration_fixture_must_resolve_to_the_original():
    item = item_for()
    item.session._fixturemanager.getfixturedefs = lambda *_args: ()
    assert not owned.admitted(item)


def test_missing_service_fixture_cannot_deselect_the_original_serial_case():
    item = item_for()
    del item._fixtureinfo.name2fixturedefs["owned_migration_service"]
    assert not owned.admitted(item)


def test_mutated_original_fixture_code_is_rejected(monkeypatch):
    def replacement(request, tmp_path):
        yield None

    function = rekey.rekey_database._get_wrapped_function()
    monkeypatch.setattr(function, "__code__", replacement.__code__)
    assert not owned.admitted(item_for())


@pytest.mark.parametrize("value", [False, True])
def test_only_original_boolean_parameter_fixture_is_admitted(value):
    item = item_for()
    definitions = item._fixtureinfo.name2fixturedefs
    item.callspec = SimpleNamespace(params={"deleted": value, "rekey_database": "postgres"})
    definitions["deleted"] = [
        SimpleNamespace(
            func=owned.pytest_python.get_direct_param_fixture_func,
            scope="function",
            argnames=("request",),
            params=None,
        )
    ]
    assert owned.admitted(item)
    definitions["deleted"][0].func = lambda request: value
    assert not owned.admitted(item)


@pytest.mark.parametrize(
    "parameters",
    [
        {"rekey_database": "shared"},
        {"migration_database": "override"},
        {"deleted": 1},
    ],
)
def test_parameter_overrides_cannot_supply_a_shared_database(parameters):
    item = item_for()
    item.callspec = SimpleNamespace(params=parameters)
    assert not owned.admitted(item)


def test_mutation_after_collection_is_a_failure_not_a_skip(monkeypatch):
    item = item_for()
    item.config = SimpleNamespace(getoption=lambda _name: True)
    item.get_closest_marker = lambda _name: True
    monkeypatch.setattr(owned.migration.MigrationDatabase, "run", lambda *_args: None)
    with pytest.raises(pytest.UsageError, match="identities changed"):
        owned.pytest_runtest_setup(item)


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "sqlite+aiosqlite://",
        "postgresql://localhost/service",
        "postgresql+asyncpg://outside.example/service",
        "postgresql+asyncpg://localhost/service?host=outside.example",
        "postgresql+asyncpg://localhost/service?database=operator",
        "postgresql+asyncpg://localhost/",
    ],
)
def test_service_urls_fail_closed_without_echoing_the_input(url):
    with pytest.raises(pytest.UsageError) as error:
        owned.service_url(url)
    assert str(error.value) == "Owned migrations require a query-free loopback PostgreSQL service"


def test_worker_identity_is_required_for_the_temporary_service():
    for host in ("localhost", "127.0.0.1", "[::1]"):
        value = f"postgresql+asyncpg://{host}/ase_test_{'a' * 32}_gw2"
        assert owned.service_url(value, worker=True) == value
    for name in ("ase", "ase_s01_disposable_ci", "ase_test_bad_gw0"):
        with pytest.raises(pytest.UsageError):
            owned.service_url(f"postgresql+asyncpg://localhost/{name}", worker=True)


def test_existing_guard_still_rejects_other_shared_service_variables(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("ASE_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", "postgresql+asyncpg://localhost/service")
    config = SimpleNamespace(option=SimpleNamespace(numprocesses=4, isolated_postgres=True))
    refuse_shared_databases_in_parallel(config)
    monkeypatch.setenv(owned.SERVICE_VARIABLE, "postgresql+asyncpg://localhost/shared")
    with pytest.raises(pytest.UsageError, match="only ASE_TEST_DATABASE_URL"):
        refuse_shared_databases_in_parallel(config)


@pytest.mark.parametrize("failure", [None, RuntimeError, asyncio.CancelledError])
def test_service_mapping_is_restored_after_success_or_failure(monkeypatch, failure):
    value = f"postgresql+asyncpg://localhost/ase_test_{'b' * 32}_gw0"
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", value)
    monkeypatch.delenv(owned.SERVICE_VARIABLE, raising=False)
    monkeypatch.setattr(owned, "admitted", lambda _item: True)
    request = SimpleNamespace(
        node=SimpleNamespace(get_closest_marker=lambda _name: True),
        config=SimpleNamespace(getoption=lambda _name: True),
    )
    fixture = owned.owned_migration_service._get_wrapped_function()(request, value)
    next(fixture)
    assert os.environ[owned.SERVICE_VARIABLE] == value
    if failure:
        with pytest.raises(failure, match="synthetic"):
            fixture.throw(failure("synthetic"))
    else:
        with pytest.raises(StopIteration):
            next(fixture)
    assert owned.SERVICE_VARIABLE not in os.environ


def test_mapping_refuses_a_preexisting_service_without_overwriting_it(monkeypatch):
    value = f"postgresql+asyncpg://localhost/ase_test_{'b' * 32}_gw0"
    monkeypatch.setenv("ASE_TEST_DATABASE_URL", value)
    monkeypatch.setenv(owned.SERVICE_VARIABLE, "existing-service")
    monkeypatch.setattr(owned, "admitted", lambda _item: True)
    request = SimpleNamespace(
        node=SimpleNamespace(get_closest_marker=lambda _name: True),
        config=SimpleNamespace(getoption=lambda _name: True),
    )
    fixture = owned.owned_migration_service._get_wrapped_function()(request, value)
    with pytest.raises(pytest.UsageError, match="environment changed"):
        next(fixture)
    assert os.environ[owned.SERVICE_VARIABLE] == "existing-service"

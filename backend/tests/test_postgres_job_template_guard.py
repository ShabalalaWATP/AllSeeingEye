"""Only the original report-job fixture graph may use an owned template clone."""

from copy import copy
from functools import wraps
from types import SimpleNamespace

import pytest
from _pytest.fixtures import FixtureDef
from _pytest.scope import Scope

import postgres_template_guard as guard
from ase.infrastructure.settings import Settings
from postgres_template_fixtures import _CHAINS, _FUNCTIONS, job_settings_chain, template_fixture
from postgres_template_guard import ordinary_app
from report_job_api_helpers import job_settings

__all__ = ["job_settings"]


@pytest.fixture
def graph(request, tmp_path):
    manager = request.session._fixturemanager
    definitions = {name: list(manager.getfixturedefs(name, request.node) or ()) for name in _CHAINS}
    assert all(isinstance(value, FixtureDef) for chain in definitions.values() for value in chain)
    source = tmp_path / "test_plain.py"
    source.write_text("def test_read(): pass\n", encoding="utf-8")
    return (
        SimpleNamespace(
            path=source,
            obj=lambda: None,
            session=request.session,
            # Manager lookups use the original real node, including module overrides.
            _fixtureinfo=SimpleNamespace(name2fixturedefs=definitions),
            get_closest_marker=lambda _name: None,
        ),
        definitions,
        request.node,
    )


def test_original_collected_job_chain_is_eligible(graph):
    item, definitions, _ = graph
    assert job_settings_chain(item, definitions)
    assert ordinary_app(item)
    assert [value.func for value in definitions["settings"]] == [
        _FUNCTIONS["settings"],
        _FUNCTIONS["job_settings"],
    ]


@pytest.mark.parametrize("name", tuple(_CHAINS))
@pytest.mark.parametrize("disguise", ["same_name", "wrapped"])
def test_substituted_fixture_functions_do_not_inherit_permission(graph, name, disguise):
    item, definitions, _ = graph
    original = definitions[name][-1]

    def replacement(*_args, **_kwargs):
        pytest.fail("Fixture inspection must never execute a replacement")

    if disguise == "wrapped":
        replacement = wraps(original.func)(replacement)
    else:
        replacement.__name__ = original.func.__name__
    substituted = copy(original)
    substituted.func = replacement
    definitions[name][-1] = substituted
    assert not job_settings_chain(item, definitions)
    assert not ordinary_app(item)


@pytest.mark.parametrize("name", tuple(_CHAINS))
@pytest.mark.parametrize("change", ["scope", "arguments", "parameters", "inserted", "missing"])
def test_changed_fixture_contract_or_chain_is_rejected(graph, name, change):
    item, definitions, _ = graph
    substituted = copy(definitions[name][-1])
    definitions[name][-1] = substituted
    if change == "scope":
        substituted._scope = Scope.Class
    elif change == "arguments":
        substituted.argnames = (*substituted.argnames, "extra_dependency")
    elif change == "parameters":
        substituted.params = ("unexpected",)
    elif change == "inserted":
        definitions[name].insert(0, substituted)
    else:
        definitions[name] = []
    assert not job_settings_chain(item, definitions)


def test_settings_chain_order_matters(graph):
    item, definitions, _ = graph
    definitions["settings"].reverse()
    assert not job_settings_chain(item, definitions)


@pytest.mark.parametrize("name", ["app", "settings"])
def test_unrequested_app_graph_does_not_allocate_a_clone(graph, name):
    item, definitions, _ = graph
    definitions.pop(name)
    assert not job_settings_chain(item, definitions)


def test_wrapping_default_settings_cannot_bypass_job_chain_guard(graph):
    item, definitions, _ = graph

    @wraps(_FUNCTIONS["settings"])
    def forged(*_args, **_kwargs):
        pytest.fail("Inspection must not execute a fixture")

    substitute = copy(definitions["settings"][-1])
    substitute.func = forged
    definitions["settings"][-1] = substitute
    assert not ordinary_app(item)
    definitions["settings"] = [substitute]
    assert not ordinary_app(item)


def test_registration_cannot_redefine_an_original_fixture():
    original = _FUNCTIONS["job_settings"]

    @wraps(original)
    def substitute(*_args, **_kwargs):
        pytest.fail("Inspection must not execute a fixture")

    with pytest.raises(ValueError, match="registered original"):
        template_fixture(substitute)
    assert _FUNCTIONS["job_settings"] is original
    assert template_fixture(original) is original


@pytest.mark.parametrize("name", ["app", "settings"])
def test_failed_default_registration_preserves_both_registries(name):
    original = _FUNCTIONS[name]

    @wraps(original)
    def substitute(*_args, **_kwargs):
        pytest.fail("Inspection must not execute a fixture")

    with pytest.raises(ValueError, match="registered original"):
        guard.template_default(substitute)
    assert _FUNCTIONS[name] is original
    assert guard._DEFAULTS[name] is original


@pytest.mark.parametrize("name", tuple(_CHAINS))
def test_indirect_parameterisation_of_any_protected_fixture_is_rejected(graph, name):
    item, definitions, _ = graph
    item.callspec = SimpleNamespace(params={name: "unexpected"})
    assert not job_settings_chain(item, definitions)


def test_dynamic_worker_lookup_uses_actual_applicable_definitions(graph, monkeypatch):
    item, definitions, real_item = graph
    manager = item.session._fixturemanager
    lookup = manager.getfixturedefs
    calls = []

    def resolve(name, node):
        assert node is item
        calls.append(name)
        return lookup(name, real_item)

    monkeypatch.setattr(manager, "getfixturedefs", resolve)
    definitions.pop("template_worker")
    assert job_settings_chain(item, definitions)
    assert calls == ["template_worker"]
    monkeypatch.setattr(manager, "getfixturedefs", lambda *_args: ())
    assert not job_settings_chain(item, definitions)


@pytest.mark.parametrize("marker", ["postgres", "migration", "race"])
def test_special_lanes_still_use_original_database_setup(graph, marker):
    item, _, _ = graph
    item.get_closest_marker = lambda name: name == marker
    assert not ordinary_app(item)


def test_independent_database_factory_still_requires_normal_setup(graph):
    item, _, _ = graph
    item.path.write_text("def test_custom(): create_engine('sqlite://')\n", encoding="utf-8")
    assert not ordinary_app(item)


def test_job_settings_preserves_postgres_identity_and_sqlite_private_file(tmp_path):
    postgres = Settings(_env_file=None, database_url="postgresql+asyncpg://localhost/private")
    assert _FUNCTIONS["job_settings"](postgres, tmp_path) is postgres
    sqlite = Settings(_env_file=None, database_url="sqlite+aiosqlite://")
    changed = _FUNCTIONS["job_settings"](sqlite, tmp_path)
    assert changed is not sqlite
    assert changed.database_url == f"sqlite+aiosqlite:///{(tmp_path / 'jobs.sqlite').as_posix()}"
    assert sqlite.database_url == "sqlite+aiosqlite://"

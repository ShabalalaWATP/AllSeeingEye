"""Nested and dynamically selected constructors cannot disappear from the DB lane."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call

import pytest
from sqlalchemy.ext.asyncio import create_async_engine as engine_factory

from database_markers import file_constructs_database, uses_database


def test_nested_constructor_is_detected_without_running_it():
    def outer():
        def inner():
            return engine_factory("sqlite+aiosqlite://")

        return inner

    assert uses_database(outer)


def test_bound_constructor_method_is_detected_without_running_it():
    class Factory:
        def make(self):
            return engine_factory("sqlite+aiosqlite://")

    assert uses_database(Factory().make)


def test_captured_factory_alias_is_detected_without_running_it():
    factory = engine_factory

    def make():
        return factory("sqlite+aiosqlite://")

    assert uses_database(make)


def test_file_fallback_preserves_dynamically_selected_methods(tmp_path: Path):
    module = tmp_path / "test_dynamic.py"
    module.write_text(
        "class Harness:\n"
        "    def database(self):\n"
        "        return create_async_engine('sqlite+aiosqlite://')\n"
        "def test_dynamic():\n"
        "    getattr(Harness(), 'database')()\n"
    )
    assert file_constructs_database(module)


def test_persistence_types_without_database_calls_remain_pure(tmp_path: Path):
    module = tmp_path / "test_value.py"
    module.write_text("from ase.adapters.persistence.session import sqlite_path\n")
    assert not file_constructs_database(module)
    assert not uses_database(lambda: 1)


@pytest.mark.parametrize(
    ("factory_name", "module"),
    [(call, "unittest.mock"), ([], "ase.mock"), ("create_engine", []), ("create_engine", call)],
)
def test_dynamic_mock_attributes_cannot_break_database_classification(factory_name, module):
    candidate = SimpleNamespace(__name__=factory_name, __module__=module)

    def ordinary():
        return candidate

    assert not uses_database(ordinary)


def test_literal_factory_name_still_requires_database_with_dynamic_attributes():
    create_engine = SimpleNamespace(__name__=call, __module__=call)

    def constructor():
        return create_engine

    assert uses_database(constructor)

"""Classify persistence tests from their complete fixture and local helper graph."""

import ast
from functools import cache
from inspect import unwrap
from pathlib import Path
from types import CodeType
from typing import Any

TEST_ROOT = Path(__file__).resolve().parent
DATABASE_FACTORIES = {"create_engine", "create_async_engine", "create_app", "Container"}


@cache
def uses_database(function: Any) -> bool:
    return _uses_database(function, set())


def _uses_database(function: Any, visited: set[int]) -> bool:
    """Follow test helpers and imported factory aliases without executing user code."""
    function = unwrap(function) if callable(function) else function
    code = getattr(function, "__code__", None)
    if not isinstance(code, CodeType):
        return False
    if id(function) in visited:
        return False
    visited.add(id(function))
    namespace = dict(getattr(function, "__globals__", {}))
    for name, cell in zip(
        code.co_freevars, getattr(function, "__closure__", None) or (), strict=True
    ):
        try:
            namespace[name] = cell.cell_contents
        except ValueError:  # An uninitialised closure cell has no value to inspect.
            continue
    return _code_uses_database(code, namespace, visited)


def _code_uses_database(code: CodeType, namespace: dict, visited: set[int]) -> bool:
    for nested in code.co_consts:
        if isinstance(nested, CodeType) and _code_uses_database(nested, namespace, visited):
            return True
    for name in (*code.co_names, *code.co_freevars):
        candidate = namespace.get(name)
        factory_name = getattr(candidate, "__name__", name)
        module = getattr(candidate, "__module__", "")
        if name in DATABASE_FACTORIES or (
            factory_name in DATABASE_FACTORIES and module.startswith(("ase.", "sqlalchemy."))
        ):
            return True
        candidate_code = getattr(candidate, "__code__", None)
        if (
            isinstance(candidate_code, CodeType)
            and Path(candidate_code.co_filename).resolve().is_relative_to(TEST_ROOT)
            and _uses_database(candidate, visited)
        ):
            return True
    return False


@cache
def file_constructs_database(path: Path) -> bool:
    """Conservatively retain mixed files with dynamically selected database helpers.

    Function traversal handles ordinary fixture/helper chains. A factory call
    anywhere in a test module keeps all its tests in the PostgreSQL selection,
    including nested closures and methods selected dynamically at runtime.
    Imports and type annotations alone do not turn pure DTO tests into DB tests.
    """
    if not path.is_file():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id in DATABASE_FACTORIES)
            or (isinstance(node.func, ast.Attribute) and node.func.attr in DATABASE_FACTORIES)
        )
        for node in ast.walk(tree)
    )

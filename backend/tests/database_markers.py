"""Classify persistence tests from their complete fixture and local helper graph."""

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
    namespace = getattr(function, "__globals__", {})
    for name in code.co_names:
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

"""Exact fixture identities for the report-job PostgreSQL template opt-in."""

from collections.abc import Callable
from typing import Any

from _pytest.tmpdir import tmp_path, tmp_path_factory
from xdist.plugin import worker_id

# Capture trusted raw functions at their declarations. Never unwrap candidates:
# functools.wraps and same-name overrides must not inherit this permission.
_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "tmp_path": tmp_path._get_wrapped_function(),
    "tmp_path_factory": tmp_path_factory._get_wrapped_function(),
    "worker_id": worker_id._get_wrapped_function(),
}
_CHAINS = {
    "app": (
        (
            "app",
            "function",
            ("settings", "clock", "email_sender", "feed_connectors", "template_database"),
        ),
    ),
    "settings": (
        ("settings", "function", ("request", "template_database")),
        ("job_settings", "function", ("settings", "tmp_path")),
    ),
    "template_database": (("template_database", "function", ("request",)),),
    "template_worker": (("template_worker", "session", ("request", "isolated_postgres_database")),),
    "isolated_postgres_database": (
        ("isolated_postgres_database", "session", ("request", "worker_id")),
    ),
    "worker_id": (("worker_id", "session", ("request",)),),
    "tmp_path": (("tmp_path", "function", ("request", "tmp_path_factory")),),
    "tmp_path_factory": (("tmp_path_factory", "session", ("request",)),),
}


def template_fixture(function: Callable[..., Any]) -> Callable[..., Any]:
    """Register repository fixture functions before pytest decorates them."""
    original = _FUNCTIONS.get(function.__name__)
    if original is not None and original is not function:
        raise ValueError("A template fixture cannot replace its registered original")
    _FUNCTIONS[function.__name__] = function
    return function


def job_settings_chain(item: Any, definitions: dict) -> bool:
    """Admit only the original graph, including dynamically requested prerequisites.

    Pinned pytest resolves dependencies before the async app's setup hook. All
    template/settings prerequisites are synchronous, so their FixtureDef.func is
    the original function at this decision. Any future wrapper fails closed.
    This inspects fixture definitions without creating a fixture or a database.
    """
    if not definitions.get("app") or not definitions.get("settings"):
        return False
    if set(getattr(getattr(item, "callspec", None), "params", ())) & _CHAINS.keys():
        return False
    manager = getattr(getattr(item, "session", None), "_fixturemanager", None)
    if manager is None:
        return False
    for name, expected in _CHAINS.items():
        candidates = definitions.get(name)
        if candidates is None:
            candidates = manager.getfixturedefs(name, item)
        if not candidates or len(candidates) != len(expected):
            return False
        for definition, (key, scope, arguments) in zip(candidates, expected, strict=True):
            function = _FUNCTIONS.get(key)
            if (
                function is None
                or definition.func is not function
                or definition.scope != scope
                or definition.argnames != arguments
                or definition.params is not None
            ):
                return False
    return True

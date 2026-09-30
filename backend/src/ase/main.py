"""ASGI entry point. Import ase.app_factory for reusable application construction."""

from time import perf_counter

_import_started = perf_counter()

from ase.app_factory import create_app  # noqa: E402 - measure the heavy import boundary
from ase.app_lifecycle import lifespan  # noqa: E402
from ase.infrastructure.startup import record_startup_phase  # noqa: E402

__all__ = ["app", "create_app", "lifespan"]

record_startup_phase("import", _import_started)
app = create_app()

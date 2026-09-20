"""ASGI entry point. Import ase.app_factory for reusable application construction."""

from ase.app_factory import create_app
from ase.app_lifecycle import lifespan

__all__ = ["app", "create_app", "lifespan"]

app = create_app()

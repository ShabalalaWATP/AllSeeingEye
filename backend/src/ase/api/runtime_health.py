"""Typed access to the lifespan's process-local health state."""

from typing import Annotated

from fastapi import Depends, Request

from ase.container.runtime_health import RuntimeHealth


def runtime_health(request: Request) -> RuntimeHealth:
    runtime: RuntimeHealth = request.app.state.runtime
    return runtime


RuntimeDep = Annotated[RuntimeHealth, Depends(runtime_health)]

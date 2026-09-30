"""Liveness and readiness."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from ase.api.deps import SessionDep
from ase.api.errors import NotReady
from ase.api.runtime_health import RuntimeDep
from ase.api.schemas import HealthOut, ReadyOut

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/ready")
async def ready(session: SessionDep, runtime: RuntimeDep) -> ReadyOut:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise NotReady() from exc
    if not runtime.ready:
        raise NotReady()
    return ReadyOut(status="ready")

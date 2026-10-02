"""Runtime health is an administrator-only, session-fenced operational view."""

from dataclasses import asdict

from fastapi import APIRouter

from ase.api.deps import AdminUser, ContainerDep, SessionDep
from ase.api.routers.stream import ENCODER
from ase.api.runtime_health import RuntimeDep
from ase.api.schemas_runtime import RuntimeHealthOut, WorkerHealthOut
from ase.api.session_fence import FenceDep
from ase.container.runtime_health import runtime_totals

router = APIRouter(prefix="/admin/runtime", tags=["admin"])


@router.get("")
async def get_runtime(
    admin: AdminUser,
    container: ContainerDep,
    session: SessionDep,
    runtime: RuntimeDep,
    fence: FenceDep,
) -> RuntimeHealthOut:
    totals = await runtime_totals(container, session)
    result = RuntimeHealthOut.model_validate(
        {
            **totals,
            "ready": runtime.ready,
            "workers": [WorkerHealthOut(**asdict(item)) for item in runtime.workers.snapshot()],
            "loop_lag_p99_ms": round(runtime.lag.p99_seconds * 1000, 3),
            "stream_encoder_cached_chars": ENCODER.cached_chars,
        }
    )
    return await fence.release(result, admin_only=True)

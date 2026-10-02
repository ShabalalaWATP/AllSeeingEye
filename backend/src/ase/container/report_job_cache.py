"""Attempt-local parsed input reuse. Authorisation and source admission are never cached."""

import json
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import replace
from typing import Any

from ase.application.report_jobs.snapshots import restore_job
from ase.application.reports.production_types import Job
from ase.domain.llm import LlmProfile
from ase.domain.users import User


def snapshot_key(value: dict[str, Any]) -> str:
    # Values originate in decoded, integrity-checked checkpoint JSON. JSON spelling
    # distinguishes bool/int/float where Python's nested equality would not.
    pending: list[Any] = [value]
    while pending:
        item = pending.pop()
        if type(item) is tuple:
            # Proposed checkpoint mutations have not been through json.loads yet.
            # A tuple must not borrow validation from an otherwise identical array.
            raise ValueError("Report snapshots require JSON arrays")
        if type(item) is dict:
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


class AttemptCache:
    def __init__(self) -> None:
        self._input: str | None = None
        self._job: Job | None = None
        self.source_key: str | None = None
        self.source_ids: frozenset[str] = frozenset()

    def restore(self, frozen: dict[str, Any], actor: User, profile: LlmProfile) -> Job:
        key = snapshot_key(frozen)
        if self._input != key or self._job is None:
            restored = restore_job(frozen, actor, profile)
            self._input, self._job = key, deepcopy(restored)
        # Frozen dataclasses still contain mappings; never expose a cached alias.
        return replace(deepcopy(self._job), actor=actor, profile=profile)


attempt_cache: ContextVar[AttemptCache | None] = ContextVar(
    "report_job_attempt_cache", default=None
)

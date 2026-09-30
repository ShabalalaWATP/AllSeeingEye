"""Section checkpoint validation and updates within one worker attempt."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from ase.application.ports.section_checkpoints import SectionCheckpoint
from ase.application.report_jobs.budget import JobInterrupted
from ase.domain.report_jobs import job_error

if TYPE_CHECKING:
    from ase.container.report_job_checkpoints import ReportJobCheckpoints


class ReportJobSections:
    def __init__(self, parent: ReportJobCheckpoints) -> None:
        self.parent = parent

    @staticmethod
    def _key(packet_digest: str, section_id: str) -> str:
        if (
            not re.fullmatch(r"[0-9a-f]{64}", packet_digest)
            or not 1 <= len(section_id.strip()) <= 120
            or len(section_id) > 120
            or any(ord(char) < 32 for char in section_id)
        ):
            raise JobInterrupted()
        return f"{packet_digest}:{section_id}"

    async def load(self, packet_digest: str, section_id: str) -> SectionCheckpoint | None:
        key = self._key(packet_digest, section_id)
        payload = await self.parent._read()
        sections = payload.get("sections", {})
        if type(sections) is not dict:
            raise JobInterrupted()
        value = sections.get(key)
        if value is None:
            return None
        if (
            type(value) is not dict
            or value.get("packet_digest") != packet_digest
            or value.get("section_id") != section_id
            or value.get("status") not in {"running", "completed", "split", "incomplete"}
        ):
            raise JobInterrupted()
        return SectionCheckpoint(value["status"], value.get("payload"), value.get("reason"))

    async def save(
        self, packet_digest: str, section_id: str, checkpoint: SectionCheckpoint
    ) -> None:
        key = self._key(packet_digest, section_id)
        if checkpoint.status not in {"running", "completed", "split", "incomplete"} or (
            checkpoint.payload is not None and type(checkpoint.payload) is not dict
        ):
            raise JobInterrupted()
        job_error(checkpoint.reason)
        value = {
            "packet_digest": packet_digest,
            "section_id": section_id,
            "status": checkpoint.status,
            "payload": deepcopy(checkpoint.payload),
            "reason": checkpoint.reason,
        }

        def save(payload: dict[str, Any]) -> None:
            sections = payload.setdefault("sections", {})
            if type(sections) is not dict:
                raise JobInterrupted()
            previous = sections.get(key)
            if previous is not None and type(previous) is not dict:
                raise JobInterrupted()
            if previous and previous.get("status") == "completed" and previous != value:
                raise JobInterrupted()
            sections[key] = value
            kind = (checkpoint.payload or {}).get("kind")
            # Post-draft stages share this store under their own digest. Only a drafted
            # section moves the packet pointer, or progress would follow the later stage
            # and the reader would lose the sections already written.
            if kind in {"topic", "synthesis"}:
                payload["current_packet"] = packet_digest
                payload["stage"] = "summarising" if kind == "synthesis" else "drafting"

        await self.parent.mutate(save)

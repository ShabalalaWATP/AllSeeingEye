"""Authenticated external evidence, not an exhaustive log of application decisions."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from pydantic import ValidationError

from ase.adapters.security.recovery_files import (
    create_private,
    journal_lock,
    read_bounded,
    replace_private,
    safe_file,
)
from ase.adapters.security.recovery_schema import (
    MAX_CIPHERTEXT,
    MAX_EVENTS,
    MAX_PLAINTEXT,
    CopyReview,
    Entry,
    JournalDocument,
    Removal,
    Resolution,
    Restriction,
    Review,
    inspection,
)
from ase.domain.errors import Conflict
from ase.domain.private_removal import RemovalRequest, ReviewDecision, ReviewPurpose


class FileRecoveryJournal:
    def __init__(self, path: Path, key: Path, *, excluded: tuple[Path, ...] = ()) -> None:
        self.path, self.key = safe_file(path), safe_file(key)
        self.lock = safe_file(path.with_name(path.name + ".lock"))
        if len({self.path, self.key, self.lock}) != 3:
            raise Conflict("Journal, key and lock require separate files.")
        for root in excluded:
            if any(p.is_relative_to(root.resolve()) for p in (self.path, self.key)):
                raise Conflict("Keep recovery records outside application and backup directories.")

    def initialise(self) -> None:
        with journal_lock(self.lock):
            if self.path.exists() or self.key.exists():
                raise Conflict("Initialisation never replaces an existing journal or key.")
            key = Fernet.generate_key()
            create_private(self.key, key)
            document = JournalDocument(journal_id=uuid4(), created_at=datetime.now(UTC), entries=[])
            create_private(self.path, Fernet(key).encrypt(document.model_dump_json().encode()))

    def _cipher(self) -> Fernet:
        return Fernet(read_bounded(self.key, 44))

    def _read(self) -> JournalDocument:
        try:
            plaintext = self._cipher().decrypt(read_bounded(self.path, MAX_CIPHERTEXT))
            if len(plaintext) > MAX_PLAINTEXT:
                raise Conflict("Recovery record exceeds its safety limit.")
            return JournalDocument.model_validate_json(plaintext)
        except (InvalidToken, ValidationError, ValueError, OSError):
            raise Conflict(
                "Recovery journal cannot be authenticated or read; do not reset it."
            ) from None

    @staticmethod
    def _head(document: JournalDocument) -> str:
        return hashlib.sha256(document.model_dump_json().encode()).hexdigest()

    def inspect(self) -> dict[str, object]:
        with journal_lock(self.lock):
            document = self._read()
            return inspection(document, self._head(document), datetime.now(UTC))

    def _write(self, document: JournalDocument) -> None:
        # Revalidate model_copy updates, including capacity and discriminated record types.
        checked = JournalDocument.model_validate_json(document.model_dump_json())
        plaintext = checked.model_dump_json().encode()
        if len(plaintext) > MAX_PLAINTEXT:
            raise Conflict("Recovery journal is full; preserve it and review capacity.")
        replace_private(self.path, self._cipher().encrypt(plaintext))

    def _append(
        self,
        actor: UUID,
        action: Removal | Review | Restriction | CopyReview,
        now: datetime,
    ) -> UUID:
        with journal_lock(self.lock):
            document = self._read()
            if any(e.status == "pending" for e in document.entries):
                raise Conflict("An earlier journal intent is unresolved; investigate it first.")
            if len(document.entries) >= MAX_EVENTS:
                raise Conflict("Recovery journal is full; retain its history and review capacity.")
            event = Entry(
                id=uuid4(),
                sequence=len(document.entries) + 1,
                actor=actor,
                at=now,
                action=action,
                status="recorded" if isinstance(action, Restriction | CopyReview) else "pending",
            )
            updated = document.model_copy(update={"entries": [*document.entries, event]})
            # Reserve space for the largest allowed resolution before any database mutation.
            if len(updated.model_dump_json().encode()) + 1024 > MAX_PLAINTEXT:
                raise Conflict("Recovery journal lacks completion capacity.")
            self._write(updated)
            return event.id

    def begin_removal(self, actor: UUID, request: RemovalRequest, now: datetime) -> UUID:
        return self._append(
            actor,
            Removal(
                owner=request.owner_id,
                scope=request.scope,
                target=request.target_id,
            ),
            now,
        )

    def begin_review(
        self,
        actor: UUID,
        owner: UUID,
        decision: ReviewDecision,
        purpose: ReviewPurpose,
        revision: int,
        now: datetime,
        due: datetime,
    ) -> UUID:
        return self._append(
            actor,
            Review(
                owner=owner,
                decision=decision,
                purpose=purpose,
                revision=revision,
                due=due,
            ),
            now,
        )

    def record(self, actor: UUID, action: Restriction | CopyReview, now: datetime) -> UUID:
        return self._append(actor, action, now)

    def complete(self, event: UUID) -> None:
        self._finish(event, "committed")

    def resolve(
        self,
        event: UUID,
        applied: bool,
        actor: UUID,
        evidence: str,
        expected_head: str,
    ) -> None:
        self._finish(
            event,
            "committed" if applied else "not_applied",
            resolution=Resolution(operator=actor, at=datetime.now(UTC), evidence_sha256=evidence),
            expected_head=expected_head,
        )

    def _finish(
        self,
        event: UUID,
        status: str,
        *,
        resolution: Resolution | None = None,
        expected_head: str | None = None,
    ) -> None:
        with journal_lock(self.lock):
            document = self._read()
            if expected_head is not None and expected_head != self._head(document):
                raise Conflict("Journal changed; inspect it again before resolving an intent.")
            matching = [e for e in document.entries if e.id == event]
            if len(matching) != 1 or matching[0].status != "pending":
                raise Conflict("Only an existing unresolved intent can be completed.")
            entries = [
                e.model_copy(update={"status": status, "resolution": resolution})
                if e.id == event
                else e
                for e in document.entries
            ]
            self._write(document.model_copy(update={"entries": entries}))

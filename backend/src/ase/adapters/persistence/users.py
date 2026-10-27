"""User and account request repositories."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import AccountRequestRow, AdministrationLockRow, UserRow
from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.adapters.persistence.session_changes import mark_session_change
from ase.adapters.persistence.web_push_devices import remove_push_user
from ase.domain.errors import Conflict, NotFound
from ase.domain.users import AccountRequest, RequestStatus, Role, User


def _user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        role=Role(row.role),
        is_active=row.is_active,
        password_hash=row.password_hash,
        failed_login_count=row.failed_login_count,
        last_failed_at=row.last_failed_at,
        locked_until=row.locked_until,
        created_at=row.created_at,
        last_login_at=row.last_login_at,
        security_version=row.security_version,
        terms_version=row.terms_version,
        terms_accepted_at=row.terms_accepted_at,
    )


def _apply_user(row: UserRow, user: User) -> None:
    row.email = user.email
    row.display_name = user.display_name
    row.role = user.role.value
    row.is_active = user.is_active
    row.password_hash = user.password_hash
    row.failed_login_count = user.failed_login_count
    row.last_failed_at = user.last_failed_at
    row.locked_until = user.locked_until
    row.created_at = user.created_at
    row.last_login_at = user.last_login_at
    row.security_version = user.security_version
    row.terms_version = user.terms_version
    row.terms_accepted_at = user.terms_accepted_at


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_administration(self) -> None:
        insert = (
            pg_insert if self._session.get_bind().dialect.name == "postgresql" else sqlite_insert
        )
        await self._session.execute(
            insert(AdministrationLockRow).values(id=1).on_conflict_do_nothing(index_elements=["id"])
        )
        await self._session.execute(
            update(AdministrationLockRow).where(AdministrationLockRow.id == 1).values(id=1)
        )

    async def lock_by_id(self, user_id: UUID) -> User | None:
        # A no-op UPDATE takes a row lock on PostgreSQL and the writer lock on
        # SQLite. SELECT FOR UPDATE alone would silently do nothing on SQLite.
        await self._session.execute(
            update(UserRow).where(UserRow.id == user_id).values(id=UserRow.id)
        )
        row = await self._session.get(UserRow, user_id, populate_existing=True)
        return _user_from_row(row) if row else None

    async def lock_by_email(self, email: str) -> User | None:
        await self._session.execute(
            update(UserRow).where(UserRow.email == email).values(id=UserRow.id)
        )
        row = await self._session.scalar(
            select(UserRow).where(UserRow.email == email).execution_options(populate_existing=True)
        )
        return _user_from_row(row) if row else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id, populate_existing=True)
        return _user_from_row(row) if row else None

    async def display_names(self, user_ids: Sequence[UUID]) -> dict[UUID, str]:
        # Limit bind parameters on both SQLite and PostgreSQL, even for callers
        # larger than the current 200-alert and 50-job list bounds.
        unique = list(dict.fromkeys(user_ids))
        names: dict[UUID, str] = {}
        for start in range(0, len(unique), 200):
            rows = await self._session.execute(
                select(UserRow.id, UserRow.display_name).where(
                    UserRow.id.in_(unique[start : start + 200])
                )
            )
            names.update((row.id, row.display_name) for row in rows)
        return names

    async def get_by_email(self, email: str) -> User | None:
        row = (await self._session.scalars(select(UserRow).where(UserRow.email == email))).first()
        return _user_from_row(row) if row else None

    async def add(self, user: User) -> None:
        row = UserRow(id=user.id)
        _apply_user(row, user)
        self._session.add(row)
        await self._session.flush()

    async def save(self, user: User) -> None:
        # Read the marker afresh even if this session cached the account before
        # removal. Callers hold the account lock, shared with operator removal.
        erased_at = await self._session.scalar(
            select(PrivateDataReviewRow.erased_at).where(PrivateDataReviewRow.owner_id == user.id)
        )
        if erased_at is not None:
            raise Conflict("This account was removed and cannot be restored.")
        row = await self._session.get(UserRow, user.id)
        if row is None:
            raise NotFound()
        before = (row.is_active, row.role, row.security_version)
        _apply_user(row, user)
        if before != (row.is_active, row.role, row.security_version):
            await remove_push_user(self._session, user.id)
            mark_session_change(self._session, user.id)
        await self._session.flush()

    async def list_all(self) -> list[User]:
        rows = await self._session.scalars(select(UserRow).order_by(UserRow.created_at))
        return [_user_from_row(row) for row in rows]


def _request_from_row(row: AccountRequestRow) -> AccountRequest:
    return AccountRequest(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        reason=row.reason,
        status=RequestStatus(row.status),
        decided_by=row.decided_by,
        decided_at=row.decided_at,
        created_at=row.created_at,
        terms_version=row.terms_version,
        terms_accepted_at=row.terms_accepted_at,
    )


def _apply_request(row: AccountRequestRow, request: AccountRequest) -> None:
    row.email = request.email
    row.display_name = request.display_name
    row.reason = request.reason
    row.status = request.status.value
    row.decided_by = request.decided_by
    row.decided_at = request.decided_at
    row.created_at = request.created_at
    row.terms_version = request.terms_version
    row.terms_accepted_at = request.terms_accepted_at


class SqlAccountRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, request_id: UUID) -> AccountRequest | None:
        row = await self._session.get(AccountRequestRow, request_id, populate_existing=True)
        return _request_from_row(row) if row else None

    async def add(self, request: AccountRequest) -> None:
        row = AccountRequestRow(id=request.id)
        _apply_request(row, request)
        self._session.add(row)
        await self._session.flush()

    async def save(self, request: AccountRequest) -> None:
        row = await self._session.get(AccountRequestRow, request.id)
        if row is None:
            raise NotFound()
        _apply_request(row, request)
        await self._session.flush()

    async def list_by_status(self, status: RequestStatus) -> list[AccountRequest]:
        stmt = (
            select(AccountRequestRow)
            .where(AccountRequestRow.status == status.value)
            .order_by(AccountRequestRow.created_at)
        )
        return [_request_from_row(row) for row in await self._session.scalars(stmt)]

    async def has_pending_for_email(self, email: str) -> bool:
        stmt = select(AccountRequestRow.id).where(
            AccountRequestRow.email == email,
            AccountRequestRow.status == RequestStatus.PENDING.value,
        )
        return (await self._session.scalars(stmt)).first() is not None

    async def count_pending(self) -> int:
        stmt = select(func.count(AccountRequestRow.id)).where(
            AccountRequestRow.status == RequestStatus.PENDING.value
        )
        return int(await self._session.scalar(stmt) or 0)

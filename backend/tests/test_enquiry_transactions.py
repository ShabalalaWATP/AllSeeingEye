"""Enquiry duplicate handling must remain inside the audit transaction."""

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from ase.adapters.persistence.enterprise_enquiries import EnterpriseEnquiryRow, SqlEnquiryRepository
from ase.adapters.persistence.session import create_engine
from ase.application.auditing import Auditor
from ase.domain.enterprise_enquiries import EnquiryDetails, EnquiryStatus, EnterpriseEnquiry
from test_enterprise_enquiries import PAYLOAD, enquiries  # noqa: F401


def record(clock):
    return EnterpriseEnquiry(
        uuid4(), EnquiryDetails(**PAYLOAD), EnquiryStatus.NEW, clock.now(), clock.now()
    )


async def test_rollback_removes_first_enquiry_insert(container, clock):
    async with container.session_factory() as session:
        assert await SqlEnquiryRepository(session).add_once(record(clock), "a" * 64)
        await session.rollback()
    async with container.session_factory() as session:
        assert (await session.scalars(select(EnterpriseEnquiryRow))).all() == []


async def test_audit_failure_does_not_leave_an_enquiry(client, enquiries, monkeypatch):  # noqa: F811
    async def failed(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(Auditor, "record", failed)
    assert (await client.post("/api/enquiries", json=PAYLOAD)).status_code == 500
    async with enquiries.session_factory() as session:
        assert (await session.scalars(select(EnterpriseEnquiryRow))).all() == []
    assert not enquiries.operator_notices.messages


async def test_other_integrity_errors_are_not_silently_duplicates(container, clock):
    row = record(clock)
    async with container.session_factory() as session:
        assert await SqlEnquiryRepository(session).add_once(row, "a" * 64)
        await session.commit()
    async with container.session_factory() as session:
        with pytest.raises(IntegrityError):
            await SqlEnquiryRepository(session).add_once(row, "b" * 64)


async def test_two_concurrent_connections_store_one_duplicate(tmp_path, clock):
    engine = create_engine(f"sqlite+aiosqlite:///{(tmp_path / 'enquiries.db').as_posix()}")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(EnterpriseEnquiryRow.__table__.create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        row = record(clock)

        async def insert():
            async with sessions() as session:
                created = await SqlEnquiryRepository(session).add_once(
                    replace(row, id=uuid4()), "a" * 64
                )
                await session.commit()
                return created

        assert sorted(await asyncio.gather(insert(), insert())) == [False, True]
        async with sessions() as session:
            assert len((await session.scalars(select(EnterpriseEnquiryRow))).all()) == 1
    finally:
        await engine.dispose()

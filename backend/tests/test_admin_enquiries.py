"""Administrative enquiry reads, decisions and erasure retain session boundaries."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from ase.adapters.persistence.enterprise_enquiries import EnterpriseEnquiryRow, SqlEnquiryRepository
from ase.adapters.persistence.models import AuditLogRow
from ase.domain.enterprise_enquiries import EnquiryDetails, EnquiryStatus, EnterpriseEnquiry
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


async def seed(container, *, days=0, status=EnquiryStatus.NEW):
    now = container.clock.now() - timedelta(days=days)
    item = EnterpriseEnquiry(
        uuid4(),
        EnquiryDetails("Example", "enquirer@example.com", "Company", "own_cloud", "1_10"),
        status,
        now,
        now,
    )
    async with container.session_factory() as session:
        await SqlEnquiryRepository(session).add_once(item, str(item.id))
        await session.commit()
    return item


async def test_admin_filters_before_counts_and_limits(client, container, admin):
    wanted = await seed(container, days=1, status=EnquiryStatus.CONTACTED)
    await seed(container)
    await seed(container, days=366, status=EnquiryStatus.CONTACTED)
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    response = await client.get("/api/admin/enquiries?status=contacted&limit=1", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [str(wanted.id)]


async def test_status_and_erasure_have_minimal_audit(client, container, admin, clock):
    item = await seed(container)
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    clock.advance(timedelta(seconds=10))
    url = f"/api/admin/enquiries/{item.id}"
    updated = await client.patch(url, json={"status": "contacted"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["status"] == "contacted"
    assert updated.json()["updated_at"] != updated.json()["created_at"]
    loaded = await client.get(url, headers=headers)
    assert loaded.status_code == 200 and loaded.json() == updated.json()
    assert loaded.headers["cache-control"] == "no-store"
    erased = await client.delete(url, headers=headers)
    assert erased.status_code == 204
    assert erased.headers["cache-control"] == "no-store"
    assert (await client.get(url, headers=headers)).status_code == 404
    assert (await client.get("/api/admin/enquiries", headers=headers)).json()["total"] == 0
    async with container.session_factory() as session:
        assert await session.get(EnterpriseEnquiryRow, item.id) is None
        audit = (
            await session.scalars(select(AuditLogRow).where(AuditLogRow.subject == str(item.id)))
        ).all()
        assert len(audit) == 2
        assert all(
            row.actor_user_id == admin.id and row.ip is None and row.details == {} for row in audit
        )


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
async def test_non_admin_cannot_access(client, container, user, method):
    item = await seed(container)
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    kwargs = {"json": {"status": "closed"}} if method == "patch" else {}
    response = await getattr(client, method)(
        f"/api/admin/enquiries/{item.id}", headers=headers, **kwargs
    )
    assert response.status_code == 403


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "status=other"])
async def test_invalid_pagination_is_refused(client, admin, query):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    assert (await client.get(f"/api/admin/enquiries?{query}", headers=headers)).status_code == 422

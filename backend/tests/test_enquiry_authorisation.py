"""Protect private records against stale, demoted and unverified administrators."""

from datetime import timedelta

import pytest

from ase.application.admin.enquiries import AdminEnquiries
from ase.application.dto import RequestContext
from ase.domain.errors import Forbidden, Unauthenticated
from ase.domain.users import Role
from helpers import bearer
from test_admin_enquiries import seed


async def start(container, actor, *, verified=True):
    async with container.session_factory() as session:
        repos = container.repositories(session)
        auth = await container._sessions(repos).start(
            actor, RequestContext(), mfa_verified=verified
        )
        await repos.uow.commit()
        return auth


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
@pytest.mark.parametrize("invalidity", ["mfa", "revoked", "expired"])
async def test_private_endpoints_reject_invalid_sessions(
    client, container, admin, clock, method, invalidity
):
    item = await seed(container)
    auth = await start(container, admin, verified=invalidity != "mfa")
    if invalidity == "revoked":
        claims = container.issuer.verify(auth.access.token)
        async with container.session_factory() as session:
            repos = container.repositories(session)
            await repos.refresh_tokens.revoke_family(claims.family_id, clock.now())
            await repos.uow.commit()
    elif invalidity == "expired":
        clock.advance(timedelta(hours=1))
    kwargs = {"json": {"status": "closed"}} if method == "patch" else {}
    result = await getattr(client, method)(
        f"/api/admin/enquiries/{item.id}", headers=bearer(auth.access.token), **kwargs
    )
    assert result.status_code == 401


async def test_use_cases_require_admin_without_a_route(container, user):
    async with container.session_factory() as session:
        use_case = container.admin_enquiries(session)
        with pytest.raises(Forbidden):
            await use_case.list(user, None, 25, 0)
        with pytest.raises(Forbidden):
            await use_case.get(user, user.id)


async def test_mutation_rechecks_demotion_under_administration_guard(container, admin):
    item = await seed(container)
    auth = await start(container, admin)
    claims = container.issuer.verify(auth.access.token)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        current = await repos.users.lock_by_id(admin.id)
        current.role = Role.USER
        await repos.users.save(current)
        await repos.uow.commit()
    async with container.session_factory() as session:
        with pytest.raises(Forbidden):
            await container.admin_enquiries(session).delete(claims, item.id)


async def test_expiry_during_mutation_rolls_back_content_and_audit(
    container, admin, clock, monkeypatch
):
    item = await seed(container)
    auth = await start(container, admin)
    claims = container.issuer.verify(auth.access.token)
    async with container.session_factory() as session:
        use_case = container.admin_enquiries(session)
        original = use_case.repository.delete

        async def delayed_delete(enquiry_id):
            await original(enquiry_id)
            clock.advance(timedelta(hours=1))

        monkeypatch.setattr(use_case.repository, "delete", delayed_delete)
        with pytest.raises(Unauthenticated):
            await use_case.delete(claims, item.id)
    async with container.session_factory() as session:
        assert await container.admin_enquiries(session).get(admin, item.id) == item


@pytest.mark.parametrize("read", ["get", "list"])
async def test_private_read_is_fenced_after_expiry(
    client, container, admin, clock, monkeypatch, read
):
    item = await seed(container)
    auth = await start(container, admin)
    original = getattr(AdminEnquiries, read)

    async def delayed(self, *args):
        result = await original(self, *args)
        clock.advance(timedelta(hours=1))
        return result

    monkeypatch.setattr(AdminEnquiries, read, delayed)
    path = "/api/admin/enquiries" + (f"/{item.id}" if read == "get" else "")
    response = await client.get(path, headers=bearer(auth.access.token))
    assert response.status_code == 401
    assert "enquirer@example.com" not in response.text

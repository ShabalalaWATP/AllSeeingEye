"""Catalogue access is personal, rate limited and checked again before release."""

from contextlib import asynccontextmanager

import pytest

from ase.application.dto import RequestContext
from ase.application.footprints import FootprintSearchUseCase
from ase.container import Container
from ase.domain.errors import RateLimited, Unauthenticated
from ase.domain.footprints import FootprintCollection
from ase.domain.users import User
from research_feed_helpers import CLOCK
from test_copernicus_footprints import QUERY


class Admission:
    allowed = True

    @asynccontextmanager
    async def guard(self):
        yield

    async def enabled(self, source_id):
        assert source_id == "research-copernicus-footprints"
        return self.allowed

    async def enabled_many(self, source_ids):
        return dict.fromkeys(source_ids, self.allowed)


class Provider:
    calls = 0
    admission = None

    async def search(self, query):
        self.calls += 1
        if self.admission:
            self.admission.allowed = False
        return FootprintCollection((), "completed", False, "Synthetic result", CLOCK.now())


async def test_admin_disable_before_and_during_query(container: Container, user: User) -> None:
    provider, admission = Provider(), Admission()
    admission.allowed = False
    use_case = FootprintSearchUseCase(provider, container.limiter, CLOCK, admission)
    checks = 0

    async def validate():
        nonlocal checks
        checks += 1

    result = await use_case.execute(user, QUERY, RequestContext(), validate)
    assert result.status == "unavailable" and provider.calls == 0
    admission.allowed, provider.admission = True, admission
    result = await use_case.execute(user, QUERY, RequestContext(), validate)
    assert result.status == "unavailable" and provider.calls == 1 and checks == 3


async def test_revocation_during_external_work_rejects_result(
    container: Container, user: User
) -> None:
    provider = Provider()
    use_case = FootprintSearchUseCase(provider, container.limiter, CLOCK)
    checks = 0

    async def validate():
        nonlocal checks
        checks += 1
        if checks == 2:
            raise Unauthenticated()

    with pytest.raises(Unauthenticated):
        await use_case.execute(user, QUERY, RequestContext(), validate)
    assert provider.calls == 1


async def test_rate_limit_and_inactive_actor_make_no_extra_requests(
    container: Container, user: User
) -> None:
    provider = Provider()
    use_case = FootprintSearchUseCase(provider, container.limiter, CLOCK)

    async def validate():
        pass

    for _ in range(5):
        await use_case.execute(user, QUERY, RequestContext(), validate)
    with pytest.raises(RateLimited):
        await use_case.execute(user, QUERY, RequestContext(), validate)
    user.is_active = False
    with pytest.raises(Unauthenticated):
        await use_case.execute(user, QUERY, RequestContext(), validate)
    assert provider.calls == 5

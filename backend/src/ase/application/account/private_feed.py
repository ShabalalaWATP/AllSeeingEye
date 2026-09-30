"""Explicit opt-in feed credentials have no authority outside their narrow projection."""

from dataclasses import replace

from ase.application.access import AccessPolicy
from ase.application.ports.notification_feed import PrivateFeedRepository
from ase.application.ports.repositories import UnitOfWork, UserRepository
from ase.application.ports.services import Clock, RateLimiter, TokenGenerator
from ase.domain.access import Visibility
from ase.domain.errors import RateLimited, Unauthenticated
from ase.domain.notification_feed import (
    FeedStatus,
    FeedToken,
    IssuedFeedToken,
    PrivateFeed,
)
from ase.domain.users import User

FEED_LIMIT = 100


class PrivateFeedService:
    def __init__(
        self,
        repository: PrivateFeedRepository,
        users: UserRepository,
        access: AccessPolicy,
        generator: TokenGenerator,
        limiter: RateLimiter,
        clock: Clock,
        uow: UnitOfWork,
        base_url: str,
    ) -> None:
        self._repository, self._users, self._access = repository, users, access
        self._generator, self._limiter, self._clock = generator, limiter, clock
        self._uow, self._base_url = uow, base_url.rstrip("/")

    async def status(self, actor: User) -> FeedStatus:
        current = (await self._access.context(actor)).actor
        token = await self._repository.get(actor.id)
        enabled = token is not None and token.security_version == current.security_version
        return FeedStatus(
            enabled,
            token.include_titles if token and enabled else False,
            token.created_at if token and enabled else None,
        )

    async def issue(self, actor: User, *, include_titles: bool) -> IssuedFeedToken:
        current = (await self._access.context(actor, for_update=True)).actor
        secret = self._generator.new_secret()
        await self._repository.save(
            FeedToken(
                actor.id,
                self._generator.hash(secret),
                current.security_version,
                self._clock.now(),
                include_titles,
            )
        )
        await self._uow.commit()
        # Credentials belong in an authentication header, never an access-log URL.
        return IssuedFeedToken(secret, f"{self._base_url}/api/notifications/feed.atom")

    async def revoke(self, actor: User) -> None:
        await self._access.context(actor, for_update=True)
        await self._repository.revoke(actor.id)
        await self._uow.commit()

    async def read(self, secret: str, client_key: str) -> PrivateFeed:
        retry = self._limiter.hit(f"private-feed-ip:{client_key}", 60, 60)
        if retry is not None:
            raise RateLimited(retry)
        if not 32 <= len(secret) <= 256:
            raise Unauthenticated()
        digest = self._generator.hash(secret)
        retry = self._limiter.hit(f"private-feed-token:{digest}", 12, 60)
        if retry is not None:
            raise RateLimited(retry)
        token = await self._repository.find(digest)
        user = await self._users.get_by_id(token.user_id) if token else None
        if token is None or user is None or not user.is_active:
            raise Unauthenticated()
        if user.security_version != token.security_version:
            raise Unauthenticated()
        access = await self._access.context(user)
        # Administrator inspection rights never imply subscription to others' work.
        visibility = Visibility(user.id, False, tuple(access.memberships))
        rows = await self._repository.entries(visibility, limit=FEED_LIMIT + 1)
        entries = tuple(
            row
            if token.include_titles
            else replace(row, title="Alert" if row.kind == "alert" else "Subscription edition")
            for row in rows[:FEED_LIMIT]
        )
        # Re-read credential/account after the query, including immediate token rotation.
        live = await self._repository.find(digest)
        current = await self._users.get_by_id(user.id)
        if live != token or current is None or not current.is_active:
            raise Unauthenticated()
        if current.security_version != token.security_version:
            raise Unauthenticated()
        fresh_access = await self._access.context(current)
        if set(fresh_access.memberships) != set(access.memberships):
            raise Unauthenticated()
        return PrivateFeed(user.id, entries, self._clock.now(), len(rows) > FEED_LIMIT)

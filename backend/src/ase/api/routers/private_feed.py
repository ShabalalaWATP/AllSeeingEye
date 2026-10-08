"""Feed management uses the normal session; feed reading uses a separate narrow token."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ase.adapters.notify.atom import render_atom
from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_notifications import FeedEnableIn, FeedStatusOut, FeedTokenOut
from ase.api.session_fence import FenceDep
from ase.container.notifications import private_feed
from ase.domain.client_address import rate_limit_key

router = APIRouter(tags=["notifications"])
_basic = HTTPBasic(auto_error=False)
_headers = {"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"}


@router.get("/me/notifications/feed", response_model=FeedStatusOut)
async def feed_status(
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> FeedStatusOut:
    response.headers.update(_headers)
    status = await private_feed(container, session).status(actor)
    return await fence.release(FeedStatusOut.model_validate(status), session=session)


@router.post("/me/notifications/feed", response_model=FeedTokenOut)
async def enable_feed(
    body: FeedEnableIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> FeedTokenOut:
    response.headers.update(_headers)
    token = await private_feed(container, session).issue(actor, include_titles=body.include_titles)
    return await fence.release(FeedTokenOut.model_validate(token), session=session)


@router.delete("/me/notifications/feed", status_code=204)
async def revoke_feed(
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> Response:
    await private_feed(container, session).revoke(actor)
    return await fence.release(Response(status_code=204, headers=_headers), session=session)


@router.get("/notifications/feed.atom", response_class=Response)
async def read_feed(
    request: Request,
    session: SessionDep,
    container: ContainerDep,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic)],
) -> Response:
    # Basic authentication is supported by feed readers and keeps the credential out
    # of URLs, browser history, referrers, reverse-proxy and ordinary request logs.
    secret = credentials.password if credentials and credentials.username == "feed" else ""
    client_key = rate_limit_key(request.client.host if request.client else None)
    feed = await private_feed(container, session).read(secret, client_key)
    return Response(
        render_atom(feed, container.settings.public_base_url),
        media_type="application/atom+xml",
        headers=_headers,
    )

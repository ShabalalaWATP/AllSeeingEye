"""Monthly usage remains private and reports the server's UTC accounting window."""

from uuid import uuid4

from httpx import AsyncClient

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.container import Container
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from report_job_helpers import job
from test_subscription_retry_worker import _claim, _in_flight_call, _queued


async def test_monthly_usage_endpoints_scope_owner_and_subscription(
    client: AsyncClient, container: Container, user: User
) -> None:
    schedule, edition, original = await _queued(container, user)
    claimed = await _claim(container, edition.id, original.id)
    assert claimed.lease_token is not None
    await ReportJobCheckpoints(container, original.id, claimed.lease_token).mutate(
        lambda payload: payload["calls"].append(_in_flight_call() | {"profile_id": str(uuid4())})
    )
    now = container.clock.now()
    one_off = _in_flight_call() | {
        "profile_id": str(uuid4()),
        "dispatched_at": now.isoformat(),
    }
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(
            job(
                owner_id=user.id,
                created_at=now,
                updated_at=now,
                payload={"schema_version": 1, "calls": [one_off]},
            )
        )
        await session.commit()

    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    own = await client.get("/api/schedules/usage", headers=bearer(token))
    subscription = await client.get(f"/api/schedules/{schedule.id}/usage", headers=bearer(token))
    assert own.status_code == subscription.status_code == 200
    assert (
        own.headers["Cache-Control"]
        == subscription.headers["Cache-Control"]
        == ("private, no-store")
    )
    own_body, subscription_body = own.json(), subscription.json()
    assert own_body["scope"] == "owner" and own_body["subscription_id"] is None
    assert own_body["used"] == {"requests": 2, "output_tokens": 200}
    assert own_body["limit"] == {"requests": 800, "output_tokens": 24_000_000}
    assert subscription_body["scope"] == "subscription"
    assert subscription_body["subscription_id"] == str(schedule.id)
    assert subscription_body["used"] == {"requests": 1, "output_tokens": 100}
    assert subscription_body["limit"] == {"requests": 240, "output_tokens": 8_000_000}
    assert own_body["month_start"] == subscription_body["month_start"]
    assert own_body["month_end"] == subscription_body["month_end"]
    assert own_body["month_start"].startswith(now.strftime("%Y-%m-01"))

    other = await create_user(
        container, email="usage-reader@example.com", password="another-long-passphrase"
    )
    other_token = await login_token(client, other.email, "another-long-passphrase")
    other_own = await client.get("/api/schedules/usage", headers=bearer(other_token))
    other_subscription = await client.get(
        f"/api/schedules/{schedule.id}/usage", headers=bearer(other_token)
    )
    assert other_own.status_code == 200 and other_own.json()["used"]["requests"] == 0
    assert other_subscription.status_code == 404

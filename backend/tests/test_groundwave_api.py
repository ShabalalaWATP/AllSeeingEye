"""Authentication, bounded JSON and current-session recheck for native RF work."""

from unittest.mock import AsyncMock

from ase.domain.groundwave import GroundwaveSample
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

BODY = {
    "frequency_mhz": 7,
    "tx_power_w": 100,
    "tx_height_m": 2,
    "rx_height_m": 2,
    "conductivity_sm": 0.005,
    "relative_permittivity": 15,
}


async def test_groundwave_auth_validation_results_and_revoked_session(
    client, container, user, monkeypatch
):
    samples = tuple(GroundwaveSample(d, 130, 20, -80, "flat_earth") for d in (1, 200))
    calculate = AsyncMock(return_value=samples)
    monkeypatch.setattr(container.groundwave_study, "calculate", calculate)
    assert (await client.post("/api/radio/groundwave", json=BODY)).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    for body in (
        {**BODY, "sample_count": 65},
        {**BODY, "tx_height_m": 51},
        {**BODY, "frequency_mhz": True},
        {**BODY, "frequency_mhz": 50},
        {**BODY, "source_url": "http://bad.invalid"},
    ):
        assert (
            await client.post("/api/radio/groundwave", json=body, headers=headers)
        ).status_code == 422
    assert (
        await client.post(
            "/api/radio/groundwave",
            content=b" " * 4097,
            headers={**headers, "Content-Type": "application/json"},
        )
    ).status_code == 422
    assert (
        await client.post("/api/radio/groundwave", content=b"{}", headers=headers)
    ).status_code == 422
    calculate.assert_not_called()
    result = await client.post("/api/radio/groundwave", json=BODY, headers=headers)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "private, no-store"
    assert result.json()["model"] == "NTIA LFMF 1.1 (P.368-10)"
    assert len(result.json()["samples"]) == 2
    assert "not a measured or guaranteed service boundary" in result.json()["limitations"]

    async def revoke(*_args):
        async with container.session_factory() as session:
            await container.repositories(session).refresh_tokens.revoke_family(
                container.issuer.verify(token).family_id, container.clock.now()
            )
            await session.commit()
        return samples

    calculate.side_effect = revoke
    assert (
        await client.post("/api/radio/groundwave", json=BODY, headers=headers)
    ).status_code == 401

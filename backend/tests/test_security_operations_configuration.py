"""Deployment settings keep proxy trust narrow and inventory jobs advisory."""

from ipaddress import ip_address, ip_network
from pathlib import Path

import pytest
import yaml
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

ROOT = Path(__file__).resolve().parents[2]


def test_deployment_endpoint_uses_protected_settings() -> None:
    text = (ROOT / ".github/workflows/deploy.yml").read_text()
    assert "${{ secrets.VPS_HOST }}" in text and "${{ secrets.VPS_PORT }}" in text
    assert 'ssh -T -p "$SSH_PORT"' in text and '"ase@$SSH_HOST"' in text
    assert "StrictHostKeyChecking=yes" in text


def test_compose_trusts_only_reserved_caddy_address_and_reduces_capabilities() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    api, web, db = (compose["services"][name] for name in ("api", "web", "db"))
    assert api["environment"]["ASE_FORWARDED_ALLOW_IPS"] == web["networks"]["proxy"]["ipv4_address"]
    # Both addresses must be reserved before either service starts. Otherwise
    # Docker's dynamic allocator can give the API the web container's address.
    api_ip, web_ip = (
        ip_address(service["networks"]["proxy"]["ipv4_address"].split(":-", 1)[1].rstrip("}"))
        for service in (api, web)
    )
    subnet = ip_network(
        compose["networks"]["proxy"]["ipam"]["config"][0]["subnet"].split(":-", 1)[1].rstrip("}")
    )
    assert api_ip != web_ip and api_ip in subnet and web_ip in subnet
    assert api["cap_drop"] == ["ALL"] and "cap_add" not in api
    assert "no-new-privileges:true" in db["security_opt"]
    assert db["cap_drop"] == ["ALL"]
    assert set(db["cap_add"]) == {"CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"}
    assert api["stop_grace_period"] == "30s"
    dockerfile = (ROOT / "backend/Dockerfile").read_text()
    assert "ASE_FORWARDED_ALLOW_IPS:-127.0.0.1" in dockerfile
    assert "ASE_FORWARDED_ALLOW_IPS:-*" not in dockerfile
    assert "--timeout-graceful-shutdown 10" in dockerfile
    assert "ase migrate && exec uvicorn" in dockerfile


@pytest.mark.parametrize(
    "peer,expected",
    [
        ("172.30.250.2", "203.0.113.10"),
        ("172.30.250.3", "172.30.250.3"),
        ("172.25.0.9", "172.25.0.9"),
    ],
)
async def test_forged_forwarded_headers_are_ignored_from_non_caddy_peers(
    peer: str, expected: str
) -> None:
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["client"][0])

    middleware = ProxyHeadersMiddleware(app, trusted_hosts="172.30.250.2")
    scope = {
        "type": "http",
        "client": (peer, 1234),
        "headers": [(b"x-forwarded-for", b"203.0.113.10")],
        "scheme": "http",
    }
    await middleware(scope, None, None)
    assert seen == [expected]


def test_image_inventory_is_advisory_and_tied_to_commit() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/sbom.yml").read_text())
    job = workflow["jobs"]["sbom"]
    assert job["continue-on-error"] is True
    assert {item["image"] for item in job["strategy"]["matrix"]["include"]} == {"api", "web"}
    inventory = next(
        step for step in job["steps"] if "anchore/sbom-action@" in step.get("uses", "")
    )
    assert inventory["with"]["format"] == "cyclonedx-json"
    assert inventory["with"]["image"] == "ase-${{ matrix.image }}:sbom"
    artefact = next(
        step for step in job["steps"] if "actions/upload-artifact@" in step.get("uses", "")
    )
    assert "${{ github.sha }}" in artefact["with"]["name"]

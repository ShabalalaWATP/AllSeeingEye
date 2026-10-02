"""The opt-in harness must not join a host network or another caller's runner."""

from copy import deepcopy

import pytest

from proxy_test_network import isolated_runner_id, loopback_caddy_config, loopback_listener


def runner() -> dict:
    return {
        "Id": "a" * 64,
        "Config": {"Hostname": "a" * 12, "Labels": {"ase.kan153.test-runner": "true"}},
        "HostConfig": {"NetworkMode": "none", "PortBindings": {}},
        "NetworkSettings": {"Networks": {"none": {}}},
        "State": {"Running": True},
    }


def test_only_current_owned_network_disabled_runner_is_accepted() -> None:
    details = runner()
    assert isolated_runner_id(details, "a" * 12) == "a" * 64
    for changed in (
        {"HostConfig": {"NetworkMode": "host"}},
        {"HostConfig": {"NetworkMode": "bridge"}},
        {"HostConfig": {"NetworkMode": "none", "PortBindings": {"8080/tcp": [{}]}}},
        {"NetworkSettings": {"Networks": {"none": {}, "another-network": {}}}},
        {"Config": {"Hostname": "a" * 12, "Labels": {}}},
        {"State": {"Running": False}},
        {"Id": "b" * 64},
    ):
        invalid = deepcopy(details)
        invalid.update(changed)
        with pytest.raises(ValueError, match="network-disabled"):
            isolated_runner_id(invalid, "a" * 12)
    with pytest.raises(ValueError, match="network-disabled"):
        isolated_runner_id(details, "native-host")


def test_real_listener_is_loopback_only() -> None:
    with loopback_listener() as listener:
        assert listener.getsockname()[0] == "127.0.0.1"
        assert listener.getsockname()[1] > 0


def test_caddy_fixture_preserves_policy_and_disables_other_listeners() -> None:
    source = (
        "{$ASE_SITE_ADDRESS:localhost} {\n"
        "request_body { max_size 65536 }\nreverse_proxy api:8000\n}"
    )
    result = loopback_caddy_config(source, 12345)
    assert "bind 127.0.0.1" in result
    assert "admin off" in result and "auto_https off" in result
    assert "request_body { max_size 65536 }" in result
    assert "reverse_proxy 127.0.0.1:12345" in result
    with pytest.raises(ValueError, match="Review changed"):
        loopback_caddy_config(source.replace("api:8000", "other:8000"), 12345)

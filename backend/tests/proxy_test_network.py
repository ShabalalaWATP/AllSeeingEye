"""Loopback-only namespace contract for the optional real-Caddy upload test."""

import re
import socket
from typing import Any


def isolated_runner_id(details: dict[str, Any], hostname: str) -> str:
    """Only join the labelled, network-disabled container running this pytest process."""
    identifier = details.get("Id", "")
    config = details.get("Config", {})
    host = details.get("HostConfig", {})
    if (
        not isinstance(identifier, str)
        or re.fullmatch(r"[0-9a-f]{64}", identifier) is None
        or hostname != identifier[:12]
        or config.get("Hostname") != hostname
        or (config.get("Labels") or {}).get("ase.kan153.test-runner") != "true"
        or host.get("NetworkMode") != "none"
        or host.get("PortBindings")
        or set(details.get("NetworkSettings", {}).get("Networks", {})) != {"none"}
        or not details.get("State", {}).get("Running")
    ):
        raise ValueError("Caddy requires this labelled, network-disabled Linux test container.")
    return identifier


def loopback_listener() -> socket.socket:
    listener = socket.socket()
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
    except BaseException:
        listener.close()
        raise
    return listener


def loopback_caddy_config(source: str, api_port: int) -> str:
    """Retain production request policy; change only listeners and the local upstream."""
    site = "{$ASE_SITE_ADDRESS:localhost} {"
    upstream = "reverse_proxy api:8000"
    if source.count(site) != 1 or source.count(upstream) != 1:
        raise ValueError("Review changed production Caddy listeners before running this fixture.")
    return "{\n\tadmin off\n\tauto_https off\n}\n" + source.replace(
        site, site + "\n\tbind 127.0.0.1"
    ).replace(upstream, f"reverse_proxy 127.0.0.1:{api_port}")

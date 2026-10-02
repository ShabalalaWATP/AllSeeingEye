"""Cancellation must settle a create and clean only the identified private sidecar."""

import asyncio
import json
from pathlib import Path

import pytest

import proxy_test_docker as commands

NAMESPACE = "a" * 64
CONTAINER = "b" * 64


class Process:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.finished = asyncio.Event()
        self.returncode = None
        self.killed = False
        self.reaped = False

    async def communicate(self):
        self.started.set()
        await self.finished.wait()
        self.reaped = True
        if self.returncode is None:
            self.returncode = 0
        return CONTAINER.encode(), b""

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9
        self.finished.set()


async def test_cancelled_command_waits_for_acknowledgement(monkeypatch) -> None:
    process = Process()

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    task = asyncio.create_task(commands.docker("create"))
    await process.started.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    process.finished.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.reaped and not process.killed


async def test_timed_out_command_is_killed_and_reaped(monkeypatch) -> None:
    process = Process()

    async def create(*args, **kwargs):
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    with pytest.raises(TimeoutError):
        await commands.docker("create", timeout=0.01)
    assert process.killed and process.reaped


@pytest.mark.parametrize("foreign", [False, True])
async def test_unacknowledged_create_reconciles_exact_ownership(monkeypatch, foreign) -> None:
    calls = []
    token = None

    async def docker(*args):
        nonlocal token
        calls.append(args)
        if args[0] == "create":
            token = next(
                arg.split("=", 1)[1] for arg in args if arg.startswith("ase.kan153.fixture=")
            )
            raise asyncio.CancelledError
        if args[0] == "ps":
            assert args[-1] == f"label=ase.kan153.fixture={token}"
            return CONTAINER
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Id": CONTAINER,
                        "Config": {
                            "Labels": {
                                "ase.kan153.fixture": token,
                                "ase.kan153.runner": "other" if foreign else NAMESPACE,
                            }
                        },
                        "HostConfig": {"NetworkMode": f"container:{NAMESPACE}"},
                    }
                ]
            )
        return ""

    monkeypatch.setattr(commands, "docker", docker)
    expected = ValueError if foreign else asyncio.CancelledError
    with pytest.raises(expected):
        async with commands.owned_proxy(NAMESPACE, "pinned-image", 12345, Path("fixture")):
            pytest.fail("A cancelled create must not yield the fixture.")
    removals = [call for call in calls if call[0] == "rm"]
    assert removals == ([] if foreign else [("rm", "-f", "-v", CONTAINER)])

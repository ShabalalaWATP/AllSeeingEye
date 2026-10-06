"""Bound one Linux child session and retain its acknowledgement and cleanup."""

import json
import os
import signal
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


def dump(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def utc() -> str:
    return datetime.now(UTC).isoformat()


def clean_env(home: Path, temporary: Path, node: Path) -> dict[str, str]:
    """No inherited tokens, provider settings, proxies, CI flags or Node options."""
    home.mkdir(parents=True, exist_ok=False)
    temporary.mkdir(parents=True, exist_ok=False)
    return {
        "PATH": f"{node.parent}:/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(temporary),
        "LANG": "C.UTF-8",
        "TZ": "UTC",
        "NO_COLOR": "1",
    }


def exited_without_reaping(pid: int) -> bool:
    # Retain the leader's PID until group cleanup, preventing PID reuse races.
    return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None


def signal_group(pid: int, kind: int) -> None:
    try:
        os.killpg(pid, kind)
    except ProcessLookupError:
        pass


def group_present(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


def run_owned(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    output: Path,
    name: str,
    seconds: int,
) -> dict:
    """No shell/retry. A fresh session owns only the invoked child process group."""
    receipt = {"command": command, "started": utc(), "exit": None, "completed": False}
    process = None
    started = time.monotonic()
    failure = None
    try:
        with (output / f"{name}.log").open("xb") as log:
            pending = []
            handlers = {}

            def defer(signum, _frame):
                if not pending:
                    pending.append(signum)

            # Do not block signals: an inherited mask could prevent Node shutdown.
            # Catch them briefly until the returned child's group is registered.
            try:
                for kind in (signal.SIGTERM, signal.SIGINT):
                    handlers[kind] = signal.signal(kind, defer)
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                receipt["pid"] = process.pid
            finally:
                for kind, handler in handlers.items():
                    signal.signal(kind, handler)
                receipt["deferredSignals"] = pending
            if pending:
                raise InterruptedError("Interrupted during owned child creation")
            while not exited_without_reaping(process.pid):
                if time.monotonic() - started >= seconds:
                    raise TimeoutError(name)
                time.sleep(0.05)
    except BaseException as error:  # noqa: BLE001 - acknowledge/clean, then re-raise.
        failure = error
        receipt["failureClass"] = type(error).__name__
    finally:
        receipt["commandFinished"] = utc()
        receipt["commandSeconds"] = time.monotonic() - started
        try:
            if process is not None:
                # Clean remaining group members even after a successful leader exit.
                cleanup_deadline = time.monotonic() + 15
                signal_group(process.pid, signal.SIGTERM)
                deadline = time.monotonic() + 10
                while (
                    not exited_without_reaping(process.pid)
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.05)
                signal_group(process.pid, signal.SIGKILL)
                receipt["exit"] = process.wait(
                    timeout=max(0.01, cleanup_deadline - time.monotonic())
                )
                while (
                    group_present(process.pid) and time.monotonic() < cleanup_deadline
                ):
                    time.sleep(0.05)
                receipt["groupAbsent"] = not group_present(process.pid)
                if not receipt["groupAbsent"]:
                    raise RuntimeError("Owned process group remained")
            else:
                receipt["groupAbsent"] = True
        except BaseException as error:  # noqa: BLE001 - retain cleanup failure and re-raise.
            receipt["cleanupFailureClass"] = type(error).__name__
            if failure is None:
                failure = error
        receipt["finished"] = utc()
        receipt["completed"] = failure is None and receipt["exit"] == 0
        dump(output / f"{name}-receipt.json", receipt)
    if failure is not None:
        raise failure
    if not receipt["completed"]:
        raise RuntimeError(f"{name} failed")
    return receipt

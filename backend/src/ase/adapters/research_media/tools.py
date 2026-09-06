"""Fixed local executables with deadlines and bounded stdout inside the isolated worker."""

import os
import subprocess  # nosec B404
import threading
import time
from pathlib import Path

from ase.adapters.research_imports.models import ImportRejected


def trusted_tool(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute() or path.name.lower() not in {name, f"{name}.exe"}:
        raise ImportRejected("Media runtime must be an explicitly configured trusted executable.")
    if not path.is_file():
        return None
    return str(path.resolve())


def run_tool(argv: list[str], deadline: float, *, max_output: int = 256_000) -> bytes:
    """Never use a shell. The outer worker must kill this process's descendants on cancellation."""
    remaining = min(10.0, deadline - time.monotonic())
    if remaining <= 0:
        raise ImportRejected("Media processing exceeded its time limit.")
    environment = {
        "OMP_THREAD_LIMIT": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    }
    for key in ("SystemRoot", "WINDIR"):
        if key in os.environ:
            environment[key] = os.environ[key]
    try:
        process = subprocess.Popen(  # noqa: S603  # nosec B603
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except OSError:
        raise ImportRejected("The configured media runtime could not be started.") from None
    output = bytearray()
    exceeded = threading.Event()

    def read() -> None:
        if process.stdout is None:
            return
        while block := process.stdout.read(8192):
            if len(output) + len(block) > max_output:
                exceeded.set()
                process.kill()
                return
            output.extend(block)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        process.wait(timeout=remaining)
        reader.join(timeout=1)
        if exceeded.is_set():
            raise ImportRejected("Media runtime output exceeds its limit.")
        if process.returncode or reader.is_alive():
            raise ImportRejected("Media processing failed or the format is unsupported.")
        return bytes(output)
    except subprocess.TimeoutExpired:
        raise ImportRejected("Media processing exceeded its time limit.") from None
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        reader.join(timeout=1)
        if process.stdout is not None:
            process.stdout.close()

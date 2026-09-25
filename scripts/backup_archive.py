"""Encrypted archives, retention, status and alerts for scheduled backups.

Host-side and standard library only, like the other backup scripts. GnuPG performs
symmetric AES-256 encryption with a passphrase file that stays outside the backup tree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tarfile
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from backup_bundle import BackupError

ARCHIVE = re.compile(r"^scheduled-\d{8}T\d{6}Z\.tar\.gpg$")
BUNDLE = re.compile(r"^scheduled-\d{8}T\d{6}Z$")
OFFSITE = re.compile(r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[A-Za-z0-9._/-]*$")
MIN_KEEP = 3
GPG_TIMEOUT = 600
# No agent passphrase cache: the key file is the only place the passphrase lives.
GPG = ("gpg", "--batch", "--quiet", "--no-tty", "--pinentry-mode", "loopback")
GPG_KEY = ("--no-symkey-cache", "--passphrase-file")


def archive_name(now: datetime) -> str:
    return now.astimezone(UTC).strftime("scheduled-%Y%m%dT%H%M%SZ")


def archives(root: Path) -> list[Path]:
    """Scheduled archives in time order; any other file is never listed or pruned."""
    return sorted(
        path
        for path in root.iterdir()
        if ARCHIVE.fullmatch(path.name) and path.is_file() and not path.is_symlink()
    )


def encryption_key(path: Path) -> Path:
    """Refuse a missing, linked, short or group- or world-readable passphrase file."""
    if path.is_symlink() or not path.is_file():
        raise BackupError("Backup encryption key must be a regular file.")
    info = path.stat()
    if os.name == "posix" and info.st_mode & 0o077:
        raise BackupError("Backup encryption key must be readable by its owner only.")
    if not 32 <= info.st_size <= 4_096:
        raise BackupError("Backup encryption key must contain 32 to 4096 bytes.")
    return path


def sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def pack(bundle: Path, tar_path: Path) -> str:
    """Tar one verified bundle directory (uncompressed) and return its SHA-256."""
    with tarfile.open(tar_path, "x") as archive:
        archive.add(bundle, arcname=bundle.name)
    tar_path.chmod(0o600)
    return sha256(tar_path)


def encrypt(tar_path: Path, key: Path, output: Path) -> None:
    subprocess.run(
        [
            *GPG,
            *GPG_KEY,
            str(key),
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "--s2k-mode",
            "3",
            "--s2k-digest-algo",
            "SHA512",
            "--s2k-count",
            "65011712",
            "--output",
            str(output),
            str(tar_path),
        ],
        check=True,
        capture_output=True,
        timeout=GPG_TIMEOUT,
    )
    output.chmod(0o600)


def decrypt(archive: Path, key: Path, tar_path: Path) -> None:
    subprocess.run(
        [
            *GPG,
            *GPG_KEY,
            str(key),
            "--output",
            str(tar_path),
            "--decrypt",
            str(archive),
        ],
        check=True,
        capture_output=True,
        timeout=GPG_TIMEOUT,
    )
    tar_path.chmod(0o600)


def decrypted_sha256(archive: Path, key: Path) -> str:
    """Decrypt to memory in blocks and hash, proving the archive opens with the key."""
    hasher = hashlib.sha256()
    command = [*GPG, *GPG_KEY, str(key), "--decrypt", str(archive)]
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    ) as process:
        stream = process.stdout
        assert stream is not None
        for block in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(block)
        if process.wait(timeout=GPG_TIMEOUT) != 0:
            raise BackupError("The encrypted archive could not be decrypted.")
    return hasher.hexdigest()


def extract(tar_path: Path, destination: Path) -> Path:
    """Extract exactly one scheduled bundle directory; links, devices and traversal fail."""
    with tarfile.open(tar_path) as archive:
        members = archive.getmembers()
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        if len(roots) != 1 or not BUNDLE.fullmatch(next(iter(roots))):
            raise BackupError(
                "Archive must hold exactly one scheduled backup directory."
            )
        if any(not (member.isfile() or member.isdir()) for member in members):
            raise BackupError("Archive may contain only regular files and directories.")
        try:
            archive.extractall(destination, filter="data")
        except tarfile.TarError as exc:
            raise BackupError("Archive contents failed safe extraction.") from exc
    return destination / roots.pop()


def prune(root: Path, keep: int) -> list[str]:
    """Delete the oldest scheduled archives beyond `keep`; nothing else is touched."""
    if keep < MIN_KEEP:
        raise BackupError(f"Keep at least {MIN_KEEP} scheduled archives.")
    doomed = archives(root)[:-keep]
    for path in doomed:
        path.unlink()
    return [path.name for path in doomed]


def push_offsite(archive: Path, destination: str, port: int) -> None:
    """Copy one archive to user@host:path over SSH; the remote side is never pruned."""
    if not OFFSITE.fullmatch(destination) or not 1 <= port <= 65_535:
        raise BackupError("Off-site destination must look like user@host:path.")
    subprocess.run(
        [
            "rsync",
            "--times",
            "--chmod=F600",
            "--timeout=120",
            "-e",
            f"ssh -p {port} -o BatchMode=yes",
            "--",
            str(archive),
            destination.rstrip("/") + "/",
        ],
        check=True,
        capture_output=True,
        timeout=1_800,
    )


def read_status(root: Path) -> dict[str, object]:
    try:
        status = json.loads((root / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return status if isinstance(status, dict) else {}


def write_status(root: Path, status: dict[str, object]) -> None:
    temporary = root / ".status.json.tmp"
    temporary.write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.chmod(0o600)
    os.replace(temporary, root / "status.json")


def heartbeat_url(value: str | None) -> str | None:
    if not value:
        return None
    parts = urllib.parse.urlsplit(value)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.fragment
    ):
        raise BackupError("Heartbeat URL must be a plain https URL.")
    return value.rstrip("/")


def ping(url: str | None, *, failed: bool) -> bool:
    """Best effort: an unreachable monitor must never fail or block a backup."""
    if url is None:
        return True
    try:
        with urllib.request.urlopen(url + ("/fail" if failed else ""), timeout=10):
            return True
    except (OSError, ValueError):
        return False

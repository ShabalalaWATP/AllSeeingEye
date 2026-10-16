"""Filesystem boundaries, including real hard links and POSIX permission checks."""

import os
from pathlib import Path

import pytest

from ase.adapters.security.recovery_files import safe_file
from ase.cli_recovery import open_journal
from ase.domain.errors import Conflict
from recovery_helpers import journal as journal  # noqa: PLC0414


def test_hardlinked_key_is_rejected(journal, tmp_path):
    os.link(journal.key, tmp_path / "second-key-link")
    with pytest.raises(Conflict, match="unlinked"):
        journal.inspect()


def test_link_in_any_ancestor_is_rejected(journal, monkeypatch):
    original = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path == journal.path.parent or original(path)
    )
    with pytest.raises(Conflict, match="links or junctions"):
        journal.inspect()


def test_junction_in_any_ancestor_is_rejected(journal, monkeypatch):
    original = Path.is_junction
    monkeypatch.setattr(
        Path, "is_junction", lambda path: path == journal.key.parent or original(path)
    )
    with pytest.raises(Conflict, match="links or junctions"):
        journal.inspect()


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX ownership/modes; Windows requires operator DACL provisioning"
)
@pytest.mark.parametrize("target", ["file", "directory"])
def test_group_readable_files_and_directories_are_rejected(journal, target):
    path = journal.key if target == "file" else journal.key.parent
    path.chmod(0o640 if target == "file" else 0o750)
    with pytest.raises(Conflict, match="only to their owner"):
        journal.inspect()


@pytest.mark.skipif(os.name == "nt", reason="POSIX owner IDs")
def test_non_owned_directory_is_rejected(journal, monkeypatch):
    original = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: original + 1)
    with pytest.raises(Conflict, match="belong to the executing operator"):
        safe_file(journal.path)


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX symlinks, no Windows developer privilege required"
)
def test_real_symlink_is_rejected(journal, tmp_path):
    link = tmp_path / "linked-key"
    link.symlink_to(journal.key)
    with pytest.raises(Conflict, match="links or junctions"):
        safe_file(link)


@pytest.mark.skipif(os.name != "nt", reason="Windows namespace and alternate stream aliases")
@pytest.mark.parametrize(
    "kind", ["extended_repo", "extended_database", "device", "stream", "trailing_dot"]
)
def test_windows_aliases_cannot_bypass_private_path_checks(journal, kind):
    repository = Path(__file__).resolve().parents[2]
    if kind == "extended_repo":
        path = Path("\\\\?\\" + str(repository / "unsafe-journal"))
    elif kind == "extended_database":
        path = Path("\\\\?\\" + str(journal.path))
    elif kind == "device":
        path = Path("\\\\.\\" + str(journal.path))
    elif kind == "stream":
        path = Path(str(journal.path) + ":alternate")
    else:
        path = Path(str(journal.path) + ".")
    with pytest.raises(Conflict, match="ordinary local paths"):
        open_journal(path, journal.key, f"sqlite+aiosqlite:///{journal.path.parent / 'data.db'}")

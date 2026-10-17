"""Isolated external history, separate from each disposable database directory."""

import pytest

from ase.adapters.security.recovery_journal import FileRecoveryJournal


@pytest.fixture
def journal(tmp_path_factory):
    directory = tmp_path_factory.mktemp("external-recovery")
    key_directory = tmp_path_factory.mktemp("external-recovery-key")
    directory.chmod(0o700)
    key_directory.chmod(0o700)
    value = FileRecoveryJournal(directory / "journal.fernet", key_directory / "key")
    value.initialise()
    return value

"""Offline, transactional rotation of every persisted application-encrypted field."""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import MetaData, Table, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from ase.adapters.security.cipher import CipherUnavailable, FernetCipher

# Deliberately explicit: additions of encrypted storage require inventory review.
ENCRYPTED_COLUMNS = {
    "llm_profiles": ("api_key_encrypted",),
    "admin_totp": ("secret_encrypted", "pending_encrypted"),
    "mfa_challenges": ("pending_encrypted",),
    "firms_credentials": ("active_encrypted", "draft_encrypted"),
    "acled_credentials": ("refresh_token_encrypted",),
    "alert_webhook_destinations": ("url_encrypted",),
    "web_push_devices": ("encrypted_subscription",),
}


async def rotate_encryption_key(engine: AsyncEngine, old_key: str, new_key: str) -> int:
    """Preflight all ciphertext, then replace it atomically without changing metadata.

    The operator must stop API and workers first. Database locks cover this
    transaction, not the later external configuration change or service restart.
    Exceptions propagate to the CLI, which emits only a non-secret failure message.
    """
    old, new = FernetCipher(old_key), FernetCipher(new_key)
    if not old.available or not new.available or old_key.strip() == new_key.strip():
        raise CipherUnavailable("Two distinct usable keys are required.")
    async with engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            await connection.exec_driver_sql("BEGIN IMMEDIATE")
        elif connection.dialect.name == "postgresql":
            # Fixed inventory, never identifiers supplied by a caller.
            await connection.exec_driver_sql(
                "LOCK TABLE llm_profiles, admin_totp, mfa_challenges, firms_credentials, "
                "acled_credentials, alert_webhook_destinations, web_push_devices "
                "IN ACCESS EXCLUSIVE MODE"
            )
        else:
            raise ValueError("Unsupported rotation database.")
        metadata = MetaData()
        await connection.run_sync(lambda sync: metadata.reflect(sync, only=list(ENCRYPTED_COLUMNS)))
        replacements: list[tuple[Table, dict[str, object], dict[str, str]]] = []
        count = 0
        for name, columns in ENCRYPTED_COLUMNS.items():
            table = metadata.tables[name]
            if not table.primary_key.columns or any(column not in table.c for column in columns):
                raise ValueError("The selected database does not match the credential inventory.")
            for row in (await connection.execute(select(table))).mappings():
                values = _reencrypt(dict(row), table, columns, old, new)
                if values:
                    keys = {column.name: row[column.name] for column in table.primary_key.columns}
                    replacements.append((table, keys, values))
                    count += len(values)
        # No writes until every non-null value has decrypted and re-encrypted.
        for table, keys, values in replacements:
            statement = update(table).where(
                *(table.c[name] == value for name, value in keys.items())
            )
            await connection.execute(statement.values(**values))
        return count


def _reencrypt(
    row: Mapping[str, object],
    table: Table,
    columns: tuple[str, ...],
    old: FernetCipher,
    new: FernetCipher,
) -> dict[str, str]:
    values: dict[str, str] = {}
    for column in columns:
        value = row[column]
        if value is None:
            if not table.c[column].nullable:
                raise CipherUnavailable()
            continue
        if not isinstance(value, str):
            raise CipherUnavailable()
        values[column] = new.encrypt(old.decrypt(value))
    return values

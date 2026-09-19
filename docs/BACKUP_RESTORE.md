# Backup and restore

The operator scripts use Python 3.12 or newer and its standard library. Run the
commands below from `C:\AlexDev\OSINT`. SQLite needs no running service. PostgreSQL
uses the existing Compose `db` service and the PostgreSQL tools inside its image.

## What is preserved

Every bundle includes the durable database: accounts, configuration, report
versions, frozen evidence, audit records and the small aggregate tables. The live
event cache is never copied or persisted by these scripts.

Configuration files are kept separately under `config/`: `.env.example`,
`docker-compose.yml`, `infra/Caddyfile` and the packaged social, aviation and
conflict watch files, when present. An explicitly selected Compose file is saved
as `config/docker-compose.yml`. Custom files outside this list, runtime
environment variables, Caddy certificates, container images and source code are
not included. Keep the matching Git revision and deployment-specific files with
your recovery records.

The real project `.env` is excluded unless `--include-secrets` is supplied. That
flag copies it **in plaintext**. Without it, preserve `ASE_ENCRYPTION_KEY` separately
in your existing secret storage: changing or losing the key prevents decryption
of saved LLM credentials and enrolled TOTP secrets. The database itself contains
private account data and encrypted credentials, so even a default backup belongs
in private, preferably encrypted storage. File modes are restricted on Unix;
Windows uses the destination directory's inherited ACLs.

## SQLite backup

Create a private backup parent folder once. Each run requires a fresh child name:

```powershell
New-Item -ItemType Directory -Path C:\AlexDev\OSINT\data\backups -Force
python scripts/backup.py sqlite --database data/ase.db --output data/backups/sqlite-20260905-180000
python scripts/restore.py data/backups/sqlite-20260905-180000 --verify-only
```

Use the actual SQLite file configured for your API. A relative database URL is
resolved from the API process's working directory. For an API started in
`backend/`, the default usually points to `backend/data/ase.db`; use that path in
`--database` instead. The script never creates a missing source database.

SQLite's online backup API captures committed WAL data consistently while the API
runs. The result is a standalone `database.sqlite3` with an integrity check and no
WAL or shared-memory sidecars. Snapshot work has a 60-second budget. A busy or
oversized database fails the run rather than producing a reported success.

To include a project `.env` deliberately:

```powershell
python scripts/backup.py sqlite --database data/ase.db --output data/backups/sqlite-private-20260905-180000 --include-secrets
```

`--project-root` selects the configuration root, defaulting to this repository.
The environment file must exist there when `--include-secrets` is used. Secrets
provided only through process environment variables are never exported.

## Restore to a new SQLite destination

```powershell
python scripts/restore.py data/backups/sqlite-20260905-180000 --output data/recovery-20260905-180000
```

The database appears at `data/recovery-20260905-180000/database.sqlite3` and the
configuration appears under its `config/` directory. All bundle hashes, sizes,
paths and the SQLite integrity check must pass before this destination is
created. There is no overwrite flag: an existing file or directory is refused.
Services, the live database and the active `.env` are unchanged.

Inspect the restored database and compare its reports and evidence with the
expected recovery point before selecting it in the API configuration. Switching
the running application to a recovered database is a separate, deliberate
operator action. Restore the original encryption key before testing encrypted
credentials or TOTP. Use a compatible application revision and review migration
requirements before starting it.

## PostgreSQL Compose backup and recovery

Create a random authentication key once and keep it outside the repository, `.env`
and backup tree. Store a separate protected recovery copy:

```powershell
python -c "import secrets; open(r'C:\\secure\\ase-backup-auth.key', 'wb').write(secrets.token_bytes(32))"
```

The key file must contain between 32 and 4,096 bytes. Do not regenerate it for each
backup, because every authenticated restore needs the same key used at backup time.

```powershell
python scripts/backup.py postgres --authentication-key-file C:\secure\ase-backup-auth.key --output data/backups/postgres-20260905-180000
python scripts/restore.py data/backups/postgres-20260905-180000 --authentication-key-file C:\secure\ase-backup-auth.key --verify-only
python scripts/restore.py data/backups/postgres-20260905-180000 --authentication-key-file C:\secure\ase-backup-auth.key --output data/pg-recovery-20260905-180000 --target-database ase_restore_20260905
```

The final command creates a **new** database in the Compose server. It leaves the
configured application database untouched. `createdb` refuses an existing name;
the configured database, `postgres`, `template0` and `template1` are refused in
advance. Simple PostgreSQL identifiers of up to 63 characters are supported.

The script reads `POSTGRES_USER` and `POSTGRES_DB` inside the `db` container.
`pg_dump` produces a custom-format dump without ownership or ACL replay.
`pg_restore --list` checks the dump catalogue before `createdb`; restore uses
`--single-transaction --exit-on-error`, never `--clean` or `DROP`. Passwords are
never command arguments, prompted for, or printed. Commands use the container's
local socket authentication and each has a ten-minute timeout. If that
authentication has been changed, configure a protected PostgreSQL password file
inside the container before use. Do not add a password to the CLI.

Both commands accept `--compose-file C:/path/to/docker-compose.yml`. The matching
Compose configuration must be available, its `db` service running, and the role
must be allowed to read the source and create the recovery database. Host
PostgreSQL tools and a published PostgreSQL port are unnecessary.

The output directory keeps the recovered configuration and a checked copy of
`database.dump`. A failed restore can leave that directory and an empty new
PostgreSQL database; neither is removed automatically. Inspect the failure and
choose fresh targets for a retry. An actual PostgreSQL restore drill requires a
running database and is separate from the offline tests described below.

## Verification and retention

`manifest.json` records the format, database type, presence of `.env`, each
member's size and SHA-256 digest. PostgreSQL backup also writes `manifest.hmac`,
an HMAC-SHA256 over the exact manifest bytes. An active PostgreSQL restore requires
the independent key and verifies the HMAC before copying files or invoking Docker.
Verification has a 2 GiB total limit, a 1 MiB
limit per configuration file and a 64 KiB manifest limit. Only known file names
are accepted. Symbolic links, junctions, traversal paths, duplicate members,
unexpected directories and unlisted files are refused. The directory format
requires no archive extraction or decompression. A failed backup can leave
partial output; only an exit status of zero and a passing `--verify-only` check
constitute a usable bundle.

Hashes detect accidental damage and mismatched files. The PostgreSQL HMAC also
detects a replaced file plus a rewritten manifest unless the attacker has the
independent authentication key. A PostgreSQL `--verify-only` command without a key
performs integrity checks only and says so; it does not authenticate the bundle.
Full restore compatibility is checked with the database tools during an actual drill.

These scripts do not install a schedule, prune backups or remove old data. For a
nightly operator-scheduled run, use a distinct UTC timestamp in the output name,
check the exit status, and periodically perform a restore drill. A practical
retention policy is seven daily and four weekly verified bundles, with a copy on
another private device. Review available space and remove older bundles manually
only after a newer recovery point has been verified. A failed dump may leave a
partial file, so monitor free disk space as well as exit status.

## Offline restore drill

The deterministic test drill creates a temporary SQLite database with reports,
frozen evidence and configuration, commits a second report into WAL, takes a
snapshot, then changes the source and restores to a fresh temporary destination.
It compares the recovered rows and checks that existing targets, corrupt files,
unsafe paths and unexpected configuration cannot be restored. PostgreSQL tests
mock subprocesses and assert the complete safe command sequence and failure
behaviour. They do not connect to Docker or any database service.

```powershell
uv run --project backend pytest backend/tests/test_backup_restore.py backend/tests/test_backup_postgres.py --no-cov
python scripts/backup.py --help
python scripts/restore.py --help
```

The tests use pytest temporary directories and never read or restore `data/ase.db`.
The normal full backend suite also includes this drill.

An earlier real recovery drill passed on 6 September 2026 using fresh SQLite
and a separate `postgres:17-alpine` Compose project, bound only to
`127.0.0.1:15440` with tmpfs storage and synthetic trust-authenticated data. Both
databases migrated to `0001`, retained a seeded account through `0001` to head
`0011`, and then exercised the then-current `backup.py`, `restore.py --verify-only` and
fresh-target restore commands. Logical hashes matched across all 19 tables
(including Alembic state), before/after recovery and between SQLite/PostgreSQL.
The checks read both report versions and their frozen evidence, decrypted the
restored model credential and TOTP secret with the separately held test key, and
verified the saved vector, aggregate, audit record and revoked-family marker.
Source databases were unchanged and `.env` remained excluded. The labelled QA
container and its network were verified and removed; no application service,
user database or user `.env` was read or changed. Local evidence is retained in
the ignored `data/phase6-backup-qa/run-20260906-15440/results.json`. This verifies
a disposable PostgreSQL 17 recovery, not the deployed PostgreSQL 16/PostGIS stack,
its storage permissions, the later manifest-HMAC requirement or an observed CI run.

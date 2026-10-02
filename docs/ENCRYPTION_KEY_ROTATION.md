# Application encryption-key rotation

The `ase rotate-encryption-key` command re-encrypts saved LLM provider keys,
active and pending authenticator secrets, pending MFA enrolment challenges,
active and draft FIRMS keys, persisted ACLED refresh tokens, alert webhook URLs
and browser push credentials in one database transaction. It covers nine
encrypted fields across seven tables and preserves non-secret metadata and
nullable fields. It does not replace provider-issued credentials or alter the
encryption format.

| Table | Encrypted fields |
| --- | --- |
| `llm_profiles` | `api_key_encrypted` |
| `admin_totp` | `secret_encrypted`, `pending_encrypted` |
| `mfa_challenges` | `pending_encrypted` |
| `firms_credentials` | `active_encrypted`, `draft_encrypted` |
| `acled_credentials` | `refresh_token_encrypted` |
| `alert_webhook_destinations` | `url_encrypted` |
| `web_push_devices` | `encrypted_subscription` (endpoint, public key and auth secret) |

## Maintenance procedure

1. Schedule downtime and stop every API and worker process using this database.
   Prevent automatic restarts and deployments during the maintenance window.
2. Follow [backup and restore](BACKUP_RESTORE.md) to create and verify a database
   backup. Preserve the old application key separately and label the backup with
   its matching key version. Rehearse recovery to a fresh destination.
3. Generate a replacement using the CSPRNG instructions in [Setup](SETUP.md).
   Write the existing and replacement values into separate protected local files.
   On POSIX, use owner-only permissions (`chmod 600`); on Windows restrict each
   file's ACL to the operator. Symlinks, directories and files above 4 KiB are
   rejected. Never put key values in command arguments or shell history.
4. Explicitly select the intended database using `ASE_DATABASE_URL` in the
   protected process environment. From `backend`, run:

   ```text
   uv run ase rotate-encryption-key --old-key-file /protected/old-key --new-key-file /protected/new-key --maintenance-confirmed
   ```

   The command checks every affected non-null value before writes. An incorrect
   old key, malformed value or failed update rolls back the whole transaction.
   It reports only the number of rotated values. SQLite must already exist;
   PostgreSQL locks the seven affected tables until the transaction completes.
5. After success, change `ASE_ENCRYPTION_KEY` in the operator's protected
   configuration to the new value. The database transaction and external
   configuration update are **not atomic**. Keep processes stopped between them.
6. Restart, verify MFA sign-in and pending enrolment, then check saved provider
   reads and active/draft FIRMS selection. Confirm ACLED refresh still uses the
   existing environment fingerprint. Check that webhook destinations and browser
   push subscriptions still decrypt with their existing ownership, session and
   delivery metadata. The VAPID signing key remains separate operator configuration.
   A software test cannot prove live provider connectivity or the operator's
   recovery process.
7. Take and verify a new backup, labelled with the replacement key version.
   Retain old backups and matching recovery keys until the backup policy permits
   their disposal. Never discard an old key solely because rotation succeeded.

## Failure and recovery

Validation and update failures roll back credential replacements. A connection
failure during commit can leave the outcome uncertain. Resolve database/key-file problems
without sharing plaintext or ciphertext in logs, tickets or support messages.
After an uncertain interruption, do not guess which key applies. Keep services
stopped, preserve the current database, and investigate on a disposable copy.

If restart or validation after successful rotation fails, either repair the new
configuration or restore the **matching pre-rotation database backup and old key**
together under the documented restore procedure. An old key with the rotated
database, or a new key with the old backup, cannot decrypt the stored credentials.
No operator credentials or production database were rotated during implementation.

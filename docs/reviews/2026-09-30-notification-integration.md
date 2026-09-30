# Notification integration, KAN-110, KAN-112 and KAN-113

The notification stack was checked after integrating the architecture and security
branches at `c4a14f82`. No operator credentials, live services or production data
were used. This review covers the encryption inventory and actual subscription
publication hook, rather than repeating the transport reviews.

## Encryption-key rotation

KAN-112 webhook destinations store `alert_webhook_destinations.url_encrypted`.
KAN-113 browser devices store `web_push_devices.encrypted_subscription`. Both now
belong to the KAN-17 rotation inventory and the fixed PostgreSQL table-lock list.
The inventory includes nine encrypted fields across seven tables and recognises
both `_encrypted` suffixes and `encrypted_` prefixes.

Real model fixtures prove that all nine replacements preserve plaintext and every
other column, decrypt under the replacement key and reject the previous key.
The push adapter also decodes the rotated subscription successfully. Synthetic
table checks cover nullable values and transaction rollback on invalid keys,
malformed ciphertext and an injected update failure. The operator procedure lists
both consumers and distinguishes the separately configured VAPID signing key.

## Publication and independent recipient preferences

The public edition publisher calls the commit-free persistence projection, which
enqueues only after the current schedule accepts the completed edition. Mail
intents share the edition transaction. Replay uses the existing unique delivery
identity. Disabled, archived or definition-mismatched subscriptions retain edition
history without changing the active projection or creating user mail.

A behaviour regression first reproduced missing material-change email when the
recipient selected that policy and in-app change alerts were disabled. Change
comparison previously returned early on the in-app setting alone. Comparison now
also runs for an explicit material-email preference; in-app alerts remain gated
by their own setting. The default with neither channel selected retains its
previous empty change state and creates no extra alerts or deliveries.

The new publication tests use the real public publisher, repositories and email
dispatcher with a recording sender. They cover every-edition and material-change
policies, changed and unchanged reports, independent in-app settings, default
silence, publication replay, rollback and retry, and disabled or stale projection.
No external SMTP calls are made. Existing fresh-recipient checks still decide
authority immediately before dispatch.

## Validation

- SQLite: 55 tests passed across rotation, actual consumer models, rotation CLI,
  publication, schedule changes, notification delivery and opt-out tests.
- Fresh disposable PostgreSQL: nine generic rotation tests and 15 real-model and
  publication tests passed. Two private databases separated the generic schema
  from the application schema; the labelled temporary container was removed.
- Strict mypy passed all 1,453 source files. Import-linter kept all three contracts.
- Repository Ruff checks, touched-file formatting, focused Bandit, whitespace and
  the file-length gate passed. Changed source and test files remain below 350 lines.

These checks establish local transaction and persistence behaviour. Actual
credential rotation, operator recovery, live relay delivery and browser-provider
acceptance remain separate operational actions.

# Security and privacy

[Documentation](README.md) · [Architecture](01_ARCHITECTURE.md) · [AI](AI.md) · [Self-hosting](DEPLOYMENT.md)

The app handles accounts, private research, saved reports, provider credentials
and untrusted public material. Its controls are designed to keep access explicit,
limit external work and preserve the distinction between source content and
instructions. These are implemented safeguards, not a security certification.

## Accounts and shared work

Passwords use Argon2id hashing and a common-password check. Account requests need
administrator approval. Administrators must enrol and verify multi-factor
authentication before entering the administration workspace. Authenticator and
email options depend on the installation's configuration.

Access tokens are short-lived and held in browser memory. Refresh sessions use
an HttpOnly cookie, server-side records and rotation. Protected requests check
the current account and session state. Streams also recheck access; the browser
invalidates scoped state when authority changes.

Personal records are visible to their owner and administrators. Team records are
visible to current members and administrators. Object-level checks cover saved
research, report versions, exports, searches and background work. Membership is
not permanent authority: removal, account deactivation and team archiving affect
subsequent operations. Archived work remains readable under the applicable scope.

Sensitive mutations coordinate account and team checks with concurrent authority
changes. Model and network calls run outside those database locks, and sensitive
results are checked again before persistence or release. Already downloaded
copies cannot be recalled.

## Untrusted sources, files and model output

Public-feed requests use destination checks, redirect checks, bounded responses
and deadlines. Private and local model endpoints are a separate, deliberate
administrator choice, needed for self-hosted models. A source URL cannot silently
become permission to use the administrator's model endpoint.

Supplied documents and media are parsed under time, size and resource limits.
The Compose parser has no network access and does not receive application secrets.
Native parsing uses an isolated subprocess and refuses extraction when required
limits cannot be installed.

External text and AI output are treated as data. The interface renders structured
text and validated links. Report validation checks structure, citations and
assessment rules; it cannot prove the truth of source claims or eliminate all
prompt-injection risk. See [AI](AI.md) and
[reporting and assessment](03_DOCTRINE_AND_REPORTING.md).

## Credentials and durable data

Provider credentials and authenticator secrets are encrypted using the configured
application encryption key. The UI does not return saved full provider keys.
Real environment files are excluded from version control. Logs and errors must
avoid credentials, raw provider responses and other secret-bearing content.

Keep the encryption key recoverable separately from the database. Replacing it
makes existing encrypted values unreadable. Database backups can contain private
research, evidence excerpts and personal information, even when those excerpts
came from public websites.

Raw live events have bounded in-memory retention. Reports deliberately preserve
selected evidence. Private supplied inputs and selected original assets have their
own retention rules; inspect the workflow rather than assuming all inputs are
permanent or all are immediately deleted.

## What may leave the installation

| Feature | Outbound information |
| --- | --- |
| Feed collection and research connectors | Requests, source-specific query terms and the configured contact identifier |
| Map and reference services | Requests for the tiles, catalogues or data needed for the view |
| AI features | Relevant questions, selected evidence, extracted text or sanitised images sent to the configured model |
| Optional fresh web research | Public research question and selected public scope sent to the compatible search provider |
| Email | Account messages and verification codes through the configured mail service |
| Optional archive capture | Cited URLs sent to the Internet Archive |
| Optional alert webhook | Alert notifications sent to the configured destination |

Enabled background collection based on private plan terms can disclose those terms
to the queried public provider. Supported private-file research does not
implicitly turn the extracted content into public feed queries, but model analysis
can still send it to the chosen AI provider.

Self-hosting controls where the application and its database run. It does not make
external source requests, map tiles or cloud model calls offline. Review provider
terms and account retention settings for the material you intend to handle.

## Operating the app

Use HTTPS for hosted access, stable protected secrets and a controlled
administrator account. Keep the API, database and parser behind the intended web
boundary. The [self-hosting guide](DEPLOYMENT.md) covers the portable requirements;
installation-specific access and recovery instructions belong in private operator
records.

CI checks dependencies, source code and container images alongside tests and type
checks. Passing those checks is useful evidence, not proof that an installation
has no vulnerabilities. Keep dependencies current, review changes and test
[backup restoration](BACKUP_RESTORE.md) with your own storage and key handling.

Reducing published server details avoids unnecessary disclosure. It does not
replace patching, authentication, access controls or a reviewed configuration.

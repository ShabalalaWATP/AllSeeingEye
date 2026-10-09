# Deployment enquiries

`POST /api/enquiries` is public and disabled by default. It is distinct from
account requests. Enablement requires an approved privacy notice, the controller's
contact details, a configured SMTP transport and `ASE_ENTERPRISE_ENQUIRY_NOTIFY_EMAIL`.
Configuration validation confirms a real transport is configured, not that a live
SMTP server is reachable. Verify delivery separately during an authorised rollout.

The JSON body contains `name` (1 to 100 characters), `email` (at most 254),
`organisation` (1 to 150), optional `role` (at most 100), `deployment_interest`
(`own_cloud`, `on_premises`, `air_gapped`, `undecided`), `expected_users`
(`1_10`, `11_50`, `51_250`, `250_plus`) and optional `message` (at most 2,000).
The optional `website` honeypot must be left empty. Unknown properties are rejected.
Single-line fields reject CR/LF; control and formatting characters are stripped.
Email is validated without DNS lookups and stored in normalised lower case.

Accepted, same-day duplicate and honeypot submissions return the identical `202`
receipt: `{"message":"Thank you. Your enquiry has been received."}`. Limits return
`429` with `Retry-After`; disabled installations return `404`. The ordinary request
body limit defaults to 64 KiB. Responses are not cached. `/api/site` exposes only
the enablement flag and retention period, never the recipient or stored data.

The existing process-local limiter allows three submissions per client key per
hour, two per normalised email per day, and fifty globally per day. Honeypots use
the client allowance without storing or sending. Limits reset on process restart,
as other application limits do; use one API process or a shared limiter before
scaling out. Canonical identical submissions on the same UTC date have a unique
database key, so concurrent duplicates cannot store or email twice.

Stored records contain no IP address. Audit entries contain only the new enquiry
ID, with no name, email, organisation or message. SMTP sends plain text to the
configured operator address with a fixed subject, never to the submitter. The
record commits before delivery. Failed delivery leaves the enquiry available for
administrator follow-up; there is no automatic SMTP retry in this endpoint.

Migration 0093 follows 0092. Apply it using the existing reviewed migration and
backup workflow before enabling the endpoint. Downgrade refuses a non-empty table.
No operator database is migrated during development. The public form is KAN-168.
Keep the feature disabled until that workflow and the privacy notice are ready.

## Administrator review and erasure

MFA-verified administrators can list `GET /api/admin/enquiries` with optional
`status=new|contacted|closed`, `limit` (1 to 100, default 25) and `offset` (default
0). Filtering precedes both the count and pagination. Results are newest first,
with a stable ID tie-breaker. The response contains `items` and `total`.
`GET /api/admin/enquiries/{id}` returns one currently retained record.

`PATCH /api/admin/enquiries/{id}` accepts only `{"status":"contacted"}` (or
`new`/`closed`), updates the decision timestamp and records the actor in audit.
`DELETE` on the same URL permanently erases the record. All responses are
`no-store`. Every route has an administrator-only session release fence; writes
take the shared administration guard and freshly validate the session before
committing. Audit records contain only the enquiry ID, actor, action and time.
They never contain the enquiry's text, email address or IP address.

## Retention

`ASE_ENTERPRISE_ENQUIRY_RETENTION_DAYS` defaults to 365, with a minimum of 30 and
maximum of 3,650. The cutoff uses the original submission time, so contacting or
closing an enquiry never extends retention. Records older than that period are
immediately excluded from list and direct reads, even when submissions are
disabled. The existing housekeeping cycle permanently deletes up to 100 expired
rows each minute. A restart or interrupted cycle is safe to repeat. A large
backlog takes more than one cycle; stopped installations resume erasure on start.
Only the committed deletion count is logged.

`GET /api/site` publishes `enterprise_enquiry_retention_days` so the KAN-165
privacy notice and KAN-168 form can show the configured period consistently.
The notice must also explain separately managed backups and operator email
copies: deleting the application's row does not erase either. Operators must
include those copies in their retention and erasure procedure.

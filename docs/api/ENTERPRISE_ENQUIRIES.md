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
the `enterprise_enquiries_enabled` boolean, never the recipient or stored data.

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
No operator database is migrated during development. Administrator management and
retention are delivered by KAN-167; the public form is KAN-168. Keep the feature
disabled until those workflows and the privacy notice are ready.

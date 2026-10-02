# Browser CSP reporting

The production Caddy policy sends modern Reporting API and legacy CSP reports to
`POST /api/security/csp-reports`. No account is required. Requests are capped at
16 KiB at the endpoint, eight reports per batch, 20 requests per client IP per
minute and 120 requests per process per minute globally. The outer ordinary proxy
and API body limit remains 64 KiB. Use the single API worker deployment or review
shared limiting before adding workers.

Structured `csp_violation` log events contain only `directive`, `blocked_host` and
`document_path`. Query strings, fragments, credentials, source samples, source-file
URLs and raw report bodies are never logged. Non-network blocked sources are
labelled `non-network`. Reports are untrusted diagnostics, not proof of an attack.
Use the operator's bounded container logs to inspect events; no new datastore or
external reporting service is introduced.

For an authorised local browser check, serve the production web image and insert
an inline script using developer tools. Confirm the browser blocks it and a
`csp_violation` line appears in the API log. Browser delivery is best-effort and
may be delayed. API tests cover both report formats, redaction, malformed reports,
size limits (including chunked bodies) and rate limiting separately from this live
browser acceptance check.

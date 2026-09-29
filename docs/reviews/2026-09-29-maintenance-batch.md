# Six-ticket maintenance batch, 29 September 2026

Draft [PR #86](https://github.com/ShabalalaWATP/AllSeeingEye/pull/86) holds six
separately committed Jira fixes from the `a539ea6f` main baseline. Each issue is
assigned to alexcodex and in review. The PR has no file overlap with Claude's
open frontend PRs #83, #84 and #85.

| Jira | Change | Regression evidence |
| --- | --- | --- |
| [KAN-15](https://alex-orr.atlassian.net/browse/KAN-15) | Redact secret-shaped keys in nested dictionaries, lists and tuples, with a depth bound for cyclic payloads. | Two new tests failed before the fix; 17 focused tests passed after it. |
| [KAN-29](https://alex-orr.atlassian.net/browse/KAN-29) | Reject parser requests safely when Unix sockets are unavailable, before the server touches its socket path. | Three Windows regressions failed before the fix; 36 focused tests passed, one POSIX-only test skipped. |
| [KAN-30](https://alex-orr.atlassian.net/browse/KAN-30) | Use one camera availability and provider-state rule in cached and refreshed views. | Four of eight state combinations failed before the fix; the 35-test camera suite now passes. |
| [KAN-40](https://alex-orr.atlassian.net/browse/KAN-40) | Read in-memory provider statuses after concurrent refreshes, without a fourth catalogue call. | A call-count regression caught the fourth call; a forced-order regression caught a stale status in the first attempt. The 35-test camera suite passes. |
| [KAN-145](https://alex-orr.atlassian.net/browse/KAN-145) | Select PowerShell 7 for Windows Justfile recipes and document the optional prerequisite. | The shell test reproduced the PowerShell 5.1 parser error, then passed with PowerShell 7. A real Windows `just check` completed. |
| [KAN-20](https://alex-orr.atlassian.net/browse/KAN-20) | Return only `{"status":"ok"}` from public health and regenerate OpenAPI and TypeScript contracts. | The unauthenticated HTTP test failed before the fix; 13 health/error tests and frontend typecheck passed. |

The touched camera test module was split back under 350 lines. The Windows
`just check` run passed backend lint, formatting, typing and import contracts,
frontend lint and typing, and the file-length gate. The API-generation recipe
also ran successfully. The Docker HEALTHCHECK tests HTTP 200 and the uptime
workflow matches `"status":"ok"`; neither consumes the removed version field.
No live Compose stack was started for this isolated worktree.

The full Windows backend run with six workers finished with 9,838 passed, 93
skipped and one failure, while coverage reached 93.78% above the 90% gate. The
failure was a 15-second readiness wait in the unchanged report-job pause test.
It passed alone in 4.87 seconds. We did not alter report-job behaviour or
increase its timeout without evidence of a product defect. All GitHub CI checks
on the final code commit passed, including eight SQLite shards, eight PostgreSQL
shards, frontend tests/build, CodeQL, Semgrep, dependency review and security.
Local Bandit and pip-audit passed; pip-audit could not audit the private `ase`
package against PyPI. The repository script suite passed 70 tests, with three
platform/tool skips. The PR checks show the current validation state for the
documentation commits.

Code-quality review: the camera state rule and status derivation have one
implementation each. A result from the last listed provider can finish before
another provider, so the final status snapshot must happen after `gather`.
The parser paths remain explicit and fail closed. Security
review: nested structured values are bounded before rendering, and health
publishes less metadata. Key-name redaction remains heuristic, so callers must
avoid putting credentials in free-text values. Documentation review: setup now
states the PowerShell 7 requirement, and generated API contracts match the new
health shape. Final PR CI and release approval remain gates. Merging to `main`
enters the production deployment path and requires Alex's approval.

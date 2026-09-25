# CI and security gates

The consolidated CI workflow runs backend lint, formatting, typing and dependency
boundary checks; frontend lint, typing, tests and build; Python and JavaScript
dependency audits; Bandit; Gitleaks; Semgrep; and container vulnerability scans.
GitHub CodeQL uses default setup and must not also be configured in a competing
advanced workflow. Semgrep publishes SARIF to GitHub code scanning.

Contract and delivery checks fail when the committed `openapi.json` or
`types.gen.ts` differs from what the backend and `pnpm gen:api` produce. They also
fail when the production build loads a lazy-only library (deck.gl, MapLibre,
three.js, hls.js or the globe page) before first paint, ships a development preview
page, or exceeds the initial JavaScript gzip budget in `frontend/scripts/check-bundle.js`.
`repo-checks` asserts that the production Caddy policy admits every camera host the
client allows and that only content-hashed assets are cached as immutable.

Backend tests run in eight deterministic file shards for each database. Every
PostgreSQL shard has its own service because fixtures recreate database tables.
The `backend` and `backend-postgres` aggregate jobs explicitly fail if any required
shard fails. They combine coverage and enforce 90%; individual shards cannot
meaningfully meet an application-wide coverage threshold on their own.

Dependency review blocks newly introduced moderate or higher vulnerabilities on
pull requests. Existing audits retain their configured thresholds. Trivy blocks
fixable high and critical image vulnerabilities. This does not establish the
absence of vulnerabilities or replace application security review.

## Main branch protection

After a successful run, require `backend`, `backend-postgres`, `frontend`,
`security`, `semgrep`, `images`, `repo-checks` and `dependency-review`, with GitHub
Actions as their expected source. Require the configured CodeQL and Semgrep code
scanning results. Require pull requests, block force pushes and branch deletion.
Avoid requiring generic duplicate `Scan` jobs from GitHub workflow templates.

The operator temporarily disabled the main ruleset during repair. The repair does
not silently re-enable it before checks have been observed on GitHub.

## Scanner exceptions and dependency compatibility

The Python 3.7 importlib compatibility rule is inapplicable to Python >=3.13.
Other Semgrep exceptions are local and documented: defusedxml type imports,
an in-memory repository method, and tests asserting escaped malicious markup.
Camera catalogue module imports are constrained to the fixed country allowlist.

Caddy 2.11.4 cannot build with cel-go 0.29.0. Keep cel-go 0.28.1 until the upstream
API compatibility is resolved; retain the compatible x/net and gRPC updates.
Container builds apply available operating-system security updates.

Dependabot covers Actions, Python, JavaScript, Go and Docker. Generic Bandit,
ESLint and Semgrep template workflows duplicate checks already present here;
the obsolete OSV template is replaced by dependency review and package audits.

## Validation on 17 September 2026

Local builds passed for both images. Trivy reported zero high/critical findings
for the web image and zero fixable high/critical findings for the API image.
An unfiltered API scan still reported upstream Debian findings without fixes,
including critical CVE-2026-6653 in libxml2. These are outstanding risks under the
existing `ignore-unfixed` policy, not remediated findings. Repeat the full image
scan when upstream updates become available. Scan results depend on database time.

CodeQL alerts 5002 and 5003 were reviewed and dismissed as false positives: the
cookie transports an opaque bearer token with HttpOnly/SameSite controls; SHA-256
digests random tokens, while human passwords use Argon2id. Alerts 5004 through
5007 are test-only assertions, including exact host/handle membership and
User-Agent provenance. Their individual dismissal records retain the rationale.
The casualty importer now uses HTMLParser to exclude hidden script/style text
instead of regex stripping (5008). The economic summary test now positively
asserts HTTP(S) link protocols (5001). Neither test assertions nor the importer
text output are production HTML sanitisation boundaries.

The full database run also exposed missing parent/child flush ordering when
creating report ledgers. The parent is now flushed inside the existing savepoint
before its entries, preserving atomic rollback and foreign-key enforcement.
The refresh-family concurrency test now forwards the MFA argument and propagates
child-task failures. Report-worker fixture completion is bounded at 60 seconds
instead of 15, after observing active checkpoint SQL work under coverage; the
120-second test ceiling and result assertions remain unchanged.

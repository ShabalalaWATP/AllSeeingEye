# CI and security gates

Reconciled on 9 October 2026 against source revision
[`13efceef48efbc6d5f2895e60c55076db5d40e3f`](https://github.com/ShabalalaWATP/AllSeeingEye/tree/13efceef48efbc6d5f2895e60c55076db5d40e3f),
read-only GitHub protection queries and the Jira items linked below. The live
`main` branch still pointed to that revision at the check. Workflow configuration,
live enforcement and historical run results are described separately.

## Workflow and contract checks

The consolidated CI workflow runs backend lint, formatting, typing and dependency
boundary checks; frontend lint, typing, tests and build; Python and JavaScript
dependency audits; Bandit; Gitleaks; Semgrep; and container vulnerability scans.
GitHub CodeQL uses default setup and must not also be configured in a competing
advanced workflow. Semgrep publishes SARIF to GitHub code scanning.

The frontend also requires the bounded Chromium regression lane described in
[browser regressions](../BROWSER_REGRESSIONS.md). It uses synthetic API responses,
rejects external requests, retains failure traces and reports elapsed runtime.
Its result participates in the existing frontend aggregate; coverage and security
thresholds remain unchanged. Historical KAN-81 acceptance remains separate.

Contract and delivery checks fail when the committed `openapi.json` or
`types.gen.ts` differs from what the backend and `pnpm gen:api` produce. They also
fail when the production build loads a lazy-only library (deck.gl, MapLibre,
three.js, hls.js or the globe page) before first paint, ships a development preview
page, or exceeds the budgets in
[`frontend/scripts/check-bundle.js`](../../frontend/scripts/check-bundle.js):
240 KiB gzipped for initial JavaScript and 850 KiB for the globe route's additional
static dependency closure, including its MapLibre worker. These are not a dedicated
`/enterprise` route budget.
`repo-checks` asserts that the production Caddy policy admits every camera host the
client allows and that only content-hashed assets are cached as immutable.

## Test shards and coverage

The configuration is in [CI](../../.github/workflows/ci.yml), its reusable
[frontend workflow](../../.github/workflows/frontend.yml), the
[backend shard runner](../../scripts/run_test_shard.py) and the
[native PostgreSQL planner](../../scripts/plan_native_shards.py).

| Lane | Partition and isolation | Aggregate gate |
| --- | --- | --- |
| SQLite | Eight deterministic file shards, indices 0–7, balanced by recorded file durations. Each uses xdist with private in-memory databases. | `backend` requires backend quality checks and every shard to succeed, requires all eight coverage files, combines them and enforces coverage.py's aggregate 90% threshold. |
| PostgreSQL | `postgres-plan` collects the selected native test IDs into a source/runtime-bound manifest. Four shard jobs, indices 0–3, each have their own PostgreSQL service and run parallel and serial lanes. Parallel workers use isolated databases; eligible fixtures use templates. Serial cases run without xdist. | `backend-postgres` requires the plan and every shard to succeed, requires all eight shard/lane coverage files, combines them and publishes diagnostic coverage with `--fail-under=0`. It does not enforce a second application-wide 90% threshold. |
| Frontend | Four Vitest shards, indices 1–4, emit blob reports with per-shard thresholds disabled. | The merge job requires all four blobs, merges coverage and applies the configured thresholds. It also requires frontend checks and every test shard to succeed. The protected `frontend` job requires the reusable workflow to succeed. |

Individual shards disable the global threshold because they exercise only part of
the suite. Completeness and upstream-success checks remain mandatory at aggregation.
PostgreSQL's selected persistence/native suite is not another full SQLite suite.

Additional enforced floors come from
[`check_coverage_floors.py`](../../scripts/check_coverage_floors.py):

- **Backend security:** each reviewed matching module needs at least 95% line and
  branch coverage in the combined SQLite report. The policy covers auth,
  authorisation, access policy, token/session persistence, grading and validation
  patterns. Missing reviewed modules or invalid reports fail the check.
- **Frontend global:** [Vitest](../../frontend/vitest.config.ts) requires 90% for
  lines, statements, functions and branches after merging. The branch-floor check
  additionally requires 92% global branches and 70% for each file with at least
  20 branches.
- **Frontend auth:** `features/auth/*` and `stores/auth.ts` each need 95% line and
  branch coverage; missing reviewed modules fail. These checks run against the
  merged report, not individual shards.

These are configured gates, not newly measured coverage results for this
documentation change. Coverage exclusions remain defined in the source configs.

## Security scans

Dependency review blocks newly introduced moderate or higher vulnerabilities on
pull requests. `pip-audit` checks the installed locked Python environment;
`pnpm audit --audit-level high` checks JavaScript dependencies. Bandit and Gitleaks
run in `security`. Semgrep scans with `--error`; its separate publication job
attributes SARIF to the PR head or pushed commit.

The `images` aggregate requires both API and web image jobs, including Trivy's
fixable HIGH/CRITICAL threshold (`ignore-unfixed: true`); the web image also has a
static-serving smoke check. The separate weekly `Database image` workflow is not
one of these two application image jobs. A passing scan does not establish the
absence of vulnerabilities, cover unfixed findings excluded by policy or replace
application security review.

## Main branch protection

Read-only GitHub API checks on 9 October 2026 confirmed that
[`protect-main`, ruleset 23590400](https://github.com/ShabalalaWATP/AllSeeingEye/rules/23590400)
is **active**, targets `refs/heads/main` and has no listed bypass actors. Its
[effective branch rules](https://api.github.com/repos/ShabalalaWATP/AllSeeingEye/rules/branches/main)
require:

- Pull requests, resolved review threads and squash merges. Force pushes and
  branch deletion are blocked.
- Up-to-date status checks from GitHub Actions (integration ID 15368): `backend`,
  `backend-postgres`, `frontend`, `security`, `semgrep`, `images`, `repo-checks`
  and `dependency-review`.
- CodeQL code scanning with `security_alerts_threshold: medium_or_higher` and
  `alerts_threshold: all`; Semgrep OSS with `high_or_higher` and `errors` respectively.

CodeQL [default setup](https://api.github.com/repos/ShabalalaWATP/AllSeeingEye/code-scanning/default-setup)
was configured with the default query suite. The ruleset also enables Copilot
review on pushes to non-draft PRs. It requires **zero approving reviews**, with
code-owner and last-push approval requirements disabled. Automated review is not
an enforced human release-approval gate.

The old statement that the ruleset remained disabled described a repair period
and is superseded by this readback. The legacy branch-protection endpoint returned
404 while the ruleset and branch endpoints reported active protection; use the
effective rules endpoint when checking this repository.

### Production release approval

The [production environment](https://api.github.com/repos/ShabalalaWATP/AllSeeingEye/environments/production)
had only a branch-policy protection rule at the same check. Its custom deployment
branch policy allowed `main`; no required reviewer or wait timer was configured,
and `can_admins_bypass` was true.

[`deploy.yml`](../../.github/workflows/deploy.yml) can deploy successful
push-triggered `main` CI after checking that the tested commit is still current.
Repository policy still requires explicit release approval before merging.
[KAN-225](https://alex-orr.atlassian.net/browse/KAN-225) proposes enforcing that
approval in GitHub and remains pending approval of the design. No proposed
reviewer configuration is represented here as applied, and this documentation
change does not alter GitHub or production settings. This gap does not establish
that a particular previous release lacked approval.

## Delivery acceptance reconciliation

Jira was read again on 9 October 2026:

- [KAN-215](https://alex-orr.atlassian.net/browse/KAN-215), the product-page title
  assertion fix, is **Done**. The merged
  [test](../../frontend/src/features/product/ProductPage.test.tsx) uses `waitFor`
  for the effect-driven title. It is not outstanding implementation work.
- [KAN-172](https://alex-orr.atlassian.net/browse/KAN-172) remains **In Review**.
  The public `/enterprise` foundation and chapters are already delivered.
  Outstanding acceptance includes canonical/Open Graph metadata, its dedicated
  150 KB gzipped route budget and measured launch evidence, including mobile
  Lighthouse targets (performance 95, accessibility 95, SEO 90) and network checks.
  The current initial/globe bundle gates do not satisfy that dedicated budget.
  The estimator remains intentionally hidden pending approved cost figures.

Passing unit tests or the existing bundle checks does not close those measured
acceptance criteria. Keep the remaining work on KAN-172 without reopening the
completed page construction or prematurely closing its parent epic. This
reconciliation records live statuses; it makes no Jira transitions.

## Scanner exceptions and dependency compatibility

The Python 3.7 importlib compatibility rule is inapplicable to Python >=3.13.
Other Semgrep exceptions are local and documented: defusedxml type imports,
an in-memory repository method, and tests asserting escaped malicious markup.
Camera catalogue module imports are constrained to the fixed country allowlist.

KAN-227 updates Caddy to 2.11.7 and its compatible `cel.dev/cel-go` 0.32.0
dependency, removing the old `github.com/google/cel-go` 0.28.1 dependency and
the temporary Dependabot exclusion for GHSA-gcjh-h69q-9w9g. The shared Caddyfile
does use expression matchers, so validation must include that configuration.
The digest-pinned Go 1.27.2 builder and x/net 0.60.0 address the additional Go
advisories reported by the image gate on 9 October 2026. Build metadata is
available with `caddy build-info`; both module checksums and the production
configuration are checked during validation. The Python lockfile includes Mako
1.4.2 for GHSA-5639-2j2p-m4mx. Repeat package and image scans against the current
advisory databases rather than treating these versions as permanently safe.
The backend image stays on Python 3.13, the version CI tests, until both move together.
Its refreshed official-image digest provides Python 3.13.16 and invalidates the old
package-update layer. The rebuilt image includes Debian OpenSSL 3.5.7-1~deb13u3,
addressing CVE-2026-84782. Both rebuilt images passed the configured fixable
HIGH/CRITICAL Trivy threshold locally on 9 October 2026. Container builds apply
available operating-system updates, but a later security refresh must invalidate
cached package-update layers as described in the deployment guide.

Dependabot covers Actions, Python, JavaScript, Go and Docker. Generic Bandit,
ESLint and Semgrep template workflows duplicate checks already present here;
the obsolete OSV template is replaced by dependency review and package audits.

## Historical validation reported on 17 September 2026

The following is retained evidence from that date. These builds, scans and alert
dispositions were not rerun or revalidated by the 9 October documentation review;
they are not current image attestations or fresh CI results.

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

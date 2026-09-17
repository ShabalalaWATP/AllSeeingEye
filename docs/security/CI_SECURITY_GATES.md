# CI and security gates

The consolidated CI workflow runs backend lint, formatting, typing and dependency
boundary checks; frontend lint, typing, tests and build; Python and JavaScript
dependency audits; Bandit; Gitleaks; Semgrep; and container vulnerability scans.
GitHub CodeQL uses default setup and must not also be configured in a competing
advanced workflow. Semgrep publishes SARIF to GitHub code scanning.

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

The Python 3.7 importlib compatibility rule is inapplicable to Python >=3.12.
Other Semgrep exceptions are local and documented: defusedxml type imports,
an in-memory repository method, and tests asserting escaped malicious markup.
Camera catalogue module imports are constrained to the fixed country allowlist.

Caddy 2.11.4 cannot build with cel-go 0.29.0. Keep cel-go 0.28.1 until the upstream
API compatibility is resolved; retain the compatible x/net and gRPC updates.
Container builds apply available operating-system security updates.

Dependabot covers Actions, Python, JavaScript, Go and Docker. Generic Bandit,
ESLint and Semgrep template workflows duplicate checks already present here;
the obsolete OSV template is replaced by dependency review and package audits.

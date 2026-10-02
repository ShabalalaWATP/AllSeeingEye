# Security and operations batch, 30 September 2026

The isolated `codex/KAN-153-security-operations` branch starts at `69696286`.
It implements KAN-16, KAN-17, KAN-18, KAN-19, KAN-21, KAN-153, KAN-154 and
KAN-155. The API shutdown settings also satisfy the Compose portion of KAN-43.
No production deployment, credential rotation or operator database change was run.

| Issue | Change | Local evidence |
| --- | --- | --- |
| KAN-16 | Deploy host and port use protected secrets with validation and existing pinned host keys. | Workflow configuration regression passes. Secret provisioning and the next `DEPLOYED` result require the authorised manual rollout. |
| KAN-17 | Protected-file CLI preflights and re-encrypts all seven encrypted fields across five tables in one transaction. | SQLite rollback, wrong-key, malformed-row, metadata and CLI tests pass. Nine rotation tests also pass against a disposable PostgreSQL/PostGIS database. |
| KAN-18 | Exact reserved Caddy address is trusted; API drops all capabilities; database drops all except five entrypoint requirements and prevents privilege escalation. | Uvicorn rejects forwarded headers from other peers in tests. Disposable API reaches HTTP 200 with `CapDrop=[ALL]`; pinned PostGIS initialises and stays healthy with the documented five capabilities. |
| KAN-19 | Advisory workflow builds and inventories API and web images as CycloneDX, storing image identity and commit-linked artefacts. | Workflow configuration check passes. Downloadable artefacts still require the first GitHub workflow run. CI inventory does not claim identity with separately rebuilt production images. |
| KAN-21 | Bounded, rate-limited CSP reporting strips URL queries, fragments and user information. | HTTP format, redaction, size and rate-limit tests pass. A Chromium browser behind the production Caddy policy over local HTTPS blocks an inline script and generates exactly one structured `csp_violation` event containing `/csp-check` without its query. |
| KAN-153 | Exact avatar/workspace route and method allowances match the API. | Disposable Caddy against the real in-memory API passes valid uploads above 64 KiB, authorisation and oversized fixed/chunked bodies; unrelated methods stay bounded. |
| KAN-154 | Remote disconnect cancels the matching runner and awaits cleanup before admission reuse. | Linux real Unix socket and existing worker tests: 39 passed. Controlled tests also prove a different client's job survives. |
| KAN-155 | Sender receipts separate submission history from private delivery and recipient identity until acceptance. | Full HTTP flow tests cover counts, status, pagination, identity changes, acceptance, decline, withdrawal, expiry and limits. Independent post-patch review: seven checks pass after repairing legacy withdrawal. |

The main focused backend run passed 101 tests with one Windows Unix-socket skip.
Actual-schema encryption and session-fence checks passed 13 tests. After the
independent review repair, the invitation suites passed 18 tests. These runs
overlap and must not be added as a distinct-test total. Frontend invitation tests
passed 17 tests across three files, and TypeScript checking passed. No coverage
measurement was requested for these isolated runs; the repository threshold is
unchanged.

Backend Ruff, full mypy (1,376 source files), three import contracts, focused
Bandit, Caddy policy tests and the file-length gate passed before the final
invitation repair. Ruff and mypy then passed on all repaired source boundaries.
OpenAPI and generated TypeScript were regenerated. Caddy adaptation and
configuration validation passed using the pinned production Caddy image.

Independent security investigation confirmed that hiding recipient fields alone
would leave count, status, revision and capacity oracles. Receipts therefore own
those sender-visible values. The candidate review found that migration 0067 hid
legacy pending invitations while leaving recipients able to accept them and
senders unable to revoke them. The repair permits authorised, known-ID withdrawal
only for a delivery without a linked receipt, returns the same empty response for
missing or resolved IDs, and does not create sender history. Independent checks
confirmed revocation prevents acceptance, wrong-team IDs do not alter grants,
modern delivery IDs cannot bypass receipts, and missing IDs reveal no state.

Migration 0067 is additive. Accepted historical deliveries get a receipt without
reconstructing current profile names; unaccepted historical deliveries remain in
recipient inboxes and are excluded from sender enumeration. The migration does
not reconstruct historical unknown submissions that were never stored. Its
downgrade requires a reviewed matching backup. See `INVITATION_PRIVACY.md` and
`ENCRYPTION_KEY_ROTATION.md` for the explicit compatibility and recovery contracts.

Remaining validation belongs to integration and release: the complete Compose
stack and a throwaway-container audit-IP check, the first downloadable GitHub
SBOM artefacts, deployment secret provisioning and the next successful deploy.
The capability checks used disposable individual containers, not a complete
production-equivalent stack. No live infrastructure settings were changed.

## Coordinator integration

The batch now includes the architecture/runtime stack and CI/test PR #91.
The integrated invitation privacy/migration, CSP, startup imports, runtime
health, shutdown and lifecycle suite passed 64 tests. The OpenAPI document
and frontend types were regenerated and unchanged, and TypeScript passed.
Full mypy passed on 1,399 source files, full-source Ruff passed and all three
import contracts were kept. The stack also includes the verified CI assertion
and test-container repairs from PRs #89 and #90.

GitHub CI and the first advisory SBOM workflow remain pending on publication.
The new CI preserves the SQLite 90% global coverage gate and adds reviewed
95% security-module floors. KAN-71 explicitly removes only the duplicate
PostgreSQL percentage gate while retaining persistence tests and their report.

The full disposable Compose rehearsal then reproduced two operational defects:
Docker assigned the API Caddy's reserved address before web startup, and the
API shell entrypoint prevented SIGTERM reaching Uvicorn. A populated stop took
30.751 seconds, exited 137 without OOM, and wrote neither shutdown phases nor
the final snapshot. The repair explicitly assigns distinct API/web proxy
addresses and uses `exec uvicorn` after migration. Six configuration regressions
pass. A fresh full Compose retry at `88664dc5` restored all 100,000 retained
events. The populated API stopped in 6.878 seconds with exit 0, no OOM, all seven
shutdown phases complete and a fresh final snapshot. Readiness returned in
26.761 seconds and a new authenticated stream in 27.892 seconds. Durable user,
audit and refresh rows remained present. The old stream exposed a separate
cooperative-close gap in the SSE library's default zero-grace shutdown.

The `5eb6167d` follow-up uses the library's supported shutdown signal and a
two-second grace period. Idle stream reads wake on that signal, close the
subscription and release admission, allowing the final ASGI body to complete.
The regression failed before the change and passed afterwards; 55 stream tests
and three session-fence architecture checks passed. Coordinator review found
no access-check or cancellation regression, and nine combined stream/configuration
checks plus full mypy (1,399 modules) passed after integration.

The final 100,000-event Compose rehearsal ended the old authenticated stream
normally, with no incomplete-response error. API stop took 3.654 seconds, exited
0 without OOM, and all seven cleanup phases completed in 1.635 seconds. The final
snapshot retained all 100,000 events. Readiness returned in 9.717 seconds and a
new authenticated stream in 10.134 seconds; durable records remained intact.
The tested API image was `sha256:6e159103d0b9dba68a96a7fe1dfd169bb6312d36dbe118c38e6137d61fdec824`.

The complete disposable proxy test also passed: actual Caddy traffic retained
the correct client address, while a direct caller on the ordinary application
network could not forge it. The harness used its own networks, local CA, database
and loopback ports. Docker Desktop required a separate web-only ingress bridge
to publish loopback ports while the API/proxy networks remained internal.

The first [SBOM workflow](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36660418423)
completed successfully. Both downloaded inventories parse as CycloneDX 1.6:
5,693 components for API and 405 for web. The accompanying image metadata
records GitHub's tested PR merge revision `4ef60571`, generated from this batch
at `88664dc5`. No production image or deployment is implied by these inventories.

## Loopback-only proxy regression fixture, 2 October 2026

CodeQL review of `7b768495` identified the optional upload fixture's all-interface
API listener. The replacement binds the API and Caddy explicitly to loopback.
The opt-in runs inside a disposable Linux test runner labelled
`ase.kan153.test-runner=true`, with `--network none`, its default container
hostname, Docker CLI/socket access and no published ports. Set
`ASE_CADDY_INTEGRATION=1` and `ASE_CADDY_TEST_CONTAINER` to that runner's name.
Its Python environment needs the locked development dependencies and the checkout
available read-only, with `backend/src` and `backend/tests` on `PYTHONPATH`.
Cache the existing digest-pinned Caddy image before starting the isolated runner;
the fixture uses `--pull=never`.

Caddy joins only the verified runner's network namespace. Fixture configuration
disables its admin/automatic-HTTPS listeners and changes its upstream to loopback;
production upload rules and all existing HTTP assertions are retained. Native
Windows/macOS opt-ins fail with an explicit unsupported-runner message. Docker
Desktop can run the isolated Linux container without host-network support.

Docker commands have bounded completion and cancellation waits. Cleanup reconciles
an uncertain create through a unique fixture label, verifies immutable container
IDs, both ownership labels and the exact namespace, then removes only those
containers. Uvicorn stop is bounded and socket close is unconditional. Fresh HTTP
connections avoid reusing a connection closed by an early oversized-body response.

The final Linux run passed 22 tests across proxy uploads, namespace guards,
Docker cancellation/ownership cleanup, limit parity, avatars and workspace body
limits. The real pinned Caddy accepted valid avatar/workspace bodies above 64 KiB
and preserved unauthorised, fixed-length and chunked rejection assertions. Eight
helper/parity tests also passed locally; these overlap the Linux selection. Ruff
lint and formatting passed. Owned runner/sidecar containers were removed. No
production code, policy suppression, coverage threshold or deployed service was
changed. The new published CodeQL result remains a separate CI verification.

# Improvement security review

Review date: 6 September 2026. Baseline: `60dff6b`; changes on
`codex/app-improvement`. This supplements the historical Phase 6 review. It is
evidence from source review, deterministic regressions and local tools, not an
ASVS certification or permission to expose the application publicly.

## Boundaries and findings

| Boundary | Finding and implemented response | Regression evidence |
|---|---|---|
| Issued access tokens | Tokens now identify a live refresh family and account security version. Logout and credential/account changes invalidate subsequent requests. Authentication closes its database session before streaming starts. | `test_access_session_revocation.py`, `test_stream_revocation.py`, `test_stream_session_pool.py` |
| Account administration | Approval/rejection now re-read current administrator authority and pending decisions under a shared transaction guard. Last-administrator transitions and competing decisions are serialised. Mail delivery occurs after the approved account/token/audit commit. | `test_account_decision_security.py`, `test_account_transition_races.py` |
| Password links | Password changes consume the chosen link and invalidate every sibling reset/activation link. Expiry is checked after waiting for account locks. | `test_account_transition_races.py`, `test_token_redemption_races.py` |
| Account self-service | A password change locks and revalidates the current account, checks the current password and any enrolled authenticator, then atomically revokes previous sessions and password links. Failed transactions preserve credentials and factor replay state. | `test_change_password.py`, `test_change_password_security.py` |
| Team authority | A global manager role alone grants no team management. Personal records require their creator or administrator; team reads require current membership or administrator. Writes additionally require ownership or designated management. | `test_access_policy.py`, `test_teams.py`, `test_direction_scope.py`, `test_warning_scope.py`, `test_report_team_scope.py` |
| Lists and relationships | SQL filters precede limits/counts. Links must share the same personal owner or team, including administrator-created links. Legacy conflicts are preserved and audited rather than assigned to guessed teams. | `test_scope_migration.py`, `test_direction_scope.py`, `test_report_privacy.py`, `test_warning_scope.py` |
| Slow and background work | Report generation, embedding work, export rendering and scheduled/indicator effects recheck current authority. Scoped client state hides previous identity/revision data and ignores late responses. | `test_report_team_scope.py`, `test_search_scope.py`, `test_private_response_security.py`, `test_warning_scope_background.py`; frontend scoped-resource/search tests |
| Streaming alerts | Alerts retain their creator/team after rule deletion. Each outgoing alert uses fresh authority; idle membership changes emit `access.changed` so clients clear scoped data. Orphan alerts are administrator-only. | `test_stream_scope.py`, `test_warning_scope.py` |
| Private collection terms | Removed members, inactive owners and archived teams stop automated collection. Social vocabulary follows current personal/team visibility. Public feed results remain shared; enabled query phrases are deliberately sent to Google. | `test_private_collection_terms.py`, `test_watchlists.py` |
| Search storage | Caller-scoped indexing previously risked deleting another scope's vectors, or immediately deleting its own older vector. Shared capacity is now checked before model calls; only obsolete versions are pruned. | `test_search_scope.py` |
| Rendering and caching | Untrusted Markdown is escaped, unsafe links remain unlinked, typed evidence retains provenance, and private API responses prohibit caching. Exports recheck permissions after rendering. | `test_export_provenance.py`, `test_private_response_security.py` |
| Analytical integrity | Topic proximity and copied headlines no longer imply verified corroboration. New responses require strict structure, valid references and supported judgements; grades derive from frozen citations and confidence ceilings are applied per judgement. | `test_grading_integrity.py`, `test_source_provenance.py`, `test_report_integrity.py` |

Test paths above are beneath `backend/tests` unless stated otherwise. The master
improvement plan and development story record the final integrated test totals.
Many regressions were observed failing before their corresponding fixes; new
permission matrices also have direct positive and negative behaviour tests.

## Tool evidence and limits

- Local Bandit source checks passed with the repository configuration.
- Python `pip-audit` and `pnpm audit --audit-level high` reported no known
  dependency vulnerabilities at this check. The local `ase` project is not a
  published PyPI dependency and was excluded by pip-audit.
- Semgrep ran 457 applicable rules over 516 source targets with no findings.
  Twenty files matched its ignore patterns. This does not establish exhaustive
  coverage of every path or third-party implementation.
  A final focused run over the four permission-refresh modules also passed
  (211 applicable rules) after their last changes.
- Gitleaks checked backend and frontend source directories with redacted output
  and reported no leaks. This directory scan is distinct from Git-history review.
  The staged-file pre-commit gate also passed after identifying a synthetic account
  fixture and an event-variable regex match as false positives. Only the synthetic
  password line has an explained `gitleaks:allow`; there is no broad exclusion.
- Independent reviews identified and reproduced the administration, reset-link,
  connection-lifetime and search-retention findings. Coordination found further
  cache, export and private-term issues, which received focused fixes and tests.
- SQLite passed 673 tests with 96.10 percent combined line/branch coverage;
  PostgreSQL passed 675 tests. Frontend passed 351 tests with 98.04 percent line
  and 91.95 percent branch coverage. Migration parity and atomicity tests use
  synthetic disposable data. Final pre-commit and architecture checks passed.
- Both new container builds passed the configured fixable HIGH/CRITICAL gate.
  The full API inventory still contains 54 unfixed package findings (51 HIGH,
  three CRITICAL; 18 unique CVEs across 19 packages). The web inventory has zero
  HIGH/CRITICAL findings including unfixed issues. See the
  [image triage](API_BASE_IMAGE_TRIAGE.md) for immutable IDs, commands, affected
  component checks and required release follow-up. This review does not accept
  those risks or suppress the findings.

No production DAST, operator database migration, real credential probe or real
model evaluation was performed. Tests use synthetic accounts, gateways and
disposable SQLite/PostgreSQL databases. No live events were added to persistence.

## Remaining operational assurance

The host remains part of the trust boundary. Back up and preserve encryption keys
before operator migration, rehearse recovery against the upgraded schema, configure
trusted proxy/TLS and model endpoints deliberately, and repeat the deployment
checks in the historical ASVS review before exposure beyond the LAN. There is no
configured Git remote, so hosted CI has not verified this branch.

Automated report checks establish bounded structure and provenance consistency,
not factual truth, independent sourcing, a measured probability or analyst approval.
PDF font coverage remains limited; unsupported characters are explicitly disclosed.
DOCX structural tests passed, but office-renderer visual verification remains
unavailable without LibreOffice or an appropriate authorised renderer.

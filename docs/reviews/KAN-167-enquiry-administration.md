# KAN-167: enquiry administration and retention

Implementation provides administrator-only list, direct read, status change and
hard erasure routes. Current MFA-backed session checks and the shared
administration/account locks protect mutations; every response passes an
administrator release fence. Status and expiry filtering happen in SQL before
counts or pagination. Audit records hold the enquiry ID and actor, never its
content or IP address.

The original creation time determines retention. Expired entries are hidden
immediately and the existing housekeeping loop erases at most 100 per minute,
including when new submissions are disabled. Fixed-clock tests cover the exact
boundary, repeated batches, rollback and committed-count-only logging. Public
site facts expose the configured retention period for the privacy notice.

## Validation

- The initial route regression returned 404 before implementation.
- Initial endpoint, retention, authorisation and lifecycle group: 46 passed;
  16 lifecycle fixture failures exposed a missing new setting in its synthetic
  `SimpleNamespace`. The corrected lifecycle and affected public submission
  group passed all 53 cases.
- The subsequent enquiry/fence/public-policy group passed 31 tests, with 95%
  combined statement/branch coverage across six affected enquiry modules.
- A final 23-case endpoint/authorisation group passed, including successful direct
  reads and rejection when the session expires during a private read.
- Strict mypy passed across 1,603 source files. Ruff, formatting, all three import
  contracts, Bandit on new boundaries and the existing file-length check passed.
- Frontend API generation, whole TypeScript check, focused ESLint and Prettier
  passed. The coordinator's integrated KAN-169 run passed all 31 tests across
  site facts, the enquiry workspace and adjacent administration/navigation.
- A fresh independent read-only review found no actionable issue in the
  transaction, authorisation, expiry and privacy boundaries.

Full integrated CI and PostgreSQL verification remain pending. KAN-166 supplies
the 0093 storage migration; this ticket adds no migration. The privacy wording
still needs the controller's details and approval. No real enquiries were used,
no operator database was migrated and no production settings were changed.

# Selected original evidence assets

Implementation contract and acceptance record for E9, 7 September 2026.
The selected re-upload path is implemented locally. This does not reduce the
full expansion scope. ADR 0014 remains authoritative.

## Current evidence and first end-to-end path

The import worker verifies SHA-256 against submitted bytes. Internal
`research_import` and `research_media` evidence freezes `original_sha256` in
attributes. The regular evidence content hash identifies extracted content;
`sample_sha256` identifies a sanitised frame. Neither substitutes for the original
file hash. Temporary inputs discard original bytes and expire after 15 minutes.

First provide deliberate original attachment to an exact report version and
evidence label. An operator re-uploads the original and records a bounded
permitted-use statement. The server resolves an eligible internal-import source,
one valid original hash, source/event identity and immutable version itself.
It computes the submitted-byte digest and rejects mismatches. No URL fetch,
parser invocation, shared event insertion or implied authenticity is involved.
The statement records the operator's declaration, not verified legal permission.

This initial path must not be described as universal web-asset capture. Later
source-specific retrieval and explicit retain-at-import integration need their
own original-byte provenance, scope and permitted-use controls.

## Bounded delivery decisions

The first implementation uses two requests: reserve an attachment using JSON
metadata, then upload raw bytes to that reservation. The permitted-use declaration
stays in the authenticated request body. Reservations are admitted before byte
intake; uploading does not hold a database lock. The server keeps the frozen
source filename and media type as provenance, even if the local file was renamed.

An original can contain from one byte to 8 MiB. Active assets and pending
reservations share personal limits of 64 records / 64 MiB, team limits of
256 records / 256 MiB, and global limits of 4,096 records / 1 GiB. A team asset
counts against its team, rather than the uploading member's personal allowance.
At most two reservations can be pending globally. Reservations expire after
two minutes; chosen retention is 1–90 days, defaulting to 30 days. These limits
are admission limits, not an invitation to evict another scope's evidence.
Deleting or expiring an asset immediately releases its byte allowance. Its
scrubbed lifecycle record still consumes one record slot for 30 days, after
which cleanup removes it. Failed or abandoned reservations follow the same
policy. This bounds repeated reservation/deletion churn without removing
another scope's history, but record capacity does not reset on deletion.

The existing selected evidence builder will accept original asset IDs alongside
claim and identity revision IDs. A package can contain originals alone, with
at most 20 selected items in total. Original bytes have a 24 MiB aggregate limit;
the combined package has a 32 MiB uncompressed limit, including metadata and
manifests. Packages without originals keep the existing 8 MiB limit. Overflow
must fail explicitly. Generated `.bin` archive members and download names keep
untrusted source filenames out of filesystem paths and response headers.

These bounds describe the selected re-upload path. Acceptance evidence and
remaining limits are recorded below.

## Required implementation and acceptance

- Domain: immutable attachment identity, version/evidence anchor, hash/byte count,
  media type, original display name, uploader/time, permitted-use declaration,
  expiry and active/deleted/expired lifecycle state.
- Storage: dedicated bounded transactional blob records with metadata and minimal
  tombstones. No filenames become paths. Add tested migration and explicit
  parent-report deletion cleanup; no operator database migration by implication.
- Admission: current session and report write permission before reading bytes;
  bounded streaming, time and concurrency reservations; release locks during the
  upload; fresh session/scope/evidence/quota checks before commit. Enforce count
  and byte limits at personal, team and global levels without cross-scope eviction.
- Lifecycle: explicit deletion and expiry remove blob bytes while recording the
  transition. Expired/deleted records cannot be downloaded or exported. Document
  that independent backups may retain historical copies.
- UI: exact selected evidence, original-byte match result and permitted-use note;
  deliberate retain/delete actions and storage/expiry disclosures. Preserve
  private state clearing on account, access and report-version changes.
- Delivery: authenticated attachment-only download, safe generated filename,
  inert media handling, byte-hash verification and final current-access check.
- Export: deliberately selected immutable asset IDs, bytes verified from storage,
  generated member names, versioned manifest and final access/lifecycle recheck.
  Existing packages cap uncompressed content at 8 MiB, including report files.
  Specify and test an aggregate asset/package budget rather than silently omitting
  originals or pretending a full 8 MiB source always fits that package.

Required regression cases include wrong bytes, original-versus-content/thumbnail
hash confusion, duplicate/malformed frozen attributes, foreign scope/version,
identical hashes in separate teams, revocation during upload/export, reservation
races/cancellation, expiry/deletion, transactional parent cleanup and aggregate
ZIP overflow. Complete one connected domain/storage/service/API/UI/download/export
milestone before claiming this E9 requirement delivered.

## Implemented path and verification

Domain, migration 0027, transactional storage, current-session service, raw
upload API, scoped report UI, attachment download and selected evidence-package
export are connected. Internal session-family binding is excluded from public
metadata and exports. The proxy and exact API upload routes both admit bounded
original bodies; authorisation precedes body consumption. A two-minute upload
lease covers the 60-second combined intake and final-retention timeout.

Verification on the final source:

- 84 tests passed against an isolated loopback PostgreSQL 17.10 instance,
  including real concurrent reservation/consume checks, schema parity,
  preservation of existing reports, empty downgrade/re-upgrade and refusal to
  discard retained original bytes. Log: `data/original-assets-postgres.log`.
- 30 final SQLite checks passed, including eight races using independent
  connections to a file database, delivery/cancellation and bounded export
  admission through final checks. Log: `data/original-assets-recheck.log`.
- 52 compatibility checks passed for request limits, imports, translation
  lifespan and existing report/annotation documents and exports.
  Log: `data/original-assets-compatibility.log`.
- 175 frontend tests passed across 37 files with two workers, including
  original retention, renamed files with empty browser MIME, mismatch cleanup,
  cancellation, read-only controls, selection and private-state reset.
  Log: `data/original-assets-frontend-final.log`.
- Mypy checked 558 files; Ruff, both architecture contracts, configured Bandit,
  scoped ESLint, TypeScript/build, file-length and whitespace checks passed.
  Caddy configuration validation passed in a disposable container. The existing
  frontend bundle-size advisory remains.
- Focused independent security/code review has no unresolved blocking findings.
  Review prompted fixes for original MIME handling, admission before blob reads,
  retaining export capacity through final checks, session/lifecycle ordering,
  upload disconnection and bounded tombstone history.

The first broader SQLite run had 76 passes and two new team-fixture failures;
the fixtures were corrected and all affected checks passed. An earlier frontend
run timed out in an existing lazy-page test under load; the bounded final run
passed all 175 cases. These are focused acceptance runs, not a new full-suite
coverage measurement. No browser/GPU check, real provider/model call, operator
database migration or deployment is claimed. The disposable PostgreSQL instance
was removed after acceptance. Backup/restore acceptance for retained originals
and wider original-source retrieval remain open.

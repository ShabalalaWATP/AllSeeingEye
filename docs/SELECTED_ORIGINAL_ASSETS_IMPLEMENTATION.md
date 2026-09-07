# Selected original evidence assets

Implementation contract for E9, 7 September 2026. This does not mark retention
implemented or reduce the full expansion scope. ADR 0014 remains authoritative.

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

# ADR 0008: Bounded semantic search of saved reports

Status: implemented and refined by [ADR 0010](0010-teams-and-access.md),
6 September 2026. Refines ADR 0002's optional pgvector proposal for the current
single-API-process application. The team-isolation update replaces the original
shared-read library and caller-driven retention assumptions below.

## Context

Semantic search is a Phase 6 requirement. The application uses SQLite for local
development and PostgreSQL under Compose, and its durable tier deliberately
excludes raw live events. The operator needs useful retrieval from a small saved
report library without another service, a PostgreSQL-only extension or a growing
feed archive.

## Decision

Store one JSON embedding per report in `report_embeddings`, behind the
`ReportEmbeddingRepository` port. Each row identifies the report version and a
fingerprint of the profile id, endpoint and model. A portable application-layer
cosine comparison searches up to the caller's latest 1,000 visible reports; no pgvector dependency
is introduced. SQLite and PostgreSQL use the same repository contract.

Indexing is explicit and requires an enabled model profile with the `embeddings`
role and an available encryption key. Each operation embeds at most eight saved
reports, using at most 6,000 characters of report title and assessment text per
report. Vectors must contain 1 to 4,096 finite numeric dimensions with non-zero
magnitude; they are normalised before storage and comparison. Queries contain
1 to 500 characters and return at most twenty results.

Index storage is capped at 1,000 vector rows globally. The report id is the
primary key, so version updates replace a vector rather than adding history.
Capacity is checked before embedding calls. A full index refuses new slots
without evicting another team's entries; existing entries remain searchable.
Global maintenance removes orphaned or superseded rows, independently of the
caller's visible report set. Model/profile changes allow existing report slots
to be reindexed rather than requiring more rows.
Rows are used only when both the stored version and profile fingerprint match
the current report and selected embedding profile. Deleted reports disappear
through the foreign-key relationship. Indexing checks the current version again
before saving; searching re-reads current reports after the outbound request.
Changing a model or profile requires re-indexing. Key rotation alone does not
change the embedding space.

One process-local lock covers indexing and querying. Model calls are limited to
30 per user and 60 globally per hour, and usage outcomes are recorded. Embedding
responses use identity encoding, a 2 MiB streaming cap and a 30-second endpoint
deadline; the application also bounds the overall call. Redirects and provider
error excerpts are refused. Administrators may select a local model endpoint,
which remains an explicit trust boundary.

Access follows the current report library: personal reports require creator or
administrator access; team reports require current membership or administrator
access. Index status, counts, results and candidate selection are caller-scoped.
Visibility is rechecked after outbound work, and index writes use the shared
authority guard before saving. Indexing one caller's library cannot delete
vectors belonging to reports outside that caller's scope.
No live event, social post or uncited feed archive is indexed or persisted by this
feature. It reuses already saved assessment text.

## Consequences

- Search storage and comparison work are bounded by constants, not feed volume.
- No extension or additional infrastructure is needed for SQLite or Compose.
- Search may require repeated explicit index batches. It considers the caller's
  newest 1,000 visible reports and only valid stored vectors, not every historical
  report or older version. The shared storage cap may prevent new slots until
  obsolete records are removed; it does not promise space per team.
- Report text and queries reach the administrator-selected embedding endpoint.
  A local endpoint keeps this processing on the host or LAN; configuring an
  external provider is an operator choice, not a service added by the app.
- JSON vectors and a linear comparison are suitable for this bound, but they are
  not a scalable substitute for an indexed vector database. Revisit pgvector only
  with measured library size or latency evidence and a separate storage decision.
- Locking and budgets assume one API process. Multi-worker deployment requires
  shared coordination and a new operational design.

Scripted gateway and repository tests cover the feature; current SQLite and
PostgreSQL execution evidence is recorded in the improvement plan. Real-model
quality and representative-load measurements remain separate verification
gates; this decision is not evidence that those operational checks ran.

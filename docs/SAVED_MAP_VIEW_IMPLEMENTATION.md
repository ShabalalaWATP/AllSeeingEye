# Saved research map views

Status: implementation in progress. This refines E5/E9 of the full research
expansion plan and ADR 0014; it does not mark saved views as delivered.

## Operator flow

Open a frozen report's evidence map, set the camera, projection, filters and
selected evidence, then choose Save view and give it a title. A save captures an
immutable revision tied to that exact report version. Opening an older revision
must restore its state even after the report or view has a newer version.

File selection remains local. Saving an imported overlay explicitly uploads its
canonical geometry into the report's personal or team scope. Show that scope and
upload disclosure before Save. Do not upload automatically on file selection.
The team area remains a sharing facility, without assignments or review queues.

## Persistence and access contract

Use dedicated map-view and revision records. A view has a fixed parent report,
creator, scope and latest revision reference. Each immutable revision has its own
identifier, sequence, title, schema version, canonical state, content hash,
creator/time and resolved report-version identifier. The server resolves the
submitted report/version pair; clients cannot bind an unrelated version UUID.

Create and update submit complete state. Update also supplies the base revision
identifier; a stale base returns conflict rather than overwriting another save.
Archive hides the view from ordinary lists without rewriting its revisions.
Report deletion must explicitly handle dependent views/revisions, including
SQLite configurations where foreign keys alone do not provide cleanup.

Every operation checks current session, parent report access and view scope.
Apply visibility before counts and pagination. Writes use the existing shared
administration guard, account lock and write policy. Membership revocation,
account deactivation and archived teams retain their existing semantics.
Responses are no-store; no view data enters public SSE or the live event store.
Exports resolve an exact revision and recheck access before returning bytes.

## Canonical state

- Camera centre, zoom, bearing and pitch; projection; allowlisted basemap ID.
- Source filters, publication cutoff and explicit handling of unknown dates.
- Selected evidence reference anchored to the frozen report version.
- Canonical AOI and overlay geometry, distinct from simplified display geometry.
- Overlay source, dataset date, attribution, declared precision and visibility.
- Dataset/catalogue release references, hashes and display-transform version.

Validate geometry again on the server. Preserve the existing 5 MiB, 2,000-feature
and 100,000-vertex bounds, plus bounded revision storage quotas. Reject arbitrary
provider URLs, alternate CRS declarations and unsupported geometry. Keep polar
coordinates canonical and disclose Mercator's display limit. Wrapped polygons
require valid pre-split geometry until a separately verified splitter exists.

Copernicus display footprints currently lack enough retained catalogue metadata
for reproducibility. Extend that boundary before saving those layers. A modern
basemap is not historical imagery. Missing old datasets must be shown as missing,
never silently replaced by a current release. Hashes identify saved bytes; they
do not establish authenticity.

## Required acceptance

- Save/reload restores camera, filters, selection, geometry and labels in both
  projections. Restoring selection must not override the saved camera.
- Consecutive saves create immutable revisions; stale concurrent saves conflict.
- A revision referencing report version 1 still resolves version 1 after version 2.
- Invalid, oversized or computationally expensive geometry is rejected before
  storage; canonical and display geometry remain distinct.
- Cross-team reads, list counts, writes and exports fail without leaking data.
  Revocation clears private rendered layers and cancels pending client work.
- An edit during export cannot change the exported revision. Revocation/deletion
  before byte release prevents download.
- Missing source releases are explicit; local import alone never uploads data.
- Real WebGL checks cover globe/Mercator restoration, poles, antimeridian and
  camera movement. Mocked engine tests are supporting evidence only.

## Current progress

The shared engine camera/viewport interface is implemented, with 28 focused tests,
TypeScript and scoped lint passing. Real WebGL acceptance remains pending. A regression
reproduced canonical GeoJSON labels being replaced on reload; the parser now
retains its own bounded label field and truncates by Unicode code point. The
frontend geometry suite passes 14 cases, including a shared topology processing
limit. Server geometry and state validation passed 111 cases with 96.51% scoped
coverage. The repository and report-deletion integration passed 10 cases, including
disposable SQLite migration checks. Migration `0024` creates view/revision tables;
it has not been applied to the operator database. Lists fetch summary columns only.

Storage limits are defined as 100 views per personal/team scope, 100 revisions per
view and 100 MiB of charged revision content per scope, including archived data.
The repository exposes usage accounting; application enforcement under the shared
write guard still needs connecting. No end-user save endpoint is exposed yet.
Application access/quotas, API wiring, saved-view controls, AOI research launch,
exact-revision map export and PostgreSQL acceptance remain outstanding.

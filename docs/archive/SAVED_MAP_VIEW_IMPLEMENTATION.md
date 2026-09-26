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
The application now enforces these quotas under the shared write guard. Its
current-session checks cover list, read, create, revise and archive. A personal
view inherits its report owner's scope even when an administrator creates it;
team views inherit the report team and retain the contributing creator.

The API exposes create/list at `/api/map/views`, latest read/revise/archive by view
ID, and exact read at `/{view_id}/revisions/{revision_id}`. Each edit supplies its
base revision and receives 409 if stale. Saved state is bound to the exact report
version and evidence hash, excluding later archive-link updates. Map responses,
including validation/authentication failures, are no-store. Save routes admit a
6 MiB state envelope plus 16 KiB overhead; other JSON routes retain the 64 KiB cap.
The proxy allows a bounded 7 MiB outer envelope on map-view paths. The Caddy
configuration validated in a disposable local container, without deployment.

Seventeen service tests passed with 90.96% scoped coverage; 18 API tests passed,
including a valid overlay above 64 KiB and fresh authentication before geometry
validation. Sixteen body-limit/security-header tests passed. Saved-view controls
are implemented with acceptance work below; AOI research launch and exact-revision
map export remain unfinished. PostgreSQL
upgrade to the current head and all 45 API/service/repository/cleanup cases passed
on a disposable server, which was removed afterwards. A file-backed SQLite race
test also passed: two simultaneous saves cannot both claim the last scope slot.
The same concurrent last-slot test passed against a second disposable PostgreSQL
server, which was removed afterwards. Frontend integration review found issues in
overlay import state, authority invalidation and camera/filter restoration. These
are fixed, including delayed file reads racing with intervening overlay edits and
lower-bound-only date filters. All 23 focused frontend cases, full TypeScript and
scoped ESLint checks passed. The subsequent full frontend suite passed all 698
tests in 124 files: 95.79% statements, 90.11% branches, 94.52% functions and 96.99%
lines. Production build, formatting and configured Bandit passed. Wider map
export/source reproduction and complete WebGL acceptance remain unfinished.

The full backend run completed with 2,197 passes, 14 skips and six failures, at
96.19% coverage. Five failures asserted superseded PDF warning text, and one
catalogue fixture lacked the current planning/replan interface. After updating
those test assumptions, all 18 cases across the PDF/font/catalogue suites passed.
No production fallback or coverage threshold was weakened. This is a full run
plus targeted repair verification, not a second full backend run.

A synthetic browser harness exercised the real MapLibre/deck.gl components in
Chrome on Intel Iris Xe graphics (ANGLE Direct3D11). Both projections rendered;
a saved flat-map view reloaded, and a manually panned camera survived close/reopen
with identical saved coordinates. At 390 pixels there was no horizontal overflow.
Simulated access invalidation removed both canvases and the private content.
This used fixture API responses, not an operator account or database. It does not
establish full pole/seam restoration, performance budgets or source reproducibility.
Screenshots are local artefacts under `output/playwright/saved-map-*.png`.

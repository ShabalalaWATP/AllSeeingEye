# Map workspace implementation

Status: implementation, focused regressions, independent review and local browser
verification are complete on `codex/map-workspace-improvements`. Final frontend
coverage, repeated static checks and CI results are pending.

## Scope

Connect map tools through reusable geometry and saved, authorised workspace documents.
Keep map input ownership, geometry validation, research disclosure and account/team
boundaries explicit. Preserve existing report maps and radio models.

## Milestones

- [x] Fix research draft loss and in-map search navigation; correct research copy.
- [x] Group and search tools; pin favourites; separate navigation; resize/collapse inspectors.
- [x] Add named drawing collections, geometry editing, undo/redo and validated interchange.
- [x] Add authorised personal/team workspace documents with revision conflict checks.
- [x] Reuse selected geometry for research; preview retained evidence and source capabilities.
- [x] Preserve exact polygons in reusable areas and supported monitoring.
- [x] Save and compare radio studies; enter precise sites; inspect linked profiles and constraints.
- [x] Add bounded terrain profile/visibility and coordinate/corridor tools.
- [x] Evaluate published propagation model integration and record evidence-based limits.
- [x] Add an attributed external nuclear-effects educational reference.
- [x] Complete integration, focused regression tests and independent review.
- [x] Verify desktop and mobile interaction in the local browser.
- [ ] Complete final full frontend coverage, repeated static checks and CI.
- [x] Update reader guides and development story with implemented capabilities and limits.

Checked implementation items do not imply a production release or measured radio
accuracy. Release verification remains separate from the local checks below.

## Verification evidence

- The combined new backend regression run passes: 81 tests.
- Backend Ruff lint and formatting pass. Mypy passes across 1,360 source files;
  all three backend import contracts pass.
- Frontend type checks, production build and lint have passed. Final repeated
  static checks and the full frontend coverage run remain pending.
- Repository source-file length checks pass.
- Local browser checks pass at 1600 × 1000, 390 × 844 and 320 × 568, using normal
  pointer interactions, with no fresh browser errors observed.
- Independent review corrections cover measurement input ownership, mobile
  overlap, an area-of-interest research race and document payload limits.
- Final CI and an authorised deployment have not been verified.

These checks exercise implementation behaviour. They do not establish live
provider coverage, real-model research quality or measured RF performance.

## Implemented scope

The shell has a grouped searchable chooser, four favourites, resizable desktop
inspectors, mobile bottom sheets and an object/result list. Drawing collections
support names, notes, colours, locks, point/vertex editing, bounded undo/redo,
GeoJSON interchange and saved personal/team documents. Both drawing and radio
libraries expose explicit pagination. Revision checks reject conflicting updates.

Area research preserves its draft between tool changes, previews the map's loaded
evidence, and hands the same adopted boundary to research, reusable areas and
supported precise-location monitoring. Accepted research jobs continue outside
the inspector. RF studies retain inputs, frozen summaries and bounded terrain
evidence; reopening requires a fresh analysis for detailed overlays. Directional
link assumptions use an explicitly idealised horizontal antenna pattern.

Terrain profiles, sampled ground visibility, WGS84 coordinate conversion and
corridor previews are implemented. Dense routes require an explicit reviewed
simplification before corridor research. The educational panel opens an external
reference without including workspace coordinates or questions.

## Follow-up work

- [ ] Integrate ITM only after the validation and execution requirements in
  [radio modelling and terrain evidence](RADIO_MODEL_EVALUATION.md) are met.
- [ ] Assess licensed higher-resolution terrain and land-cover/building data.
- [ ] Evaluate measured antenna-pattern input and independently sourced field validation.
- [ ] Evaluate persisted historical replay and comparison as a separate storage decision.
- [ ] Consider additional hazard-exposure tools only with suitable dated datasets.

These integrations are not shipped by the current map workspace change.

## Engineering boundaries

The shell owns presentation and focus. The coordinator owns input routing. Drawing
commands and geometry validation remain pure where possible. Dedicated services own
document persistence, radio study handling, terrain requests and research jobs.
Storage accepts bounded user-authored artefacts, never an unbounded archive of raw
live observations. Reads, writes, exports and historical revisions retain scope checks.

## Acceptance

An operator can draw and save an area, switch tools without losing a research question,
inspect available evidence, and use the same geometry for a report. A radio study can
be saved, reopened and compared with a changed configuration without losing its baseline.
Panels leave usable map space on mobile. Search and browser navigation open the intended
tool. Account/access changes clear transient work and prevent stale responses restoring it.

Test geometry bounds, invalid rings, date-line behaviour, authority transitions, revision
conflicts, obsolete requests, keyboard/touch input and projection switching. Published RF
reference tests establish implementation agreement, not field reception accuracy.

## Deliberate limits

The educational reference does not implement an in-house nuclear-effects model or transfer
map coordinates to an external service. New radio propagation models require published
reference validation and bounded native execution before exposure. Full historical event
replay and new commercial terrain/population subscriptions are not introduced by this work.
Optional research ideas are tracked separately from implemented capabilities.

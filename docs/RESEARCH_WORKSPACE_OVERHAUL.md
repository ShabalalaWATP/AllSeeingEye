# Research workspace overhaul

Status: software implemented and locally verified, 11 September 2026. This is the
active research milestone, following the source connection work. Passing unit tests
does not establish geolocation accuracy or configured-model research quality.

## Outcome

One research workspace supports a question across selected countries, a bounded
historical interval, optional fresh web discovery, private photo geolocation and
recurring runs. Saved reports preserve outputs, evidence and limitations. The
map remains the default application view and teams remain a sharing boundary.

## Interface decisions

Visual thesis: a quiet dark research workbench with a clear question, compact
scope controls and readable results. Use the existing accent and typography;
avoid another dashboard of competing cards or decorative counters.

Content plan: Research contains New research, Geolocate a photo, Recurring and
Plans & areas. Saved reports contains previous outputs and exports. Live monitor
contains topical feed boards. Alerts contains notifications and threshold rules.
Existing routes and contextual report links remain usable.

Interaction thesis: choose the task first, reveal advanced controls when needed,
show the selected scope before collection and make cancellation and coverage gaps
visible. An unknown photo location is a valid result. Uploaded images are sent to
the configured AI only after an explicit disclosure acknowledgement.

## Delivery and acceptance

- [x] Add up to eight countries with strict scope validation, legacy single-country
  compatibility and preserved report/plan/follow-up scope. Never broaden malformed
  or plural scope into a worldwide query.
- [x] Support rolling or fixed ordinary research periods up to 730 days. Preserve
  specialist recorded-project history and show each provider's actual date limits.
- [x] Add optional real OpenAI Responses web search with bounded tool calls,
  scoped model routing, source controls, usage and cancellation. Preserve generated
  web context separately from original publisher evidence and corroboration scores.
- [x] Add actual multimodal photo geolocation with strict candidate/unknown output,
  expiring private inputs, destination-model routing and bounded processing.
- [x] Add weekly and calendar-monthly recurring research, month-end handling,
  exact saved scope/options, pause/resume and links to saved run reports.
- [x] Simplify primary navigation and explain each view's purpose. Preserve legacy
  routes and privileged administration separation.
- [x] Verify validation, authorisation, source controls, privacy, cancellation,
  date/scope round trips, monthly scheduling, browser interaction and rendering.
- [x] Run relevant integration, lint, typing, build, architecture, file-length and
  security checks. Record actual results and remaining model-quality limitations.
- [x] Update operator/API documentation and make a coherent local commit.
- [ ] Restore a working AI connection and evaluate actual web and photo results
  against known examples. Fixture tests do not establish research accuracy.

## Data and model boundaries

Historical selection does not create an archive where a source has none. Feed
snapshots and current registry context retain their limitations. Country selection
must not invent an event location. Multi-country collection shares bounded budgets.

Native fresh web search initially requires an administrator-configured compatible
OpenAI connection. Do not silently use another person's or team's connection when
the selected provider cannot search. Search answers are model-generated context;
their citations are discovery references, not independent verified evidence.

Photo analysis uses a sanitised image derivative, not the original file or its
private metadata. Do not send private media into public search. Candidate locations
remain unverified and include clues, contradictions and suggested checks. Model
quality and geography coverage require separate evaluation with known examples.

Recurring runs retain their owner/team access checks and save a new report. A
calendar-monthly run on day 31 clamps to a shorter month's last day without
changing the requested day in subsequent months.

## Operational blocker

The local OpenAI Luna profile is disabled and untested. Its encrypted credential
cannot be read because the original `ASE_ENCRYPTION_KEY` is unavailable. The
operator has been asked whether to restore it or authorise a new local key and
re-enter the OpenAI credential. Neither key nor profile was changed while that
answer was pending. OpenAQ live authentication succeeded independently.

The overall goal remains open until configured-model evaluation is possible.

## Verification evidence

- Combined backend integration: 196 tests passed for photo contracts, owner/session
  isolation, cancellation, receipt lifecycle, native web transport/persistence,
  country/date scope and recurring scheduling. Additional worker regressions and
  scoped coverage are recorded in the development story; no full backend-suite
  coverage claim is made.
- Backend Ruff, formatting, strict mypy (783 source files), both import contracts
  and scoped Bandit passed. File-length checks passed; the existing untouched
  380-line MapLibre engine remains a target-length warning.
- Frontend TypeScript, ESLint and production build passed. Changed-file formatting
  and subsequent test-edit lint checks passed after correcting formatting.
- Full frontend suite: 1,906 tests passed, with one existing performance benchmark
  skipped. The unchanged 90% coverage gate passed. Coverage: 95.40%
  statements, 90.67% branches, 93.35% functions and 96.58% lines. The first run's
  stale conflict-report request expectation was corrected for the explicit false
  web-search field; no production behaviour or threshold was relaxed.
- Browser checks used intercepted synthetic API responses in a separate Playwright
  session. At 1440 by 1000 and 390 by 844 they exercised research navigation,
  multiple countries, two-year scope, optional web search, photo controls and
  monthly day 31. Screenshots were inspected. No live report was submitted.
- Restarted the local API. Health and frontend login returned 200; unauthenticated
  photo analysis and input deletion returned 401. OpenAQ authentication was also
  verified independently; the AI connection remains blocked as described above.
- The [manual scoped security review](security/RESEARCH_WORKSPACE_REVIEW.md)
  reported no outstanding confirmed finding after corrections. A scan of proposed
  files found no configured local secret values. Test output, screenshots and
  runtime logs remain local verification artefacts outside the commit.

The software milestone is committed locally on `main`. No Git remote is
configured, so nothing was pushed. No production deployment took place. Live model
evaluation remains the unchecked acceptance item above.

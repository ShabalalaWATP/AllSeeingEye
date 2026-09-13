# Eye assistant

## Design

The assistant is a quiet black and cyan companion to the map, using the original
animated Eye without a launcher box, with ASK EYE directly below it.

The content sequence is a movable Eye launcher, a short question and explicit
search scope, a concise answer with evidence links, then a follow-up question or
deeper research. Coverage and source dates belong beside the answer.

Interaction uses direct pointer dragging with keyboard alternatives, a short panel
reveal, and a clear hover/focus response. Reduced motion removes transitions.
The wider launcher uses the same original flame and pupil motion as the login
page, with transparent compositing and room at both sides. Its small WebGL
instance is capped at 24 frames per second and pauses when the tab is hidden.
Reduced motion stops flames and pupil following. Graphics failure restores the
original captured frame, without a context-recovery loop or a map subscription.

Acceptance requirements:

- Available across authenticated pages; login and MFA gates do not mount it.
- Compact and expanded panels, and the wider launcher, stay inside desktop and
  mobile viewports. Expanding preserves the draft and in-flight response.
- Dragging moves the launcher without accidentally sending a click.
- Search retained public map data independently of visual layer toggles; allow
  an explicitly chosen current map area when an actual area is available.
- Explain cache retention, unavailable sources and sampling. An empty result
  must not become a claim that nothing happened in the world.
- Use the administrator-selected connection and reasoning setting without an
  implicit fallback. A short answer has its own schema, separate from full reports.
- Validate citation syntax and membership against server-selected evidence.
  Valid references establish traceability, not factual accuracy.
- One bounded, cancellable model call per question, with admission limits,
  session checks before and after, and secret-free operational usage accounting.
- Active chat remains temporary browser memory. Clear it on logout,
  identity/access changes and explicit reset. A user may explicitly save a
  private, bounded transcript snapshot, resume it or delete it. Saved answers
  are historical copies, not newly verified evidence. A bounded, server-owned
  continuation can reuse a recent cited packet for a referential follow-up;
  generated claims and saved copies are never promoted into evidence.
- No raw feed archive, new dependency, external messages or model configuration
  changes are required.

## Using the Eye

Sign in and click the Eye at the lower right. Drag the launcher to move it;
keyboard arrows also move it, Shift increases the step, and Home resets it.
The panel fits beside the map and stays inside small screens. Expand in its
header opens a window across most of the screen with a small outer margin;
Restore returns to compact size. Minimising preserves an in-flight request,
while Stop cancels it. Escape dismisses the panel while focus is inside.

Choose all retained map sources, the current geographic view, or a selected map
item. Set a reporting window or leave time automatic; the natural-language
parser recognises a small set of relative periods, including today and
yesterday on the Europe/London calendar. The Source types control narrows the
event categories and camera, infrastructure or doctrine references. Hidden
visual layers remain searchable. Source links open the publisher's page.
Show on map selects a still-visible cited record and opens its inspector, or
centres on the source point when that layer/record is unavailable. It does not
turn on visual layers. The Research and Subscription links open reviewable
drafts, never start collection or a schedule automatically.

Answers separate observations, assessments and gaps. Sources and coverage shows
candidate, matched and selected counts, source dates, feeds and sampling limits.
A valid citation means the referenced record exists in the supplied context;
it does not prove that the claim is correct or independently corroborated.

## Scope and limits

The search uses retained events across feed categories, cached public camera
metadata, the packaged infrastructure inventory and a short static UK/NATO
doctrine reference catalogue. It does not refresh providers, inspect camera
images or streams, search GNSS or Cloudflare Radar aggregates, read saved
reports or run fresh web research. Data availability depends on connected feeds
and retention. Place mentions are not verified incident coordinates. Doctrine
sources guide methodology but are not evidence that a world event occurred.

Retrieval applies an explicit publication-time interval in the event store before
paging and scans up to 900 records per event category to find up to 90 matching
records. Camera and infrastructure inventories have their own per-group caps.
Answers receive at most 30 records, six per publisher group, within a
32,000-character context. These limits can omit relevant records; counts are
bounded samples, never world totals. Undated camera and infrastructure records
are excluded from explicit time-bound searches. Current map scope uses the
engine's geographic bounding box, not a drawn polygon. Selected-item scope
refers to the selected event, camera or site.

Chat retains eight turns in temporary browser memory and sends at most four
previous user questions. A referential follow-up may reuse the previous
server-selected source packet for 20 minutes when scope and account version
still match. The token is opaque, held only in process and lost on a server
restart; prior generated text is never evidence. Expired or cross-account
references fail closed. Unsupported exclusions and ambiguous periods ask for
clarification rather than silently broadening the search. New chat, logout and
identity/access changes clear the active conversation.

Saved chats are opt-in private snapshots (up to 30 per account, eight answered
turns and 64 KB each). The server strips model and continuation metadata and
returns a stale-evidence notice. Resume does not restore a trusted evidence
token or automatically repeat a paid model request. Source links in a saved
copy may have changed or disappeared; recheck them before relying on the answer.

## Request and access contract

`POST /api/assistant/answer` accepts a question, bounded prior questions, an
explicit scope, optional publication-time range and optional source-category
allowlist. It returns plain-text paragraphs, server-owned evidence links,
interpreted scope, coverage, generation time and a short-lived continuation
reference. The response also carries operational model data, hidden in the
ordinary reader interface. The checked-in OpenAPI schema and generated frontend
types define the complete contract.

The public UK PHIA Probability Yardstick and Common Analytical Standards are
attributed as methodology. MOD JDP 2-00 and NATO AJP references use original
short summaries and official/publication links only; the assistant does not
ingest or redistribute their full PDFs. Source reliability, information
credibility, assessed likelihood and analytical confidence remain distinct.
The app's source matrix is its own policy, not an official NATO scoring
algorithm or an accredited intelligence assessment. Citation membership and
basic numeric support checks cannot prove full semantic accuracy.

The assistant uses the account's personal/global assessment-model assignment.
There is no implicit model or reasoning fallback and no team selector in this
popup. The current development connection remains Luna with Max reasoning and
the existing 32,000-token output allowance. That allowance includes reasoning.

Each question has a 120-second deadline, one model call, one active call per user,
two active calls across the process and six requests per user per minute. Empty
results and clarification responses do not call the model. A refreshed session
does not automatically replay a paid question; the user can submit it again.

Current account, session and source permissions are checked before model work
and again before release. No database lock crosses a provider request. Usage
stores bounded operational metadata, never raw questions, answers or feed text.
The response is private and not cached. A local popup error boundary allows
restarting the assistant without remounting the map. The bounded Eye animation
introduces no live-feed subscription, new dependency or additional model call.

## Verification

On 11 September 2026, 146 backend assistant tests passed with 96.04% focused
branch coverage, above the unchanged 90% gate. Source, access, cancellation,
accounting, schema and source-selection regressions are included. Separately,
77 frontend integration tests passed across the assistant,
shared API client, research/admin shells and globe. Browser checks covered pointer
and keyboard movement, current-view scope, follow-up requests, evidence display,
Escape and layouts down to 320 by 568 pixels. Browser API replies were fixtures;
real model acceptance is recorded separately below. The production build, full
frontend type checks and changed-file lint/format checks passed.

The first public-feed check collected 285 USGS records but returned no sources:
retrieval had mistaken answer-format instructions for source entity constraints.
No model request was made. A regression now covers that exact question alongside
normal wording, explicit place constraints and both quick-question buttons.

A second check collected 286 records and the normal application use case received
a three-paragraph answer from the configured Luna Max profile in approximately
8.6 seconds. All six citations resolved. The magnitude and depth ranges matched
the six supplied records. Content review rejected a jurisdiction claim: the model
treated a relative place label as an incident state. Source IDs alone did not
catch that error. The original result is preserved in ignored local acceptance
artefacts. The prompt now requires explicit incident administrative metadata and
preserves distance/bearing labels when jurisdiction is unknown.

The final acceptance check refetched the same six public USGS observations and
supplied only those six earthquake records to the normal use case. Luna Max
returned three paragraphs in 20.7 seconds, with all six source references valid.
Both magnitude/depth ranges and automatic status matched the records. Exact
relative location labels were preserved, with no unsupported jurisdiction claim;
the supplied-record count and one-source coverage limitation were explicit.
This is a narrow six-record content check, not broad retrieval-quality evaluation.
The two model calls completed without token exhaustion or citation validation
errors. Model, reasoning and token settings were unchanged.

Full long-report acceptance remains open. These checks do not establish general
factual accuracy, exhaustive source coverage or browser login/MFA live acceptance.

On 13 September 2026, the expanded Ask Eye backend regression selection passed
98 tests with coverage collection disabled for the scoped run. Six saved-chat
API and migration tests passed, as did 29 focused frontend tests spanning chat,
saved snapshots, map selection and draft navigation. App TypeScript checking,
changed-file lint, import-layer checks, Ruff, mypy and the production frontend
build passed. The full backend coverage gate is meaningful only on the full
suite; a prior assistant-only selection passed its 155 tests but failed that
global gate because it covered 40% of the entire application. No full-suite
coverage or live model/browser acceptance is claimed for this extension.
The local development database advanced from migration 0033 to 0034, and the
running local API returns 401 for an unauthenticated saved-chat request, showing
the route is mounted and guarded.

The local backend was restarted with the feature. Health and the frontend login
returned 200; an unauthenticated assistant request returned 401. Full backend
typing (799 files), both import contracts, scoped Ruff/Bandit, frontend typing
and file-length checks passed. The existing MapLibre file-length warning and
large map/video bundle warnings are unchanged. No new full-app coverage figure
is claimed. Configured plaintext secrets were absent from non-ignored source.

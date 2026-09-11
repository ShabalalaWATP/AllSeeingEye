# Eye assistant

## Design

The assistant is a quiet black and cyan companion to the map, using the actual
Eye brand capture and leaving the working surface visible.

The content sequence is a movable Eye launcher, a short question and explicit
search scope, a concise answer with evidence links, then a follow-up question or
deeper research. Coverage and source dates belong beside the answer.

Interaction uses direct pointer dragging with keyboard alternatives, a short panel
reveal, and a clear hover/focus response. Reduced motion removes transitions.
The launcher uses the existing original Eye frame capture without another WebGL
context, animation loop or map subscription.

Acceptance requirements:

- Available across authenticated pages; login and MFA gates do not mount it.
- A compact panel and launcher stay inside desktop and mobile viewports.
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
- Chat remains temporary browser memory. Clear it on logout, identity/access
  changes and explicit reset. Prior questions provide conversational context;
  old generated claims are not promoted into evidence.
- No raw feed archive, chat database, new dependency, external messages or model
  configuration changes are required.

## Using the Eye

Sign in and click the Eye at the lower right. Drag the launcher to move it;
keyboard arrows also move it, Shift increases the step, and Home resets it.
The panel fits beside the map and stays inside small screens. Escape closes it
while focus is inside. Closing or stopping cancels the current request.

Choose all retained map sources, the current geographic view, or a selected map
item. Hidden visual layers remain searchable. Follow a source link to check its
publisher, or use Centre map here to move to a supplied point. This moves the
view without changing layer switches. Search deeper in Research carries the
question to the existing research form for scope review.

Answers separate observations, assessments and gaps. Sources and coverage shows
candidate, matched and selected counts, source dates, feeds and sampling limits.
A valid citation means the referenced record exists in the supplied context;
it does not prove that the claim is correct or independently corroborated.

## Scope and limits

The current search uses retained events across feed categories, cached public
camera metadata and the packaged infrastructure inventory. It does not refresh
providers, inspect camera images or streams, search GNSS aggregates, read saved
reports or run fresh web research. Data availability depends on connected feeds
and retention. Place mentions are not verified incident coordinates.

Retrieval takes at most 90 event candidates per category before text ranking,
100 camera records and 100 infrastructure records. Answers receive at most 30
records, six per configured publisher group, within a 32,000-character context.
These limits can omit relevant records; counts are bounded samples, never world
totals. Current map scope uses the engine's geographic bounding box, not a drawn
polygon. Selected-item scope refers to the selected event, camera or site.

Chat retains eight turns in temporary browser memory and sends at most four
previous user questions, never previous generated answers as evidence. Ambiguous
global follow-ups such as 'which of those?' ask for a selected item/view or a
repeated place rather than silently broadening the search. Unsupported exclusion
filters and complex phrasing ask for clarification rather than assuming an area. New chat, logout and
identity/access changes clear the conversation. Moving between authenticated
pages within the same workspace preserves it; changing shells remounts it.

## Request and access contract

`POST /api/assistant/answer` accepts a question, bounded prior questions and an
explicit scope. It returns plain-text paragraphs, server-owned evidence links,
coverage information, generation time and the model used. The checked-in OpenAPI
schema and generated frontend types define the complete contract.

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
restarting the assistant without remounting the map. The launcher introduces no
WebGL context, animation loop, live-feed subscription or new dependency.

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

The local backend was restarted with the feature. Health and the frontend login
returned 200; an unauthenticated assistant request returned 401. Full backend
typing (799 files), both import contracts, scoped Ruff/Bandit, frontend typing
and file-length checks passed. The existing MapLibre file-length warning and
large map/video bundle warnings are unchanged. No new full-app coverage figure
is claimed. Configured plaintext secrets were absent from non-ignored source.

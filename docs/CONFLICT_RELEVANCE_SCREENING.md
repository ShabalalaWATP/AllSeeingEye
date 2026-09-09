# Conflict relevance screening and source audit

Reviewed 9 September 2026. This is topic screening, not independent verification.

## Why the construction accident appeared

The GDELT adapter admitted CAMEO roots 14, 15, 17, 18, 19 and 20 as conflict
records. These include protests, force posture, coercion and assault as well as
fighting. CAMEO 173 includes arrests, charges and legal action. A code alone cannot
distinguish an industrial-accident prosecution from armed conflict. GDELT actor/code
descriptions are not original headlines. Feed ingestion had no LLM relevance check.

The [HSE account](https://press.hse.gov.uk/2026/09/09/two-companies-and-an-individual-sentenced-after-worker-crushed-by-two-tonnes-of-soil-in-trench-collapse/)
describes sentencing after a construction accident in June 2020. It is not a new
armed incident. The original GDELT row was not recovered, so the legal-action path
is an explanation of the defect, not a claim to have reproduced that exact row.
See the [CAMEO manual](https://data.gdeltproject.org/documentation/CAMEO.Manual.1.1b3.pdf).

## Delivered behaviour

- Unreviewed GDELT/machine-coded conflict points are hidden by default on both
  projections. **Unreviewed media signals** exposes pending/uncertain records for
  investigation, never known unrelated or context-only records as incidents.
- Trackers exclude unreviewed/rejected machine-coded incidents from activity
  totals. Curated regions remain labelled context. UCDP history is a separate opt-in.
- AI distinguishes armed conflict, civil unrest, military activity, context,
  unrelated and uncertain. Screened drills/protests cannot count as fighting merely
  because their original subtype was `fight`.
- Details show relevance, reason, supporting quotation and requested model. Original
  grades, subtype, coordinates and precision remain available. Metadata also retains
  provider, profile ID and revision. Relevance never raises a credibility grade or
  verifies an event's date/location. Excluded selections clear their highlights.
- Delayed grading merges only grading fields, preserving newer screening and
  translation. Pruned and revised records are not resurrected.

## Bounded background worker

Screening uses the existing global assessment model, never a team/person fallback
for shared evidence. Installations with no bindings retain legacy global selection.
Private bindings without a global binding leave screening unavailable. The source
coverage panel explains the state. Activate a tested global connection in the
administrator workspace to enable actual model calls.

Inputs are collected public RSS titles/summaries with outlet metadata. GDELT needs
an exact canonical URL match to collected source text. Tracking parameters and
fragments may be removed. URL slugs, generated CAMEO prose, inferred article bodies
and new HTML scraping are not evidence. Initial news triage uses the existing English
keyword check, including available title translations, which limits recall.
Previously screened items remain eligible after model/content changes. Missing
source text stays unreviewed.

One worker examines at most 5,000 retained candidate records per minute using the
cooperative reader. Filtering/join work runs off the API event loop. There is at
most one model call at a time, 10 texts per call, 300 title and 1,000 summary characters
per text, a 45-second deadline and a 4,000-output-token ceiling. The default is six
calls per clock hour per API process. Failed calls consume the allowance and receive
a 15-minute retry delay. Budgets/cache reset on restart; use one feed worker. Usage
purpose is `conflict_screening`. These limits do not guarantee a currency spend.

The 2,000-entry cache keys policy, connection generation and source text. Up to 100
matched records share a batch. Publication rechecks the global generation, enabled
sources, both canonical URLs, source/target hashes and current text. Source/model
locks are never held over an LLM request. Cancellation releases no verdict. Invalid
JSON and extra/missing IDs fail closed. Positive relevance needs an exact quotation
from supplied text, which checks textual grounding, not truth. Inputs remain untrusted
prompt data and cannot invoke tools or executable actions.

Optional settings in `.env.example`:

- `ASE_CONFLICT_SCREENING_ENABLED`, default `true`.
- `ASE_CONFLICT_SCREENING_CALLS_PER_HOUR`, default `6`, range `1..30`.

Raw events/verdicts remain bounded in memory. No new schema, dependency, private
upload input or historical event database was introduced.

## What OSIRIS actually does

At commit `11ecf488253c202714ab11709750b651c765e07b`, its
[conflict endpoint](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/app/api/conflicts/route.ts)
uses 15 curated regions, fixed severity and BBC World, Al Jazeera and NYT World RSS.
It matches title/description keywords, deduplicates exact titles, assigns the first
matching region and caches for five minutes. Some news points use synthetic offsets
and retrieval timestamps. This endpoint has no LLM relevance/factual verification;
its GDELT comment does not describe its implementation. GDELT has a separate endpoint.

ASE already adopted the useful overview/selection concept with its own catalogue.
It preserves source positions/dates and does not copy synthetic news locations,
fixed scores or a claim of AI verification. No OSIRIS code was copied.

## News coverage and priorities

All 29 configured non-social RSS feeds returned parseable entries in bounded
read-only probes on 9 September. This is accessibility, not proof of admin enablement
or continuous live collection:

- 14 outlets: BBC World, DW, France 24, Al Jazeera, Guardian World, Le Monde English,
  SCMP, Nikkei Asia, Times of Israel, Anadolu, Dawn, Meduza English, Ukrainska Pravda
  English and TASS English.
- Eight regional feeds: Meduza Russian, Mediazona, The Insider Russian, China
  Digital Times Chinese, HRANA Persian/English and IranWire Persian/English.
- Seven institutional/context feeds: FCDO news, UK/US travel advice, UN News,
  UN press, ReliefWeb and International Crisis Group.

FCDO news, UK/US advice, Crisis Group, DW and Nikkei had no recognised publication
timestamps in the sample. Updated/retrieved timestamps cannot become incident dates.
State-controlled outlets retain provenance; outlet count is not corroboration.

ASE has two of OSIRIS's three conflict RSS sources. NYT World RSS is a candidate
after intended-use terms review. The New Humanitarian's
[RSS directory](https://www.thenewhumanitarian.org/content/rss-feeds) returned a
working feed, but its [republishing terms](https://www.thenewhumanitarian.org/republish)
also need checking. Neither was silently activated. Approved
[ACLED access](https://acleddata.com/api-documentation/getting-started), already supported
by the connector, is a stronger next step than more general-news volume. Aggregators
and original publishers must not count as separate independent witnesses.

## Remaining acceptance

The local installation had no usable global assessment model when checked. No live
model quality result is claimed. Fixtures test protocol/admission, including the
supplied accident headline; they do not prove a deployed model classifies it correctly.
A reviewed multilingual benchmark for accidents, crime, strikes, sport, drills,
negation, historical references and genuine armed events is still needed before
claiming precision/recall. Exact-URL joins can leave most GDELT signals unreviewed.
Interactive browser/GPU verification remains blocked by the existing local policy.
Component/API tests do not establish visual or GPU behaviour.

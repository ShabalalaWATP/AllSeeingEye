# Research workspace

| View | Purpose |
| --- | --- |
| Map | Explore spatial observations and start research for a drawn area. |
| Research | Ask a question, open saved reports, read the daily briefing or reuse plans and areas. |
| Subscriptions | Schedule repeated research on a topic, conflict, disaster or area. |
| Geolocation | Compare up to six photos and assess candidate locations. |
| Economy | Explore markets, country indicators, economic news and daily cited analysis. |

Administration remains separate and restricted to administrators. Teams define
sharing and model destinations. Existing tracker/direction/warning routes and
contextual report links remain usable.

The top-bar profile icon opens identity, security and team sharing. Personal
settings contain appearance, time and region, research/report defaults, and links
to the source catalogue and alert rules. These preferences apply per user. See
[Economy and personal workspace](ECONOMY_WORKSPACE.md).

## Questions and scope

Enter a question and choose Basic, Deep or Advanced, the destination and up to eight
countries. No selected countries means worldwide. Choose a rolling period or a
fixed UTC range, with inclusive start and exclusive end. Ordinary intervals allow
730 days. This limits duration, not the age of a saved historical interval.

Inspect the collection plan for actual source coverage. Current RSS feeds cannot
supply two years of archives. Fresh headline research can match reviewed country
names in original titles or summaries, with exact source spans and an explicit
unverified-geography notice. It never assigns incident countries or coordinates
from the question. Spatial research retains its strict location requirements.
See [country subject matching](COUNTRY_SUBJECT_RESEARCH.md). OONI/AidData country-specific research currently requires one
supported country. Specialist recorded-project history keeps its separate policy.

Fresh web search is an explicit, separate opt-in. It sends the public question and
scope to the destination's compatible OpenAI connection. Generated context and
native citations appear separately from scored evidence. See
[fresh web research](FRESH_WEB_RESEARCH.md) for exact bounds and limitations.

Follow-ups preserve the original countries and fixed interval. Rolling windows
can move forward. Start new research to change the scope.

## Report types

| Type | Indicative narrative length | Research approach |
| --- | --- | --- |
| Basic | 500–900 words | Focused collection and the strongest relevant findings. |
| Deep | 1,200–2,000 words | Broader collection, fuller reasoning and challenge review. |
| Advanced | 2,500–4,000 words | Extended collection, competing explanations and synthesis. |

These are evidence-dependent targets, excluding references, not guaranteed lengths.
Sparse evidence produces a shorter report. Provider limits and schema bounds still
apply. More depth consumes more time and provider capacity. Existing saved `quick`
and `detailed` values mean Basic and Deep respectively; `advanced` is additive.
These choices also apply to area research, personal defaults and schedules.

## Photo geolocation

Open Geolocation in the left navigation. Old `/research/photo` links redirect to
`/geolocation`. Select the destination and choose up to six PNG, JPEG or WebP photos
together. Each permits up to 8 MiB, 8 megapixels and 8,192 pixels per edge, with no animation.
Optional questions and hints describe what to examine. Confirm
that the sanitised preview and supplied context may be sent to the configured AI,
then start analysis. The photos are labelled in order and sent in one model request.
Changing the set clears the result and requires fresh disclosure consent.

The vision call receives a sanitised preview of at most 512 pixels per dimension,
not the original filename, private EXIF or extracted OCR. Fine text and distant
details can be lost. It does not perform public reverse-image search. OpenAI and
Bedrock image payloads are supported, subject to the chosen model accepting images.

Results contain up to three unverified candidate places or an unknown result,
visible clues, contradictions, uncertainty and verification steps. Multi-photo
results include clues for each photo and a comparison across the set. The model
must not assume that every photo shows the same place. Hints are claims
to test. Candidate coordinates are not automatically added to the live map.

Create saved report preserves selected extracted text and visual findings with
model/hash provenance and uncertainty, without image bytes. Original uploads are
discarded after extraction; working previews and assessments expire after 15 minutes.
The combined analysis expires with its earliest parent photo; removing any parent
invalidates the derived receipt. Replace/remove cleans up working receipts.
Uploads run sequentially, and the server retains its global 8 MiB working-store cap,
so other active uploads may temporarily limit capacity. Returning to the tool retains only
bounded in-memory receipt references for cleanup. Pending report requests protect
their input until they settle. Account/access changes clear client references.

## Subscriptions

Create a normal research brief under Subscriptions: question, report type,
country scope, lookback, source choices and optional fresh-web search. A separate
timing panel sets when the brief repeats. The control panel filters active, paused
and attention-needed schedules; edit reuses the same composer. It shows the next
run, recent outcome and latest successful report. Changing settings preserves the
paused state until explicitly resumed. Lookback can use days, hours or the report
cadence default; editing preserves existing values. Daily, Weekly, Monthly,
3 monthly, 6 monthly and Annual runs are supported, alongside existing weekdays.
Longer calendar intervals use an anchor month. Times remain UTC throughout the year. Monthly day 31
uses February's final day, then returns to day 31 in March.

The server must be running. Each completed run saves a report in the selected
destination. Pause/resume retains options and history. Source coverage and access
are checked again each run. Optional evidence-change alerts use the existing
deterministic comparison. Changed scope resets its baseline. Company/domain
research requires a subject; expiring private media/document inputs cannot recur.

The primary navigation opens `/subscriptions`; old `/research/recurring` links
redirect there. Completed editions appear in Saved reports. This is in-app
delivery, not email or push delivery. New briefs suggest lookbacks of 1, 7, 31,
92, 184 or 366 days respectively; custom windows and existing schedules are
preserved. A long lookback cannot supply archives that providers do not offer.

Optional controls select a known conflict, hazard or saved area. A fixed area
replaces country, topic and collection-plan filters. Geometry is copied into the
subscription, so later edits to the saved area do not change the subscription.
Coordinate disclosure to source providers remains explicit.

Avoid repetition is enabled by default. Collection prioritises previously unseen
content while retaining unchanged evidence for context and corroboration. Up to
500 content fingerprints and the last non-empty successful edition are retained
per subscription. Empty or failed editions do not erase the baseline. Scope
changes reset it. Exact comparison cannot detect every paraphrase or syndicated
story; drafting guidance also checks dates and cautions against presenting old
facts as new. A quiet edition should say no material update was identified in the
sources checked, not that nothing happened. Current access is checked before
using prior evidence and before saving.

## Daily Live Monitor

Opening Daily briefing within Research ensures one personal Basic briefing covering the previous
24 hours of available conflict, disaster, humanitarian and news evidence. It uses
the durable research pipeline and saves a cited report. Multiple tabs and repeat
visits reuse the same job for 24 hours, including paused or failed jobs. The page
shows progress, a situation summary, latest developments, coverage limitations and
a link to the full report. Failed work has an explicit progress link rather than
an automatic retry loop.

The next briefing is requested when the page is visible at its refresh time or
on the next visit after expiry. It does not run daily while the page is closed.
Use Subscriptions for unattended recurring research. Hidden tabs pause
polling. Source and model availability determine the result; fixture tests do not
establish real-model briefing quality.

## Reusing map areas

The research tabs are New research, Saved reports, Daily briefing and Plans & areas. Running,
failed and paused work remains accessible through Research progress from Saved
reports. Plans & areas stores reusable geographic definitions. Open on map links
use `/?area=<id>` and fetch authorised geometry before focusing and drawing it on
the globe or flat map. Country areas are approximate extents, not country borders.
Closing the notice removes the outline; access changes hide private geometry.

The map's area-research tool can save a drawing's enclosing rectangle as a
personal reusable area, including boundaries crossing the antimeridian. It is
labelled as a rectangle, not an exact copy of an arbitrary polygon. These areas
can be used in subscriptions. Report-specific saved map views remain separate.

## Connection readiness

An administrator needs the server's persistent encryption key, an AI connection
and a successful connection test before activation for the intended destination.
A saved model name does not prove working vision or web access. Restore a missing
encryption key or explicitly decide to re-enter affected credentials before
replacing it. Actual research and geolocation accuracy need known-example evaluation.

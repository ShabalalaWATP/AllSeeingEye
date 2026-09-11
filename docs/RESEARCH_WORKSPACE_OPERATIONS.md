# Research workspace

| View | Purpose |
| --- | --- |
| Map | Explore spatial observations and start research for a drawn area. |
| Live monitor | Browse recent connected-feed activity by topic. |
| Research | Ask a question, geolocate a photo or configure recurring research. |
| Saved reports | Read previous outputs, inspect frozen evidence, compare and export. |
| Alerts | Review notifications and configure rules over feed activity. |
| Plans & areas | Reuse geographic areas and structured questions, within Research. |

Administration remains separate and restricted to administrators. Teams define
sharing and model destinations. Existing tracker/direction/warning routes and
contextual report links remain usable.

## Questions and scope

Enter a question and choose Quick or Detailed, the destination and up to eight
countries. No selected countries means worldwide. Choose a rolling period or a
fixed UTC range, with inclusive start and exclusive end. Ordinary intervals allow
730 days. This limits duration, not the age of a saved historical interval.

Inspect the collection plan for actual source coverage. Current RSS feeds cannot
supply two years of archives. Country-filtered graded evidence requires associated
geography: unknown-country articles are excluded rather than assigned a country
from the question. OONI/AidData country-specific research currently requires one
supported country. Specialist recorded-project history keeps its separate policy.

Fresh web search is an explicit, separate opt-in. It sends the public question and
scope to the destination's compatible OpenAI connection. Generated context and
native citations appear separately from scored evidence. See
[fresh web research](FRESH_WEB_RESEARCH.md) for exact bounds and limitations.

Follow-ups preserve the original countries and fixed interval. Rolling windows
can move forward. Start new research to change the scope.

## Photo geolocation

Open Research, Geolocate a photo. Select the destination and upload one PNG, JPEG
or WebP up to 8 MiB. Optional questions and hints describe what to examine. Confirm
that the sanitised preview and supplied context may be sent to the configured AI,
then select Analyse photo.

The vision call receives a sanitised preview of at most 512 pixels per dimension,
not the original filename, private EXIF or extracted OCR. Fine text and distant
details can be lost. It does not perform public reverse-image search. OpenAI and
Bedrock image payloads are supported, subject to the chosen model accepting images.

Results contain up to three unverified candidate places or an unknown result,
visible clues, contradictions, uncertainty and verification steps. Hints are claims
to test. Candidate coordinates are not automatically added to the live map.

Create saved report preserves selected extracted text and visual findings with
model/hash provenance and uncertainty, without image bytes. Original uploads are
discarded after extraction; working previews and assessments expire after 15 minutes.
Replace/remove cleans up working receipts. Returning to the tool retains only
bounded in-memory receipt references for cleanup. Pending report requests protect
their input until they settle. Account/access changes clear client references.

## Recurring research

Save a question, country scope, lookback, source choices and optional fresh-web
choice under Research, Recurring. Weekly and calendar-monthly runs are supported
alongside daily/weekdays. Times remain UTC throughout the year. Monthly day 31
uses February's final day, then returns to day 31 in March.

The server must be running. Each completed run saves a report in the selected
destination. Pause/resume retains options and history. Source coverage and access
are checked again each run. Optional evidence-change alerts use the existing
deterministic comparison. Changed scope resets its baseline. Company/domain
research requires a subject; expiring private media/document inputs cannot recur.

## Connection readiness

An administrator needs the server's persistent encryption key, an AI connection
and a successful connection test before activation for the intended destination.
A saved model name does not prove working vision or web access. Restore a missing
encryption key or explicitly decide to re-enter affected credentials before
replacing it. Actual research and geolocation accuracy need known-example evaluation.

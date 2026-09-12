# Map controls, news and evidence assessment

Implemented 13 September 2026. The map and globe share the same event-filter
pipeline. Backend source categories and saved research scopes remain unchanged.

## Layer controls

- Natural hazards supports any combination of hazard checkboxes, with select-all
  and clear actions. Magnitude, reporting period and GDACS alert refinements
  apply to natural hazards, not fire records.
- One Fires flame icon controls NASA FIRMS thermal detections and reported
  wildfires (including EONET and GDACS fire reports). Either source family or both
  can be selected. Thermal detections are observations, not proof of a wildfire.
- Fires and Natural hazards have independent master switches. Fires starts off.
  Only Conflicts starts enabled, as before. Excluding an inspected event clears
  its details and selected map highlight.
- Topics was removed from the rail. Its time window remains as Event time on the
  right, while political, humanitarian, economic and public social reporting
  choices sit inside News subjects. Research categories were not deleted.
- New map preferences default to Hybrid in both projections. An explicitly saved
  style is retained. Native attribution starts closed and remains accessible
  through its information toggle at bottom left, clear of the Eye launcher;
  source credits still update automatically.

## News briefing

The News icon toggles news pins. Its Brief control opens a searchable headline
list with publisher and subject choices. A panel-only authenticated snapshot
loads at most 300 retained events, initially showing 15 grouped stories. More
rows are revealed on request. Closing the panel removes its data-loading hook;
it does not add a continuous poll or a model request.

Keyword, publisher and subject filters also apply to the News map layer. The
shared country and publication window scope the snapshot. Data from previous
country, period or access scopes cannot reappear after a late response. A
selected news item is cleared if a changed filter or advancing time excludes it.

Headlines remain readable when pins are off or no usable position exists. Locate
and inspect selects a known position; Inspect evidence opens unlocated records
without inventing coordinates. Nation filters require source-supported event
geography, not the publisher's home country. The broader RSS additions do not
infer locations from headlines. Research story creates a research draft, without
automatically starting a model job.

Matching story IDs and identical links are grouped for readability. Counts are
source feeds, not independent corroboration. Missing or unsafe URLs retain their
headline text but have no external link. Source assessment explains each stored
event grade. Coverage details are collapsed below the headlines.

## Source coverage and operating limits

[News source coverage](NEWS_SOURCE_COVERAGE.md) records the 38 verified additions,
publisher organisations, endpoint probes, exclusions and usage limitations.
There are now 92 seeded RSS feeds across the app, including 14 additional UK
national/regional feeds and 24 additional international feeds. These are
headline/date/attribution/link feeds, not licensed full-text archives.

Each new source has an explicit unassessed rating and F6 evidence grade. Known
shared publishers retain their organisation identity. More feeds increase
breadth but do not establish reliability, independence or complete worldwide
coverage. Existing source switches, backoff, 200-item/5-MiB response bounds,
30-minute intervals and bounded shared retention still apply. No API key is
needed for these additions.

Research now separates catalogue/coverage metadata from collection allowances:
128 providers and 136 plan/receipt rows, while explicit selection stays at 64
sources plus eight tasks. Actual quick/detailed/advanced collection budgets remain
6/24/32 requests and 200/800/1,000 items. Unsupported and unselected entries remain
visible without becoming extra network work. The private publisher inventory is
unchanged; the new feeds contribute through retained evidence.

## Report assessment and doctrine

The canonical report reader and Word, PDF and Markdown exports now include:

1. Saved likelihood and its approximate UK PHIA band, separately from analytical
   confidence and its recorded rationale.
2. Recorded reporting-item grades and separate contrary reporting citations.
3. Source reliability (A to F), information credibility (1 to 6), frozen rating
   status and the recorded grading basis for cited evidence.
4. Saved evidence-confidence limits, method limitations and ways to strengthen
   the assessment, where those were recorded.

Economy, Cyber and daily situation previews also retain those judgement
dimensions and separate supporting and contrary citations. The reader's
Assessment workspace contains the methodology; Sources explains evidence grades.

This is a presentation repair, not a new accuracy scoring algorithm. Existing
generation prompts, mechanical yardstick validation and evidence-based confidence
limits remain in force. Historical views are projected from their frozen report
values without regrading their sources or modifying the saved Markdown bytes.
Absent historical assessment metadata is explicitly described as unrecorded.

The [PHIA guidance published in 2025](https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment)
separates assessed likelihood from analytical confidence. Its confidence framework
considers information base, analytical rigour, and complexity and volatility.
The app constrains confidence using evidence but does not claim to measure all
three dimensions automatically. Grades do not become truth percentages.

[UK MOD JDP 2-00, fourth edition](https://www.gov.uk/government/publications/jdp-2-00-understanding-and-intelligence-support-to-joint-operations)
is the public intelligence-doctrine reference for source and information grading.
F and 6 mean insufficient grounds to judge, not that information is false.
Feed-handling grades do not establish an individual publisher's reliability.
Several weak or copied articles do not outvote stronger independent evidence.

The official [NATO AJP-2.9 catalogue entry](https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283399)
lists Revision B dated 20 August 2025 with controlled distribution. We describe
the product as informed by public UK and NATO doctrine. We do not claim NATO
accreditation, a NATO-mandated numeric scoring matrix or complete conformance to
a controlled document based on an older public copy.

Source links and citation presence are not independent factual verification.
Model-assigned support/opposition and source identities still need analyst
evaluation when consequential decisions depend on an assessment.

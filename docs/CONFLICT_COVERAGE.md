# Conflict evidence and source coverage

Updated 9 September 2026.

Machine-coded signals now require relevance screening for default incident display
and tracker counts. See [screening and source audit](CONFLICT_RELEVANCE_SCREENING.md)
for model setup, worker bounds, source-text requirements and the OSIRIS comparison.

## Delivered behaviour

The conflict tracker counts reported violence by usable occurrence date. Protests,
riots, force posture, coercion and unclassified activity remain separate. GDELT
media counts do not establish independent corroboration. Aircraft, vessels,
satellites and weather records cannot inflate conflict reporting counts.

Exact originating dataset/incident identifiers collapse linked records. Otherwise,
grouping requires the same canonical article URL, date, event type, coordinates and
actors. Tracking parameters are ignored. This deliberately avoids speculative
text-similarity merges. Different articles may still describe one incident, so the
UI says reported violence rather than confirmed unique attacks. It does not turn
three repeated articles into three independent sources.

Casualties sum available estimates from retained evidence, not total conflict
fatalities. Missing figures and ACLED ambiguous zero estimates remain unknown.
Known zero, reported ranges and differing estimates are distinct. Related records
are not summed twice. Invalid or imprecise dates are excluded from exact activity
charts and counted as evidence gaps. Original dates and precision remain visible.
Precise points outside an area's bounding box do not qualify through country tags.
Country-only context remains indicative and can concern multiple disputes; it is
not an attributed attack. Context relevance currently uses English titles and
summaries, including translated titles when present, so recall is incomplete.

Both map views offer conflict-type filters. Monthly research records are hidden
until Historical baseline is selected, carry release/coverage labels, and never
enter the latest-events ticker. Deselected items lose their selected state.
The authenticated source coverage panel reports configuration and safe health
states without exposing upstream error text or credentials.

## Providers and activation

| Provider | Purpose | Activation and limits |
| --- | --- | --- |
| GDELT events | Early media reports | Existing latest 15-minute export, bounded to 400 candidates. No missed-batch catch-up. Machine-coded reports require verification. |
| UCDP Candidate | Provisional historical baseline | Public CSV enabled by default, release 26.0.7 (July 2026). Daily refresh, existing 5 MiB HTTP bound, 10,000-row cap. Optional API token selects the authenticated endpoint instead. |
| ACLED | Coded political violence and demonstrations | Optional approved bearer token. Fourteen-day window, six-hour polling, bounded pagination. Entitlements and token expiry can prevent collection. |
| ReliefWeb API | Humanitarian context with original publishers | Optional approved application name. Latest 100 metadata records hourly. Replaces the existing ReliefWeb RSS connector when configured. |
| ReliefWeb RSS / Crisis Group | Existing context feeds | Public upstream availability varies. A configured source is not evidence that its latest poll succeeded. |

Set optional values in the ignored backend environment, never in frontend code:
`ASE_UCDP_ACCESS_TOKEN`, `ASE_UCDP_CANDIDATE_VERSION`,
`ASE_ACLED_ACCESS_TOKEN`, `ASE_RELIEFWEB_APPNAME`.
The version is explicit, not an automatically invented latest release. Check the
provider downloads page before updating it. Restart the local API after changing
these environment values. Ordinary source enable/disable controls still apply.
No API credentials were added, purchases made or provider emails sent by this task.
ACLED token refresh is an operator responsibility in this integration.

The public UCDP July CSV was fetched once during implementation: 1,357,690 bytes,
1,828 rows, 49 columns. This verifies accessibility of that release, not real-time
coverage. Raw events stay in the existing bounded shared in-memory store; no new
historical event database or migrations were introduced.

## Sources checked and remaining gates

- [UCDP downloads](https://ucdp.uu.se/downloads/) and
  [API documentation](https://ucdp.uu.se/apidocs/): preserve the provider's release,
  provisional status, precision and CC BY attribution requirements.
- [ACLED API](https://acleddata.com/api-documentation/getting-started) and
  [codebook](https://acleddata.com/methodology/acled-codebook): approved access and
  applicable data terms are required; positive estimates are not verified totals.
- [ReliefWeb API](https://apidoc.reliefweb.int/): approved appname and original
  publisher rights apply. An aggregator is not another independent witness.
- [Crisis Group RSS directory](https://www.crisisgroup.org/rss-0): its advertised
  CrisisWatch link redirected to the HTML directory when checked. No new working
  CrisisWatch feed is claimed or simulated.
- ISW/CTP, Airwars and HDX remain candidate enrichment sources. Their accessible
  machine interfaces, reuse terms and duplication with existing originators must
  be resolved before activation. HDX redistribution of ACLED must not count as a
  second independent dataset. No paid access or scraping bypass is implemented.

## Verification

Fixture tests cover provider bounds and malformed responses, exact-origin header
credentials, no redirects with credentials, secret-safe errors, source registration,
classification, date uncertainty, duplicate evidence, casualty uncertainty,
authenticated coverage and historical evidence retrieval. Frontend tests cover
filters, selection clearing, evidence bundles, baseline notices and ticker exclusion.
Backend focused regression run: 148 passed. Scoped conflict suite: 89 passed,
97.76% coverage across nine changed/new modules, above the unchanged 90% gate.
The initial scoped command accidentally retained the repository-wide coverage
source setting and failed that global coverage gate; it was corrected to measure
only the explicitly named modules. No coverage threshold was lowered.
Full backend Ruff, formatting and mypy (701 modules) passed; both architecture
contracts and the file-length check passed. A pre-existing 354-line map-engine
warning remains. Read-only review findings on missing ACLED publication dates,
country over-attribution, unrelated humanitarian context and imprecise dates were
fixed and regression-tested. Credential review found no concrete disclosure or
origin-guard regression.

After the local API restart, health and frontend returned 200; GDELT, UCDP and
existing ReliefWeb/Crisis Group feeds reported successful polls. The store exposed
1,814 UCDP records with no fabricated publication timestamps. Some records span
or revise periods before July; their original occurrence dates are retained.
ACLED and ReliefWeb API correctly showed not configured.
Frontend final results are recorded in the development story. Browser
visual verification remains unavailable because the local browser policy blocks
access; API and component tests do not substitute for GPU interaction testing.

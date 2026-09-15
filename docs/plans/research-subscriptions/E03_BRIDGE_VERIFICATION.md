# E03 structured bridge verification, 14 September 2026

This record covers the bounded IODA country event and ECB daily GBP-per-EUR research
routes only. It does not claim complete cyber, network or economic coverage.

## Source contracts and permitted scope

| Route | Official source contract | Implemented scope | Use and interpretation |
| --- | --- | --- | --- |
| `research-ioda-outage-events` | [IODA HTTP API v2](https://api.ioda.inetintel.cc.gatech.edu/v2/), `GET /v2/outages/events` | One selected country and recorded interval of at most 14 days; one request, first 20 returned events | The live response identifies Georgia Tech copyright, but an explicit general data-reuse licence was not established. Research collection is off by default. The operator must review permission and set `ASE_IODA_PUBLIC_DATA_USE_ACKNOWLEDGED=true` before use. An anomaly window is not proof of an outage cause, affected users, precise location, deliberate interference or a cyberattack. |
| `research-ecb-gbp-reference-rate` | [ECB SDMX data API](https://data.ecb.europa.eu/help/api/data) and [EXR examples](https://data.ecb.europa.eu/help/api/data-examples) | Exact `EXR.D.GBP.EUR.SP00.A` series, at most 31 UTC recorded days, one CSV response | [ESCB public statistics reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html) permits attributed reuse of unmodified public statistics and metadata. The bridge stores the returned value and unit. ECB reference rates are information-only, not necessarily transaction prices. |

Both routes require an exact subject or selected source. They never place the user's
question, private terms or credentials in the provider URL. Public-source transport
continues to enforce host, redirect, timeout and body limits. The parsers impose a
separate 64 KiB ceiling, reject mismatched series or country, and disclose returned
item limits. A response with no rows is labelled empty, not evidence that no event
or rate existed.

## Read-only live checks

The following checks used public endpoints without credentials on 14 September
2026. They are point-in-time transport and shape checks, not continuous provider
monitoring or permission to reuse IODA data.

- IODA `outages/events` with `entityType=country`, `entityCode=IR`, a one-day
  interval and `limit=2` returned HTTP 200. The envelope echoed the country and
  interval, returned zero events, and contained a Georgia Tech copyright notice.
  A separate bounded global request returned one country event with signal,
  method, start and duration fields.
- ECB `EXR/D.GBP.EUR.SP00.A` with three selected August 2026 dates and
  `format=csvdata` returned HTTP 200 and three daily rows. The header exposed
  the series dimensions, `TIME_PERIOD`, `OBS_VALUE`, `UNIT`, `UNIT_MULT`, source
  and observation status columns.

Offline contracts: `test_e03_ioda_ecb_bridges.py` passed 22 tests, including
one-request factory integration, opt-in denial, malformed/mismatched responses,
units, null versus zero, provenance and observation time. A 65-test combined
source catalogue, capability and E03 composition run passed. Scoped Ruff and
mypy checks passed. No PostgreSQL migration or live end-to-end report was run.

## Remaining coverage gaps

IODA use remains disabled until the operator documents suitable data-use rights.
The first 20 returned events and a bounded 14-day interval cannot establish a
complete national outage history. Cloudflare Radar outage annotations still lack
a dedicated research route. ECB support is limited to one GBP-per-EUR daily
reference-rate series; other ECB series, historical vintages and ONS latest-version
discovery remain unavailable. No network anomaly is automatically promoted to
conflict or cyberattack evidence.

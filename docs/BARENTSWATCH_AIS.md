# BarentsWatch AIS connection

BarentsWatch supplements AISStream and Fintraffic with Norwegian Coastal
Administration vessel reports. Its public feed covers Norwegian maritime zones,
Svalbard and Jan Mayen, using terrestrial, offshore and satellite reception.
It excludes fishing vessels under 15 metres and leisure/sailing vessels under
45 metres. This is regional coverage, not complete global AIS.

## Configuration

Create a client under **My page > Developer access > AIS API**. The general
BarentsWatch client has scope `api`; ship positions require a separate client
with scope `ais`. Set `ASE_BARENTSWATCH_CLIENT_ID` and
`ASE_BARENTSWATCH_CLIENT_SECRET` in the backend environment, then restart the API.
Keep credentials server-side and outside Git. Both are required before the
`barentswatch_ais` feed is registered. Its administrator source control and
`ASE_FEEDS_DISABLED` entry work like other feeds.

The current local AIS client was created on 11 September 2026. Its generated
secret is stored only in ignored `backend/.env`. The operator's general API
client is unchanged and is not used for ship access.

The operator subsequently supplied the general client's secret. Its token
request succeeded with scope `api` at 00:39 UTC on 11 September. That credential
is saved separately as `ASE_BARENTSWATCH_API_CLIENT_ID` and
`ASE_BARENTSWATCH_API_CLIENT_SECRET` in ignored `backend/.env`, reserved for
future general API adapters. The current application does not consume those
two values. Both existing AIS credential values were verified unchanged;
this does not activate fish-health, wave or other general API datasets.

## Collection and display

The connector requests the current combined snapshot every two minutes. Tokens
are cached in memory with early expiry and coalesced refresh. Requests use fixed
HTTPS origins, DNS pinning, bounded responses and no redirects. Failed requests
consume a cooldown; there is no anonymous retry. Neither credentials nor token
responses become event metadata or normal diagnostic output.

Snapshot responses are capped at 5 MiB and 20,000 rows. Malformed coordinates,
missing/naive timestamps, positions over 15 minutes old and positions more than
30 seconds in the future are excluded. Duplicate MMSIs within a snapshot retain
their latest record. Shared store, map retrieval and browser limits still apply;
API counts are not promises that every upstream vessel is simultaneously visible.
Existing ship-layer defaults are unchanged. Enable Ships and use the source filter
to inspect BarentsWatch. Selection, directional icons and details share the
existing map/globe path.

AIS type 35 means **reported military operations**, not verified naval ownership.
Names and MMSI prefixes do not establish military status. The combined snapshot
does not provide a separate timestamp for its static vessel-type information.
Provider provenance remains separate when multiple networks report the same MMSI;
they do not constitute independent identity verification. No track archive or
historical area-research adapter is introduced.

Visible map credit identifies BarentsWatch and the Norwegian Coastal Administration
when its observations are displayed. Event metadata carries attribution, licence,
delivery credit and normalisation details into frozen evidence. The public API
uses NLOD unless dataset documentation specifies otherwise. See the
[provider terms](https://www.barentswatch.no/en/articles/api-terms-and-conditions/).

## Verification

On 11 September at 00:26 UTC, a bounded guarded token request succeeded with
scope `ais`, and the official latest-position endpoint returned 4,321 records.
This proves API access at that time, not continuous availability or complete
vessel reception. At 00:33 UTC the production connector accepted 3,407 fresh,
valid positions, including 12 with reported AIS military-operations type 35.
Every accepted position contained the provider credit. Differences from the
earlier upstream count reflect a later snapshot and conservative freshness and
validation, not guaranteed world coverage or verified military identity.

Frontend verification passed 18 relevant tests, scoped ESLint/Prettier and full
TypeScript checks. Independent static review found no remaining correctness or
security issues after fixing same-position vessel-name corrections to update the
stored event. Credential scanning found no configured secrets in proposed source
changes; the backend environment remains ignored. No live browser/GPU acceptance
or complete backend coverage is claimed by these checks.

Final backend acceptance passed 216 targeted tests, with 100% statement and
branch coverage across all four new connector modules and the unchanged 90%
gate. Full backend Ruff/format/mypy and architecture checks passed, as did scoped
Bandit and file-length checks. The local API was restarted with the configured
credentials; API health and frontend login returned 200, while an unauthenticated
protected-camera request returned 401. No remote push or production deployment
was performed.

Official references checked 11 September 2026:

- [Client registration and tokens](https://developer.barentswatch.no/docs/tutorial/)
- [Live AIS coverage](https://developer.barentswatch.no/docs/AIS/live-ais-api/)
- [Snapshot and historical API examples](https://developer.barentswatch.no/docs/AIS/examples/)

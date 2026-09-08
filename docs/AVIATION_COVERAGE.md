# Aircraft coverage and map lists

Updated 8 September 2026.

## Coverage is not every flight

The map represents fresh positions reported by the community ADS-B network. It
cannot establish that unobserved aircraft are absent. The public provider API
supports military and regional position queries; its documented public interface
does not provide an unrestricted all-aircraft endpoint. No feeder-only endpoint
or paid-provider access has been bypassed.

The original collector watched eight areas. The updated configuration watches 22
regional circles, including the UK, western and central Europe, US regions, Japan,
India, Singapore and Australia. Regional coverage remains incomplete. Each circle
has a 250-nautical-mile radius and is refreshed through the existing scheduler.
The combined area batch is capped at 15,000 aircraft; the starting region rotates
so a crowded first region does not permanently starve later regions.
Each batch has an internal 45-second budget and each request at most five seconds,
inside the scheduler's 60-second limit. Successful partial batches are published,
with a coverage warning; the next poll resumes after the last attempted region.
All-region failures remain visible, and shutdown cancellation still propagates.
See the versioned air-watch resource for the exact centres.

Before this change, a live authenticated API probe returned 1,671 aviation records,
including 385 provider-labelled military aircraft. The browser's mixed 5,000-record
budget reserved most capacity for ships, satellites and FIRMS, leaving about 1,000
for aircraft and other records. The 999+ badge also obscured larger actual counts.
This was a display/retention problem as well as a coverage limitation.

## Military identity and movement

A military label comes from the provider's military endpoint or explicit database
flags. It is not guessed from a callsign, aircraft name or location. A shared,
bounded classification cache prevents a later overlapping regional/privacy query
from erasing an earlier provider label. The label's basis and observation time
remain available; this does not invent a fresh aircraft position. Older overlapping
ADSB position reports cannot overwrite newer positions. Position timestamps derived
from reported age participate in the event digest, allowing fresh stationary
reports to refresh a marker without replaying an old timestamp as new.

The cache is memory-only, expires classifications after 24 hours and holds at most
15,000 entries. Aircraft positions still follow the normal freshness and store
retention rules. A provider label is not proof of current mission or intent.

## Map controls

Flights and ships have searchable, paginated lists with 25 rows per page. Selecting
a row locates the object on the current map/globe and uses the normal selected
marker and details panel. Closing details clears that selection. Military filters
and distinct marker colours make explicit provider classifications easier to find.
Search runs against loaded records, not an unlimited worldwide inventory.

The browser remains bounded at 5,000 events. Guaranteed category allocations are
1,500 aircraft, 1,500 vessel positions, 1,000 satellites and 500 FIRMS observations,
with unused places reusable by other records. Military records receive priority
within aircraft/vessel allocations. Dedicated aviation and military snapshots
prevent unrelated busy layers from excluding them before selection. Popups show
loaded counts and server-retained totals; differing time/country scopes and the
bounded client sample are stated explicitly.

The events API keeps its 2,000-record response cap. Military filtering occurs before
the limit, and bounded offsets support paging without an unrestricted response.
Provider/API gaps, inactive transponders, geographic receiver gaps, freshness
expiry and local filters still affect what can be shown.

## Sources and operations

- [ADSB.lol public API](https://www.adsb.lol/docs/open-data/api/) and
  [provider implementation](https://github.com/adsblol/api): attribution and ODbL
  requirements continue to apply.
- [AISStream documentation](https://aisstream.io/documentation): vessel metadata
  is collected only through the backend using the existing configured key.
- [US Coast Guard AIS report definitions](https://www.navcen.uscg.gov/ais-class-a-reports):
  ship type 35 describes reported military operations. It does not independently
  verify naval ownership. Type 55 law enforcement is a separate classification.

No new account, paid subscription, database migration or production deployment is
required. Backend changes take effect after restarting the local API. No secrets
are placed in frontend code. Tests and final runtime results are recorded in the
development story. Browser visual verification remains unavailable under the
existing local browser policy.


## Verification of this update

94 backend regression tests passed, covering traffic classification, feeds, store
queries, API bounds, the pipeline and scheduler. The three new classification
modules reached 100% branch-aware coverage in their focused suite. Full backend
Ruff, formatting, mypy (704 modules), and both architecture contracts passed.

After restarting only ASE's local API on port 8001, an initial live probe returned
299 provider-labelled military aircraft and one vessel with explicit AIS military
operations metadata. Of the sampled 2,000 AISStream positions, 72 had joined static
ship metadata. These are changing live samples, not guaranteed counts or naval
inventories. API health and the frontend on port 5174 returned successfully.
Final frontend validation and collection results are recorded in the development
story. No changes were made to the separate MIST app on port 5173.

A live startup check exposed the regional request timing problem. The repair
passed 52 related tests, including explicit timeout/continuation/cancellation
regressions, before the final API restart. No scheduler-wide timeout or browser
memory limit was increased.

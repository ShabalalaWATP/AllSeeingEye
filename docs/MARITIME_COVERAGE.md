# Ship position coverage

Updated 8 September 2026. Vessel markers represent received AIS reports, not a
complete inventory of ships at sea. AIS identity and coordinates can be wrong or
spoofed. Missing markers do not establish that a vessel is absent.

## Working sources

| Source | Coverage | Access | Collection |
| --- | --- | --- | --- |
| [Fintraffic AIS](https://www.digitraffic.fi/en/marine-traffic/) | Finnish waterways and nearby Baltic receiver coverage | No key | Latest positions, polled every two minutes |
| [AISStream](https://aisstream.io/documentation) | Global receiver network, incomplete | Free account API key | Forty-second collection windows, followed by the scheduler's thirty-second interval and jitter |

Fintraffic returned **778 fresh vessel positions** in a live guarded HTTP probe
on 8 September 2026. Their observed bounds were 17.58 to 30.25 degrees east and
57.11 to 65.80 degrees north. This is a regional source, so an otherwise empty
worldwide ship layer was expected. Its parser does not exclude stationary ships.
The existing 5,000-record response limit was not reached.

AISStream is the global provider used by the inspected OSIRIS implementation.
The integration accepts class A and both standard and extended class B position
reports. It validates the report's own coordinates and provider timestamp, keeps
the latest report per MMSI in each batch, and retains zero-speed ships. It rejects
unavailable coordinates, invalid reports, ambiguous or missing timestamps and
positions older than fifteen minutes. It never refreshes a ship's timestamp just
because an old report was received again.

Both providers publish through the existing bounded event store, map, globe and
selection system. Separate providers retain separate provenance; overlapping
reports for the same vessel are not independent identity confirmation.

## Enable global coverage

1. Create a key in your [AISStream account](https://aisstream.io/).
2. Set `ASE_AISSTREAM_API_KEY` in the backend deployment environment or its ignored
   `backend/.env`. Do not put the key in frontend configuration or commit it.
3. Restart the API. The source catalogue then includes `aisstream`; administrators can inspect feed
   health in Admin Sources.
4. Enable Ships on the map. Allow the first forty-second collection window to
   finish. Source failures are reported rather than replaced with synthetic ships.

An administrator can disable the source through the existing source controls, or
an operator can add `aisstream` to `ASE_FEEDS_DISABLED`. Account key creation and
live authenticated AISStream coverage were not performed during this change.
The provider offers no delivery guarantee. Collection is deliberately sampled to
fit the existing scheduler: messages during the interval between windows are not
received. A future persistent stream adapter could remove that gap, with explicit
shutdown, admission-control and backpressure integration.

The connection uses compression, a fixed WSS endpoint, public-address DNS pinning,
TLS hostname verification, no redirects or environment proxy, bounded 64 KiB
messages, a sixteen-frame queue, 50,000 messages and 20,000 vessels per window.
Cancellation closes the socket. Transport debug logs are disabled and provider
errors are replaced with credential-safe health messages.

## Other sources investigated

- [Norwegian Coastal Administration via BarentsWatch](https://developer.barentswatch.no/docs/AIS/live-ais-api/)
  is useful additional Norwegian terrestrial and satellite coverage, but requires
  an account, AIS client and OAuth client credentials. Its open feed excludes
  small fishing vessels and leisure craft. It has not been integrated here.
- [NOAA AccessAIS](https://www.coast.noaa.gov/digitalcoast/tools/ais.html) provides
  downloadable research data. It is appropriate for historical analysis, not a
  substitute for current ship markers.
- Commercial MarineTraffic and similar services require provider-authorised API
  access. Public website visibility is not treated as permission to bypass an API.

## Verification

- 43 AISStream and Fintraffic tests passed with offline transport fixtures.
- AISStream scoped branch-aware coverage: 94.21 percent.
- Ruff and mypy passed for the new adapters and their configuration integration.
- Live Fintraffic coverage verified as above. Global AISStream playback/data
  delivery remains unverified until an operator configures a key.

## Browser loading and retention

The general snapshot remains capped at 2,000 records. When server statistics show
maritime records missing from that snapshot, the browser also requests up to
1,500 maritime records. It merges newer duplicates and applies live updates and
expiry messages received during loading. Signing out or cancelling invalidates
both requests. A failed supplement leaves the valid general snapshot visible
with a partial-coverage message.

The 5,000-record browser limit remains unchanged. Up to 1,500 vessel positions
receive reserved capacity; other events can use every unused reserved place.
This prevents busy aircraft/news feeds from evicting all loaded ships. It does
not remove provider coverage gaps, country/time filters or freshness expiry.

Independent peer review found no material credential, transport or timestamp
issue. The dependency audit reported no known vulnerabilities in installed
published dependencies (the local application package is not a PyPI package).

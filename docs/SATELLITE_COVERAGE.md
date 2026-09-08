# Public satellite coverage

The satellite adapter expands the former stations-only feed to four independently monitored CelesTrak sources. The active catalogue uses CSV, which supports catalogue IDs above 99,999 and stays within the existing 5 MiB HTTP response bound. No new package or credential is required.

| Source ID | Published selection | Bound |
| --- | --- | --- |
| `celestrak_stations` | Stations and associated vehicles | 20,000 rows |
| `celestrak_active` | Active satellites, including large commercial constellations | 20,000 rows |
| `celestrak_military` | CelesTrak's public military group | 20,000 rows |
| `celestrak_skynet` | Publicly named Skynet objects, excluding rocket bodies and debris | 20,000 rows |

A public probe on 8 September 2026 returned 16,510 rows from the active CSV (2,495,875 bytes), a populated military catalogue and 13 Skynet name matches. One Skynet match was launch hardware, which the adapter excludes. These are retrieval observations, not a guarantee of future catalogue size or successful propagation for every row. Skynet matches include historical spacecraft; presence in this catalogue does not establish current operational service. The app does not manufacture an orbit for a satellite absent from the public catalogue.

## Position meaning and freshness

Positions are SGP4 predictions from public mean orbital elements. They are not live sensor observations. The existing spherical Earth subpoint conversion is retained, so latitude and altitude are approximate; this is a general visualisation rather than a precision orbit determination or pass-planning tool.

Each event includes NORAD ID, original element epoch, prediction time, epoch age in hours, catalogue group and an explicit `position_kind=propagated`. Elements older than three days are marked stale. Elements older than fourteen days, more than one day in the future, invalid records and propagation failures do not produce positions. Element downloads are cached for two hours and positions are recalculated on each two-minute poll. A failed download remains a source failure; the adapter does not invent fresh positions from a failed response.

A `military_public_catalogue` flag means the source published the object in its military group or the object has a Skynet family name. `affiliation_basis` records that distinction. This is not a comprehensive classification of military, commercial or dual-use assets. It does not infer operational tasking or the position of undisclosed spacecraft. Different source groups overlap; map rendering should deduplicate by `norad_id`, preferring the specific military or Skynet record.

## Verification and sources

Deterministic tests cover six-digit catalogue IDs, more than the former 500 objects, the 20,000-row bound, duplicate IDs, malformed and stale orbital data, cache refresh, source labels and exclusion of Skynet launch hardware. Network calls are excluded from tests.

- [CelesTrak public element groups](https://celestrak.org/NORAD/elements/)
- [CelesTrak GP formats and query parameters](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [MOD description of the Skynet capability](https://www.gov.uk/guidance/skynet-6)
- [OSIRIS satellite route](https://github.com/simplifaisoul/osiris/blob/master/src/app/api/satellites/route.ts), inspected revision `fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8`. OSIRIS also starts from the active catalogue and adds overlapping groups; this implementation uses bounded CSV/JSON rather than legacy five-digit TLEs.

## Browser loading and controls

The browser retains its 5,000-event global bound. It reserves up to 1,500 places for ships, 1,500 for satellite positions and 1,000 for FIRMS thermal detections, leaving at least 1,000 places for other events when all reservations are full. Unused reservations remain available to other events. Alongside the ordinary snapshot it requests a space supplement (up to 1,500), then a separate combined stations/military/Skynet supplement (up to 1,500). A separate 1,000-record request covers both keyed and public NOAA-20 FIRMS source IDs when disaster records exist. Source-specific priority keeps these smaller satellite catalogues visible when a commercial constellation fills the broader active catalogue. These limits mean the map is a bounded view of the full server catalogue, not a promise to render every tracked satellite simultaneously.

The satellite panel offers all, stations/crewed vehicles, public military and Skynet selections. Counts describe loaded distinct objects. Rendering collapses overlapping feeds by NORAD ID and favours Skynet, military, then stations records; other map categories pass through unchanged. The event inspector retains original source attribution and orbital-age attributes. Failed supplements show an error while retaining a successful primary snapshot. Existing live-update reconciliation, session cancellation and tombstone handling remain in force.


## Final runtime and freshness checks

The final authenticated runtime probe returned 22 station/crewed objects,
24 public military catalogue objects and 12 Skynet objects. The active catalogue
was returning HTTP 403 at that point. The earlier 16,510-record result was a
successful provider retrieval, not a claim that those objects remain available
in the running application. Failed network retrievals wait two hours before the
next upstream attempt, including when no elements were cached.

Position snapshots expire after ten minutes, separately from the two-hour
orbital-element cache and fourteen-day maximum element age. The server prunes
expired positions on its existing maintenance cadence; the browser hides expired
predictions on its thirty-second clock even if the live connection is lost.
Precision labels explicitly identify propagated orbital estimates. These rules
avoid presenting a seven-day retained SPACE event as a current satellite position.

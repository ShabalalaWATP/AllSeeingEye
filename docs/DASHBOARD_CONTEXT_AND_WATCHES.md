# Dashboard controls, context and area watches

10 September 2026. Implements the next slice of the
[OSIRIS comparison](OSIRIS_DASHBOARD_FEATURE_REVIEW.md).

## Operator flows

- **Flights / Boats:** the small disclosure opens the same panel system as the other
  map controls. Search and provider selection filter both map and list. Aircraft
  can also be filtered by reported ground state. Military labels retain their
  existing provider-based meaning. Lists show 25 rows per page and obey location
  quality; choosing a result enables its category and opens the shared inspector.
- **Space:** search name, NORAD number or designator across current, deduplicated
  positions. Select a result to enable Space, locate it and highlight its record.
  The Space weather tab reads collected NOAA scales, Kp and bulletins on demand.
- **Boats > Navigation warnings:** search text, NAVAREA or keyword-derived topic.
  A selected located warning opens details and shows one highlighted first-position
  marker, even if that record is absent from the viewport cache. Closing details
  removes the marker. No warning polygon or safe-navigation assessment is inferred.
- **Network:** opens IODA connectivity signals. Nation applies when source country
  attribution exists. These are dated drops, not established current outages:
  the existing adapter does not retain recovery messages.
- **CCTV:** media choices distinguish approved in-app streams, video clips, snapshots
  and provider-only links. Provider names are searchable. A camera can match more
  than one media kind. Filtering away its selection closes its media/details.
- **Draw on map > Watch this area:** finish a rectangle, polygon or circle, then
  review a watch in Warning. All geodesic sketches use a conservative geographic
  envelope, including their curved edges and some surrounding area. Edit bounds,
  category, terms, threshold and workspace before Add indicator. A path has no area.
  The default is No report; nothing is submitted by opening the form.

The compact event-scope strip states map-area sampling or the worldwide sample,
nation, retained/selected publication time and removable refinements. Topics & time
explains the independent scopes of cameras, infrastructure, GNSS, regional conflict
markers and context panels. These controls do not change a source's precision.
An event excluded by a filter loses its details and highlight; restoring the filter
does not silently reselect it. Deliberate unplotted records remain inspectable.

## Evidence and data interpretation

Selected aircraft, vessels, satellites, earthquakes and FIRMS records now show
readable fields with their actual retained units. Missing fields remain Not
reported. Raw attributes remain available in Source fields. Source severity,
reliability, credibility, sensor confidence and claim accuracy are distinct.

ADSB altitude parsing now preserves unknown ground state for absent or malformed
altitude, including booleans and non-finite values. Numeric altitude, including zero
or negative values, is kept; a literal ground value reports ground state. Contract:
[readsb JSON fields](https://github.com/wiedehopf/readsb/blob/dev/README-json.md).
AIS navigation-status labels retain their original code:
[USCG AIS Class A reports](https://www.navcen.uscg.gov/ais-class-a-reports).

NOAA missing/malformed scales remain unknown, not zero. The issue stamp participates
in change detection so unchanged levels can carry a new issue date. The tracker now
recognises the actual NOAA bulletin source ID. The panel displays the reported R/S/G
scales separately from Kp; it does not infer local jamming, HF reception or forecasts.
Reference: [NOAA scale definitions](https://www.spaceweather.gov/noaa-scales-explanation).

## Performance and access boundaries

Only Conflicts remains enabled at startup. The changes add no continuous provider
loop, model work, history retention or heavy default layer. Text searches are
deferred and bounded; traffic projections run only in the mounted drawer. Existing
event and camera caps remain unchanged. Camera filters do not fetch or play media.

Context panels mount only when opened, read at most 100 collected records and show
at most 25 entries. Space uses three source-specific reads of 33 records each so
bulletins cannot crowd out the singleton indices. Refresh is explicit. Failures,
empty records, issue dates and snapshot fetch dates remain distinct. Existing API
authentication, request cancellation and workspace guards apply. Batched logout and
same-account login also discard old snapshots. A selection holds at most one extra
record in memory, never bulk-inserts context into the viewport store, and clears
on account/access/nation changes or another pick.

Area drafts stay in memory, bound to the current actor and workspace access revision.
They never enter URLs or browser storage. Access changes, discard or successful
submission clear the draft. Warning uses the existing authorised create endpoint.
Its geographic predicate now supports west > east dateline boxes. Watches count
published items inside a rectangle and apply the existing cooldown; a missing
observation does not prove an object departed. Report generation requires an explicit
template choice and existing server authorisation.

## Remaining gaps

Camera in-view/availability filtering, richer traffic numeric filters, pinned
shortlists, dashboard view persistence/sharing, real spatial area briefs, public
GIS selection, warning polygons, orbit/pass details and licensed history remain
separate work. Updating frontline geometry still needs approved provider access.
No complete worldwide observation coverage is promised.

Validation results are recorded in the development story. Browser/GPU acceptance
remains unverified under the existing browser-control policy; mocked renderer tests
do not establish graphics-driver stability or measured usability on the user's monitor.

# Research from a selected map area

Status: design for the next E5 implementation slice, not a delivered feature.
This extends the full research and geospatial plans; it does not replace their
polygon, regional dataset, imagery or historical comparison requirements.

## Operator flow

Select or draw an area on a report map, inspect its coordinates and save the map.
Choose Research this area to open a new research form bound to that exact map
revision. Show the area, parent report version, destination personal/team scope,
source capabilities and requested observation dates before collection starts.
Changing the area requires a new saved revision. Do not put private geometry in
query strings or browser persistence. The launch URL carries opaque view/revision
identifiers and the server resolves their current authorisation.

The initial selection control can support a two-corner rectangle and a numeric
keyboard alternative. Using the viewport captures its bounding envelope, which
must be labelled as such rather than an exact visible-ground polygon. Reuse the
existing canonical geometry validation and saved `aoi` field. Keep arbitrary
validated polygon storage; individual providers advertise the shapes and extent
limits they can actually search. A provider's narrow limit must not become a
permanent global AOI limitation.

## Spatial collection contract

Country selection is not polygon search. Add explicit spatial capability to the
research provider inventory, plan tasks and receipts. Distinguish native bounding
box/polygon queries, bounded filtering of supported source coordinates, and sources
with no spatial coverage. Each plan must explain what its area constraint means.

Strict area mode executes only supported tasks. Unsupported tasks remain visible
with an explanation and make no requests. A later optional contextual-search mode
must label its results as context and keep them separate from observations inside
the area. Do not silently convert an AOI to a country name or fabricate a place
name through reverse geocoding. Empty results do not demonstrate an empty area.

The existing Copernicus footprint search is the first available native-bbox seam:
it admits a non-wrapped box of at most 10 degrees per side, a 14-day acquisition
interval and 20 catalogue records. Integrate it through the bounded research
provider contract. Preserve acquisition dates, cloud metadata, collection/item
identifiers and source references. Catalogue metadata does not mean imagery has
been downloaded, inspected or found to contain an event.

Broader area research still requires the planned regional datasets and additional
spatial providers. Unsupported sources must never appear supported simply because
the initial catalogue adapter works. Seam-crossing AOIs need split-query admission,
deduplication and shared budgets before their collection capability is enabled.

## Exact origin and scope

Add an optional map-origin reference to research requests and plan previews. Resolve
the saved view and exact revision through fresh access checks. Freeze its canonical
AOI, geometry hash, view/revision identifiers, exact parent report-version identifier
and revision content hash in the new report's scope/receipts.

The destination must retain the origin's personal owner or team. Administrator
access is not permission to copy another person's private map into a different
scope. Recheck origin access and destination eligibility after external work and
before persistence. Revocation or deletion must prevent delivery of derived data.

Do not use the ordinary parent follow-up path: it resolves the latest parent and
automatically seeds its evidence. An AOI origin is provenance, not permission to
admit every parent record into the new area query. Likewise, frozen report source
IDs are not necessarily callable provider IDs. Map publication filters are not
satellite acquisition dates; the form must request the appropriate interval.

## Pipeline changes needed

- Extend `ResearchQuery`, provider capability metadata and plan schemas with
  explicit spatial scope; regenerate API types through the normal exporter.
- Forward capabilities through the controlled-provider wrapper and retain source
  activation checks before collection and final release.
- Register a research adapter around the existing guarded Copernicus search.
- In strict area mode, prevent the current global live-context copy from injecting
  out-of-area evidence. Add separately tested spatial eligibility before reusing it.
- Do not rely on `Job.bbox` alone: current production selection filters event
  points, whereas valid catalogue footprints can have no event point.
- Keep bounded canonical footprint provenance outside generic event attribute
  strings, which have a 500-character value cap. Never invent a centre-point event.
- A term-only replan cannot improve a fixed catalogue box/date query. Suppress
  ineffective retries and retain shared request, duration and item ceilings.
- Add map selection/launch controls through shared components, without importing
  one frontend feature into another or changing the default globe renderer.

## Required evidence

Tests must prove exact revision binding after a newer save, scope isolation,
revocation during collection, area/date propagation into real adapter requests,
unsupported-task non-execution, no global-context leakage and bounded retries.
Exercise absent geometry, oversized areas, seam/pole cases and catalogue records
without point coordinates. Frontend tests cover keyboard selection, unsaved edits,
preview invalidation, scope disclosure and account-change aborts. Real browser
checks must demonstrate selection on both projections. Fixture success does not
establish a provider's operational availability or complete geographic coverage.

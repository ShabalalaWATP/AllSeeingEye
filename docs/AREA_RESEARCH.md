# Research an area

Area research answers a question about a specific boundary and time period. It
combines supported public sources, records their coverage limits and produces a
saved report with citations. The boundary remains part of the report.

For drawing collections, the tool menu and saved workspace documents, see
[Map workspace](MAP_WORKSPACE.md). For provider configuration, see
[Sources](02_DATA_SOURCES.md) and [AI](AI.md).

## Start from a drawing or saved area

1. Open **Research area** from the map's Tools menu, or choose **Research** on an
   area in the drawing collection. Draw a polygon, rectangle or circle.
2. Inspect **What is already loaded here?**. It separates precisely located
   observations inside the boundary from approximate markers, outside records,
   country-level records and records without a usable position or publication date.
   Select a listed observation to highlight it on the map.
3. Enter a question, or leave it blank for an overview of the available evidence,
   developments, uncertainty and gaps.
4. Choose 24 hours, 3, 7 or 14 days and **Basic**, **Deep** or **Advanced** research.
   Deeper research allows more collection and analysis; it does not guarantee
   better source coverage.
5. Choose sources and use **Check sources**. This checks capabilities and budgets
   without making provider or model calls. It freezes the proposed UTC interval
   and shows selected, unsupported and unavailable source tasks.
6. Review disclosure, then generate the report. Collection sends the necessary
   boundary information to the selected providers. The configured AI connection
   assesses the returned evidence and produces the report.

The local evidence preview covers records currently loaded by the map, using
publication time. Display filters and bounded retention can reduce that sample.
Research collection can use acquisition time and fetch additional evidence.
Neither the local preview nor a successful capability check establishes that
external collection has happened. Empty results do not establish no activity.

The question, period, depth and source choices survive switching map tools. Use
**Continue in full research** for more space; the boundary and draft travel in
account-scoped memory, not in the URL or browser storage. This draft does not
survive a reload. Source preview and provider disclosure must still match the
current geometry and question before generation.

Submitted report generation is a durable job. Closing a panel or leaving the
page does not cancel an admitted server job. Its progress and outcome remain
available through research jobs and saved reports; use the explicit job controls
when cancellation or pausing is required. Unsaved previews and other temporary
map requests are separate from that job.

## Save and reuse an exact boundary

**Save as a reusable area** stores the polygon or multipolygon in personal
**Plans & areas**. It retains canonical geometry and a server-calculated SHA-256
hash, including holes and split dateline rectangles. It does not replace a shape
with its enclosing rectangle. Each saved area is an immutable record; saving a
changed boundary creates another record.

In Plans & areas, **Open on map** displays the saved boundary and **Research area**
opens a personal research draft using it. Existing rectangular areas can also be
reused, including rectangles that cross the date line. The current server access
policy determines which records can be read. Copying a boundary into a research
draft does not automatically copy a collection plan's questions or requirements.

Collection plans can match retained evidence against exact areas. Their legacy
assessment templates do not support polygon scope. An exact-area plan therefore
offers standalone area research and explains that plan requirements are not
transferred. The backend rejects incompatible plan assessment requests rather
than widening the boundary.

Research Briefs and research subscriptions retain their exact area and hash in
frozen scope. Use the report/Brief subscription workflow for recurring reports.
A map workspace document, reusable area, Research Brief and report are distinct
records; saving one does not automatically create the others.

## Watch an area

**Watch this area** prepares an editable indicator draft in Warning. Nothing is
saved until **Add indicator** is selected. Exact-shape indicators use the same
straight-edged canonical boundary as area research. Geodesic sketch strokes can
look different on the globe; the research boundary defines membership.

Only precisely located incident or site points count towards an exact-shape
indicator. Country centres, approximate points, unrelated footprints and unknown
locations do not become inside evidence. Polygon holes exclude their interiors;
outer and hole boundaries are included. Exact membership is applied before the
candidate result limit.

Exact-shape indicators create alerts only. Use an area research subscription for
recurring reports. The ordinary rectangle and nation indicators keep their own
supported report choices. Switching an exact shape to **Map area (rectangle)**
is an explicit choice to use its enclosing bounds, and may include space outside
the shape. This is a count of matching published items, not an arrival or
boundary-crossing detector.

## What collection covers

A catalogue entry does not imply polygon search support. The planner checks the
selected source capabilities and current administrator controls. Display-layer
switches do not define the collection scope or turn sources on for research.

| Source route | What it provides | Important limit |
| --- | --- | --- |
| Retained public feeds | Precise public observations already held by the server, with original source IDs, dates and grades | A bounded live snapshot, not historical backfill or guaranteed current positions |
| USGS and EONET | Dated hazard catalogue records followed by exact local geometry intersection | Bounded requests and candidate pages can omit records; a displayed centre is not an original incident geometry |
| Copernicus | Satellite scene metadata for supported intervals | Requires a single axis-aligned rectangle, at most 10 degrees per side; no image interpretation or automatic polygon widening |
| OpenAQ | Optional keyed collection of permitted, dated stationary sensor readings | Samples latest values, not a complete historical series or an area-wide air-quality assessment |
| Packaged asset registers and retained instruments | Context about supported infrastructure and observations when relevant to the scope | Dataset snapshots and limited observation windows do not establish current site status or complete coverage |

Retained-feed selection checks exact geometry and excludes country-only,
approximate, unlocated and unsupported footprint records. It uses acquisition
time where present, otherwise publication time; unknown dates are excluded.
Source and category sampling prevents high-volume traffic feeds from consuming
the entire allowance. Most news and conflict reports have city, regional or
country precision, so many cannot support strict area membership.

Fresh USGS/EONET collection is bounded to a 14-day interval. USGS uses earthquake
origin time; EONET uses dated original event geometry, including open and closed
events. Original provider identity survives deduplication and citation. OpenAQ
retains pollutant units, licence and provider attribution; see
[OpenAQ research](OPENAQ_RESEARCH.md).

Provider receipts distinguish unsupported scope, unavailable sources, failures,
empty responses and truncated collection. Review those receipts alongside the
answer. Model output does not independently verify facts or establish complete
coverage.

## Map context in a report

A scope receipt explains the geographic basis and its limits: an operator's
outline is a collection choice, a country outline is coarse near coasts, and a
curated conflict box is not a front line.

The containment receipt separates precise inside evidence, precise outside
context, approximate positions, country-level records and unlocated records.
Selection for a report does not by itself mean an event happened inside the area.

Packaged registers can include data centres, energy sites, nuclear facilities,
semiconductor sites, submarine cables, ground stations and cameras. Retained
instruments can include aircraft, vessels, thermal detections and navigation
accuracy cells. Eligibility follows the question and scope. A drawn area is an
explicit geographic context request; unrelated questions do not automatically
read map data.

The report states whether counts come from a short live window or a dated
register. Comparisons use only an available compatible baseline. Selected
readings survive in the report's frozen receipt; the app does not persist raw
live-event history to support this workflow.

## Geometry, access and validation

- Direct area requests allow one Polygon or MultiPolygon feature, at most
  256 vertices and 16 KiB of GeoJSON. Invalid topology and non-area geometry are
  rejected. Supplied URLs are never fetched as geometry.
- Map sketches have a 32-anchor bound. Circles use 32 perimeter points and a
  maximum 1,000 km radius. Dateline rectangles are split; unsplit crossing
  polygons and circles require a supported boundary instead of an inferred box.
- Editing scope invalidates the capability preview and provider disclosure.
  Account or workspace access changes clear private drafts and suppress late
  delivery. Reads and writes recheck the current object access policy.
- Saved-map origins and direct research areas are mutually exclusive inputs.
  Regeneration retains the original boundary and interval; ordinary follow-ups
  cannot silently remove spatial scope.
- Retained collection and exact indicator matching are bounded. Their limits
  describe application work budgets, not a claim that the underlying area was
  fully observed.

The plan and generation endpoints accept
`research_area: { geometry: <GeoJSON FeatureCollection> }`. Outputs include the
canonical geometry and hash. External area collection requires
`disclose_area_to_provider: true`.

Automated regression checks cover geometry preservation, dateline and hole
membership, result-limit ordering, private handoffs, compatible existing
rectangles, access changes and migration behaviour. They do not establish live
provider availability, model quality, exhaustive source coverage or real-world
location accuracy. Release validation is recorded in the implementation plan
and development story rather than as historical test totals in this guide.

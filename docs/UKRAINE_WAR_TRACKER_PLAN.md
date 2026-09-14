# Ukraine war tracker: implementation plan

Status: plan for build, written 13 September 2026. Nothing in this document is
implemented yet. Every external endpoint named below was probed on 13 September
2026 from the development machine with the project's identifying User-Agent, and
the result of each probe is recorded so the build does not rest on assumptions.

The page is a left-rail workspace at `/conflicts/ukraine` named "Ukraine war". It
shows a proper map of Ukraine with reported control and the frontline, latest
updates, headline figures, a timeline from 2014 to today, force organisation for
both sides, an equipment catalogue broken down by speciality, and three news
lenses (equipment, workforce, casualties). It updates itself from bounded feeds
and operator-run importers, and it says on every element who reported the fact
and on what basis.

## 1. Doctrine

- Nothing on the page is presented as verified. Each figure, line and headline
  carries a basis badge: `claimed` (a belligerent's own figure), `assessed` (a
  named research body's judgement), `visually confirmed` (photo or video
  documented losses), `documented` (a UN or court record), `reported` (press).
- The frontline is a reported line. Control status per settlement is a majority
  vote of public maps, not observed positions. The map legend says so.
- The Ukrainian General Staff, the Russian Ministry of Defence, ISW, DeepState and
  Oryx are all interested or partial parties in different ways. Their outputs
  are shown side by side, never merged into one number.
- No HTML from any source is rendered. Titles, excerpts and descriptions are
  plain text, truncated at import. Images are Wikimedia Commons files with a
  recorded licence and credit, cached by the operator importer, never hot-linked.
- Outbound access goes through fixed adapters with bounded bytes, bounded
  feature counts and request cooldowns. No arbitrary URL proxy. No credentials
  in the browser. Nothing new is persisted in the database: snapshots live in
  packaged resources or the bounded cache directory, events in the shared
  in-memory store.

## 2. Source research: what was verified today

### 2.1 Frontline and territorial control

| Source | What it gives | Probe result 13 Sep 2026 | Terms | Decision |
| --- | --- | --- | --- | --- |
| VIINA 2.0 (Zhukov and Ayers, Harvard) | Daily control status (UA, RU, CONTESTED) for 33,141 populated places, a majority vote of Wikipedia, DeepState and ISW plus geocoded news; tessellated place polygons | `Data/control_latest_2026.zip` is a Git LFS object of 23,976,646 bytes served at `https://media.githubusercontent.com/media/zhukovyuri/VIINA/main/Data/control_latest_2026.zip` (200, `application/zip`); last commit 13 Sep 2026 10:58 UTC; `Data/gn_UA_tess.geojson` is a 31.7 MB plain file | Open Database Licence (ODbL), citation requested | Default control layer. Permission-free with attribution. Operator importer, not runtime. |
| DeepStateMap | Occupied, liberated and unknown-status polygons, attack-direction arrows, unit markers, assessment stamp | `GET https://deepstatemap.live/api/history/last` returns 627 KB of GeoJSON: 526 features, 124 polygons (occupied, liberated, unknown, CADR and CALR, Crimea, Transnistria, Abkhazia, South Ossetia) and 402 points; `datetime` "12.09 o 21:04"; `api/history` returns 401 | Licence of 3 Sep 2025: API use is granted only by the rights holder; free for volunteer, charitable and Ukraine-defence bodies; commercial use by prior agreement; requests at `https://api.deepstatemap.live/request`; no unauthorised proxying or redistribution; screenshots and visuals carrying the DeepState mark are free to reuse | Adapter is built but disabled until the operator records granted access in `ASE_UKRAINE_DEEPSTATE_ACCESS`. A request text is drafted in section 9 for the operator to send. |
| UN OCHA `UKR_Front_Line` | Weekly frontline lines derived from ISW and CTP | Hosted FeatureServer answers JSON and GeoJSON; latest features dated 8 Sep 2026; source field "Institute for the Study of War and American Enterprise Institute's Critical Threats Project" | "Intended for use only for humanitarian purposes"; credit ISW and CTP | Optional layer behind `ASE_UKRAINE_OCHA_HUMANITARIAN=true`, which the operator sets only for a humanitarian deployment. Off by default. |
| ISW and CTP ArcGIS layers | Assessed control of terrain polygons | Items are public on arcgis.com | Written consent is required to incorporate the geodata into another mapping platform | Not used for geometry. Linked from the sources panel. |
| Wikimedia Commons `2022 Russian invasion of Ukraine.svg` | Crowd-drawn control map | 4.35 MB SVG, CC BY-SA 4.0, last revised 24 Apr 2026 | Free with attribution | Too stale to show as current. Not used. |
| geoBoundaries UKR ADM1 | 27 oblast outlines, simplified GeoJSON | API answers; the simplified file is linked from `https://www.geoboundaries.org/api/current/gbOpen/UKR/ADM1/` | ODbL (OpenStreetMap derived) | Packaged once as `ukraine_oblasts.json`, simplified to under 150 KB. |

The existing `countries_110m.json` outline stays as the neighbour context. The
frontline directory already shipped in the map's Conflict panel
(`FrontlineSourcesPanel.tsx`) remains the statement of record on ISW, DeepState,
OCHA and Liveuamap terms; this page links to it rather than restating it.

### 2.2 Latest updates and assessments

| Source | Endpoint | Probe result | Use |
| --- | --- | --- | --- |
| ISW daily "Russian Offensive Campaign Assessment" | `https://www.understandingwar.org/wp-json/wp/v2/posts?search=Russian%20Offensive%20Campaign%20Assessment&per_page=10&_fields=id,date,link,title,excerpt` | 200; the RSS endpoints return 403 or HTML; newest post dated 12 Sep 2026 | New JSON connector `isw_assessments` storing title, link, date and a plain-text excerpt under 400 characters. The fair use and attribution policy revised 8 Jan 2026 permits citation with attribution; only the daily post metadata is stored. |
| Kyiv Independent | `https://kyivindependent.com/news-archive/rss/` | 200, valid RSS (the `/feed` and `/rss/` guesses are 404) | New RSS seed `news_kyiv_independent`. |
| Ukrinform, Ukrainska Pravda, Meduza (EN and RU), GOV.UK MoD news, ReliefWeb, Crisis Group, Interfax (state agency), Russia MFA (state official), BelTA (state) | Already seeded | Running | Reused through keyword lenses; state-controlled feeds keep their `state_controlled` tag and doubtful credibility. |
| Bellingcat | `https://www.bellingcat.com/feed/` | 200 | New RSS seed for the investigations lens. |
| UK Defence Intelligence updates | The GOV.UK search API returns no matching publications; the updates are posted on X and summarised in MoD news | Not a feed | Whatever the MoD news feed carries is shown; no X scraping. |
| Ukrainian Ministry of Defence site | `mod.gov.ua` is a Next.js site without RSS | 404 on every feed guess | Not a feed. General Staff figures come from the API below. |

### 2.3 Losses and casualties

| Source | Endpoint | Probe result | Basis | Use |
| --- | --- | --- | --- | --- |
| Ukrainian General Staff daily figures via russianwarship.rip | `/api/v2/statistics/latest`, `/api/v2/statistics/{YYYY-MM-DD}`, `/api/v2/statistics?date_from=&date_to=` | 200; 13 Sep 2026 is day 1663; 15 categories plus a daily `increase`; each record links the General Staff post as `resource`; the range query returned 13 records for 1 to 13 Sep | `claimed` (belligerent) | Runtime connector, one fetch per six hours, last 90 days retained for sparklines. |
| Oryx visually confirmed losses via `leedrake5/Russia-Ukraine` | `data/byType/YYYY-MM-DD.csv` and `data/bySystem/` on branch `main` | Repository pushed 13 Sep 2026 02:30 UTC, MIT licence; `data/byType/2026-09-12.csv` fetched (200) with per-type rows for both sides | `visually confirmed` | Operator importer `ase import-ukraine-losses`, daily. The `scarnecchia/oryx_data` mirror was last updated 21 Aug 2025 and is not used. |
| WarSpotting | `https://ukr.warspotting.net/api/losses/russia/{YYYY-MM-DD}`, `/api/losses/russia/{YYYY-MM}`, `/api/stats/russia` | 200 with geolocated Russian losses (model, status, nearest location, coordinates, date); the Ukraine-side paths return 404; the site's terms sit behind a bot challenge | `visually confirmed` | Phase 4 optional map layer once the operator has read its terms. Linked meanwhile. |
| UN Human Rights Monitoring Mission in Ukraine (HRMMU) | Listing `https://ukraine.ohchr.org/en/reports/protection-of-civilians` and monthly pages such as `/en/Protection-of-Civilians-in-Armed-Conflict-July-2026`; a half-year civilian casualty report for the first half of 2026 | 200; monthly pages March to July 2026 listed; the ReliefWeb API and RSS blocked the probe as bot traffic (406), but the app's existing ReliefWeb connector with an approved appname is unaffected | `documented` | Importer `ase import-ukraine-casualties` reads the listing and each monthly page, stores title, date, link and the killed and injured figures when a bounded regular expression finds them, otherwise the link alone. |
| Mediazona and BBC Russian named dead; UALosses | Web applications without a machine endpoint | No CSV or JSON URL in the page markup | `documented` (named) | Curated reference rows with `as_of` and a link, refreshed by the operator. |
| Kiel Ukraine Support Tracker | Excel release on the Kiel page (Release 30) | 200 | reported | Link-out card with a curated headline and date. No xlsx dependency. |

### 2.4 Reference content: equipment, forces, timeline

- The Wikidata entity API resolved all 20 sample equipment names on the first
  hit (T-90M, BMP-3, M2 Bradley, Iskander, HIMARS, Shahed-136, Lancet, Patriot,
  Pantsir-S1, NASAMS, Kh-101, Storm Shadow, FPV drone, Magura V5, Bohdana,
  TOS-1, Su-34, F-16, AK-12) and 19 carry a Commons image. The public figures
  importer already fetches Commons `extmetadata` for licence and credit and
  caches a bounded PNG; the same code path serves equipment and timeline images.
- Equipment, force organisation and timeline content is curated JSON written by
  hand with a Wikipedia or official link and an `as_of` date on every entry,
  then enriched through Wikidata for images, articles and identifiers. These
  are reference notes, not intelligence, and the page labels them as such.

## 3. Page design

Route `/conflicts/ukraine`, lazy page `features/ukraine/UkrainePage.tsx`, rail
entry "Ukraine war" between Cyber intelligence and Administration with a new
`ukraine` rail icon (a map pin over a broken line). The page is one scrolling
article with a sticky in-page navigation strip (Map, Updates, Figures, Timeline,
Forces, Equipment, Lenses, Sources) and a `?section=` query so links land on a
section. Layout is a 12-column grid at desktop and a single column below
1024 px. Cards use the existing surface, line and muted tokens. Series colours
are cyan for Ukraine, ember for Russia, amber for contested and muted for
unknown, validated for colour-vision safety with the dataviz validator before
the first commit.

1. **Hero strip.** Title, "Day N of the full-scale invasion" (from the General
   Staff record, falling back to a local count from 24 February 2022), the
   assessment date of the control snapshot, and four freshness chips (control
   snapshot, ISW assessment, General Staff figures, last feed poll).
2. **Map.** A 2D mercator MapLibre map through the existing `MapLibreEngine`,
   opened by the same tile-provider consent control the report evidence map
   uses, fitted to the Ukraine bounding box. Layers: oblast outlines; reported
   control as filled settlement cells (VIINA tessellation, simplified) with a
   dots fallback where an oblast exceeds its vertex budget; the frontline line
   and DeepState polygons only when their flags are set; a legend with the
   basis note; a hover tooltip naming the settlement, its status and which
   sources agreed; a "show on globe" link. The globe's Conflict panel is not
   changed in this work.
3. **Latest updates.** Three tabs: Assessments (ISW daily, MoD news), Ukrainian
   reporting (Kyiv Independent, Ukrinform, Pravda), Russian and independent
   Russian (Meduza, with Interfax and the MFA tagged as state). Each row shows
   source, credibility grade, time, title and link. A lens chip row (all,
   equipment, workforce, casualties, strikes, diplomacy) filters every tab.
4. **Headline figures.** One row of cards: General Staff claims for personnel,
   tanks, armoured vehicles, artillery, UAVs and missiles with the daily
   increase and a 30-day sparkline; Oryx confirmed totals per side with the
   destroyed, damaged, abandoned and captured split as a share bar; the latest
   HRMMU monthly killed and injured figures. Each card carries its basis badge
   and source link, and a table view sits behind each card for screen readers.
5. **Timeline.** A horizontal phase ribbon (Background 2014 to 2021; Invasion
   February to April 2022; Donbas summer 2022; Counteroffensives autumn 2022;
   Bakhmut winter 2022 to 2023; the 2023 counteroffensive; Avdiivka and
   attrition 2024; Kursk and long-range strikes 2024 to 2025; 2025; 2026)
   above a vertical list of event cards with date, title, three to five
   sentences of plain English, an image where a licensed one exists, and
   links. Theme chips (ground, air and missile, naval, diplomacy, mobilisation,
   economy) filter the cards. Choosing a phase scrolls the list to it.
6. **Forces.** Two columns, Russia and Ukraine, each an expandable tree of
   nested cards: political and military command, services and branches,
   operational groupings, armies and corps, notable formations. Nodes show
   role, the commander where a public figure record exists (linking to the
   figures tracker), a reported strength band with its source, and links. The
   tree is a CSS grid with connector borders, keyboard navigable, no image.
7. **Equipment.** Headings inside headings: Drones (reconnaissance, FPV,
   fibre-optic FPV, loitering munitions, long-range one-way attack,
   interceptor, naval and ground drones); Communications and electronic
   warfare (satellite links, tactical radios, command software, jamming and
   GNSS interference); Air defence (long range, medium range, short range and
   point defence, MANPADS and mobile fire groups, counter-drone); Land-attack
   missiles and glide bombs (ballistic, cruise, guided rockets, glide bombs);
   Artillery (self-propelled, towed, rocket, thermobaric); Small arms and
   infantry weapons (rifles, machine guns, anti-tank, mortars); Tanks; Infantry
   fighting vehicles and armoured personnel carriers; Aviation; Naval. Each
   speciality shows a Russia column and a Ukraine column of cards; each card
   has the image, a one-paragraph description, origin, role, reported numbers
   with source, the Oryx loss count where a system maps to an Oryx row, and
   links. A "compare" toggle collapses the cards into one table per speciality.
8. **Lenses.** Equipment news; Workforce news (mobilisation, conscription,
   recruitment, contract service, demobilisation, foreign personnel including
   DPRK troops, desertion); Casualty updates (HRMMU, General Staff claims, Oryx
   deltas, named-dead reference counts). Each lens is a bounded keyword match
   over retained events in the Ukraine bounding box and country set, listed
   newest first with a small stacked-columns chart of items per day by source
   group.
9. **Sources and doctrine.** Attribution for VIINA, ISW, DeepState, OCHA, Oryx,
   the General Staff, HRMMU, Wikimedia Commons and geoBoundaries; the licence
   of each; a plain statement of what the page cannot tell the reader.

## 4. Backend

Layering stays domain, application, adapters and api, with `ase.container` the
only composition root.

Domain (`ase/domain/ukraine/`)
- `control.py`: `ControlStatus` (ua, ru, contested, unknown), `SettlementControl`,
  `ControlSnapshot` (assessment date, release stamp, counts per status and
  oblast, attribution), `MAX_SETTLEMENTS = 12_000` and a byte bound.
- `frontline.py`: `FrontlineFeature` (class occupied, liberated, unknown,
  historical, line), provider, assessment stamp, download time, a vertex bound
  of 60,000 and a `simplify` that drops unit markers and arrows.
- `figures.py`: `ClaimedLosses` (General Staff record with day, categories,
  increase and resource link), `ConfirmedLosses` (Oryx per type and status per
  side), `CivilianHarm` (HRMMU month, killed, injured, link), basis enums.
- `lenses.py`: keyword lenses `EQUIPMENT`, `WORKFORCE`, `CASUALTIES`, `STRIKES`
  and `DIPLOMACY` in the `cyber_themes.py` style (word-boundary patterns,
  bounded text, a lens is a text match and never attribution).
- `reference.py`: `EquipmentEntry` (id, side, speciality path, name, wikidata,
  description, origin, role, reported numbers with source and as_of, Oryx keys,
  image id, links), `ForceNode` (tree), `TimelineEvent` (phase, date, title,
  text, theme, image id, links), each validating link hosts and text lengths.

Application (`ase/application/ukraine/`)
- `board.py`: `UkraineBoardService` assembling `UkraineBoard` from the control
  snapshot loader, the frontline provider when enabled, the figures store, the
  reference catalogue and the event store (bounding box and country queries as
  in `TrackerService._area_events`, a 14-day window, a bounded pool, lens
  application).
- Ports under `application/ports/`: `ControlSnapshotSource`,
  `FrontlineProvider`, `LossFiguresSource`, `UkraineReferenceSource`.

Adapters
- `adapters/geo/ukraine_control_import.py`: streams the VIINA zip with
  `zipfile` and `csv`, keeps the latest date per `geonameid` for the majority
  `status` and the three source columns, joins centroids and simplified cells
  from the tessellation file (a Douglas-Peucker pass to a vertex budget), and
  writes `resources/ukraine/control_snapshot.json` under 1.5 MB with
  attribution and the release stamp, using the existing bounded download and
  gzip guards.
- `adapters/geo/ukraine_frontline_deepstate.py` and `ukraine_frontline_ocha.py`:
  fixed-host providers behind the outbound guard, one request per six hours
  and per week respectively, a 1 MB response bound, polygons and lines only,
  the previous stamp kept so provider revisions are separated from observed
  change; disabled unless the flags in section 6 are set.
- `adapters/feeds/ukraine_general_staff.py`: JSON connector for
  russianwarship.rip emitting a daily claimed-losses record into a 90-day ring
  held by the service, never into the event store.
- `adapters/feeds/isw_assessments.py`: WordPress JSON connector producing NEWS
  events tagged `assessment`, with a source rating catalogue entry for ISW.
- `adapters/feeds/rss_seeds_outlets.py`: seeds for Kyiv Independent and
  Bellingcat; `source_rating_catalog.py` and `source_discovery.py` entries; the
  `PUBLISHER_SEEDS` count test updated.
- `adapters/geo/ukraine_losses_import.py`: the Oryx day file by date, falling
  back through the previous seven days, Oryx types mapped to the equipment
  specialities, written to `resources/ukraine/confirmed_losses.json`.
- `adapters/geo/ukraine_casualties_import.py`: the HRMMU listing and monthly
  pages, text-only parse, written to `resources/ukraine/civilian_harm.json`.
- `adapters/geo/ukraine_reference_import.py`: resolves the curated seeds
  (`ukraine_equipment_seeds.json`, `ukraine_forces.json`,
  `ukraine_timeline.json`) through the Wikidata entity client for QIDs,
  articles and images, caches images through the Commons path already used for
  portraits at 480 px JPEG under 60 KB each with licence and credit, and writes
  `resources/ukraine/reference.json` plus `resources/ukraine/images/`.
- `adapters/geo/ukraine.py`: `lru_cache` loaders for every snapshot.
- `adapters/cli_ukraine.py`: `ase import-ukraine-control`,
  `import-ukraine-losses`, `import-ukraine-casualties`,
  `import-ukraine-reference` and `import-ukraine-oblasts`, each with
  `--contact`.

API (`ase/api/routers/ukraine.py`, `schemas_ukraine.py`)
- `GET /api/conflicts/ukraine`: hero, figures, updates, lenses and snapshot
  metadata. Session revalidation, `private, no-store`.
- `GET /api/conflicts/ukraine/control`: control cells and dots (ETag, one-hour
  `max-age`).
- `GET /api/conflicts/ukraine/frontline`: provider features, or a `disabled`
  state with the reason.
- `GET /api/conflicts/ukraine/reference`: equipment, forces and timeline.
- `GET /api/conflicts/ukraine/images/{image_id}`: cached JPEG from the packaged
  store, same origin, so the Content Security Policy is unchanged.
- `GET /api/conflicts/ukraine/losses`: the General Staff series, Oryx totals
  and HRMMU months.
- OpenAPI export and `pnpm gen:api` after the schemas land.

Container: `container/ukraine.py` factory wiring loaders, providers and the
service; settings in `infrastructure/settings.py` and `.env.example`.

## 5. Frontend

`features/ukraine/` imports nothing from other features; shared pieces go to
`components` and `lib`.
- `UkrainePage.tsx` (layout and section navigation), `UkraineHero.tsx`,
  `UkraineMap.tsx` with `useUkraineMap.ts` (engine, layers, hover),
  `controlLayers.ts` (GeoJsonLayer for cells, ScatterplotLayer fallback,
  PathLayer for the line), `UpdatesTabs.tsx`, `FiguresStrip.tsx`,
  `TimelineRibbon.tsx` and `TimelineList.tsx`, `ForcesTree.tsx`,
  `EquipmentSections.tsx` with `EquipmentCard.tsx` and `EquipmentTable.tsx`,
  `LensPanel.tsx`, `SourcesFooter.tsx`, `useUkraineBoard.ts`,
  `useUkraineReference.ts`, `lenses.ts` (chip definitions from the generated
  enum names).
- `lib/api/ukraine.ts`: zod schemas over the generated types with `.default`
  for nullable fields, and fetchers for the five endpoints.
- `components/charts`: reuse `Sparkline`, `ShareBar`, `StackedColumns` and
  `BarList`. The phase ribbon stays inside the feature unless a second page
  needs it.
- `components/ui/BasisBadge.tsx`: the basis badge shared with the trackers.
- `app/shell/LeftRail.tsx` and `railIcons.tsx`: the entry and icon.
- `app/router/routes.tsx`: the route and a DEV-only `/dev/ukraine-preview`
  fixture page for visual checks through a temporary launch configuration.
- Tests: `ukraine.test.tsx` (board rendering, tabs, lens filtering, basis
  badges), `ukraineMap.test.tsx` (layer construction, disabled provider state,
  legend), `timeline.test.tsx`, `forces.test.tsx`, `equipment.test.tsx`
  (nested headings and the compare table), MSW handlers for every new endpoint
  in `test/handlers.ts`, fixtures in `test/fixtures.ukraine.ts`.

## 6. Configuration and update cadence

Environment (all `ASE_` prefixed, documented in `.env.example`):
- `ASE_UKRAINE_DEEPSTATE_ACCESS` (unset or `granted`) and
  `ASE_UKRAINE_DEEPSTATE_KEY` if DeepState issues one.
- `ASE_UKRAINE_OCHA_HUMANITARIAN` (`false`) for humanitarian deployments only.
- `ASE_UKRAINE_WARSPOTTING` (`false`), reserved for phase 4.
- The existing `ASE_FEEDS_CONTACT` and `ASE_RELIEFWEB_APPNAME`.

Cadence: General Staff every six hours; ISW hourly through the feed worker; RSS
seeds on the normal news schedule; DeepState every six hours when granted; OCHA
weekly when enabled; VIINA, Oryx and HRMMU through the operator importers,
which the operator schedules with a documented daily command (the app installs
no scheduler); reference content on demand. The page polls its board endpoint
every five minutes while visible and shows the age of each element.

## 7. Tests and checks

Backend: unit tests for the VIINA stream parser on a fixture zip, the
tessellation simplifier's vertex budget, the DeepState simplifier dropping
points, the Oryx type mapping, the HRMMU number pattern on saved pages, the lens
patterns (positives and near misses), the board service with a fake store and
clock, the router with session revalidation, and the CLI commands with offline
fakes for Wikidata and Commons. Coverage stays at or above the 90 percent gate
and no test touches the network. Frontend: vitest with MSW default handlers,
axe checks on the page, typecheck and lint. Repo: the file length script, ruff,
mypy strict, import-linter and pre-commit. Visual check through the DEV preview
route with a temporary launch configuration that is deleted afterwards.

## 8. Phases

Status: phases 1 to 4 delivered by 14 September 2026 (`docs/UKRAINE_WAR_TRACKER.md`).
Phase 5 (DEV polish and the wider documentation pass) remains.

1. **Skeleton and map.** Domain, oblast import, VIINA importer and snapshot,
   board endpoint, page shell, rail entry, map with control cells and legend,
   General Staff cards, latest-updates tabs from the existing feeds plus Kyiv
   Independent and ISW. Acceptance: the page loads with a real control
   snapshot, figures and updates, and every test and check passes.
2. **Timeline, forces and equipment.** Curated seeds written and resolved,
   images cached, the three sections rendered with nested headings and the
   compare table. Acceptance: every entry has a link and an as_of date, and
   every image carries a licence and credit.
3. **Losses, casualties and lenses.** Oryx and HRMMU importers, the figures
   strip complete, the three lens sections with charts.
4. **Authorised layers.** DeepState and OCHA providers behind their flags, the
   optional WarSpotting layer once the operator has read its terms, the Kiel
   card.
5. **Polish and documentation.** DEV preview, `docs/UKRAINE_WAR_TRACKER.md` for
   operators, updates to `MAP_TOOLS_AND_LAYERS.md`, `CONFLICT_COVERAGE.md`,
   `FRONTLINES_AND_UNREST.md` (the DeepState licence text now read in full),
   `DEVELOPMENT_STORY.md` and the master research plan checklist.

Each phase is a small set of conventional commits touching only this feature's
paths, so the concurrent session's work on the map controls is not disturbed.

## 9. Decisions for the operator and open notes

- **DeepState access.** The API answers without a key today, but its licence
  places API use at the rights holder's discretion and defines free use for
  volunteer, charitable and defence bodies. The adapter stays off until access
  is recorded. Suggested request text for the operator to send through
  `https://api.deepstatemap.live/request` (the form is in Ukrainian):
  "I run a self-hosted, non-commercial open-source OSINT research application
  (The All Seeing Eye, github.com/ShabalalaWATP/OSINT) for personal analysis.
  I would like permission to fetch the latest control map from
  deepstatemap.live/api/history/last at most four times a day, displayed with
  the DeepStateMap credit and link, never redistributed or proxied to others.
  Please let me know the terms or key required." Nothing has been sent.
- **ReliefWeb appname.** If an approved appname is already configured, the
  HRMMU reports can also arrive through the existing connector; the importer
  works without it.
- **New sources.** Kyiv Independent, ISW daily assessments and Bellingcat are
  added as unassessed headline feeds under the normal source controls.
- **Oryx mirror.** The day file for the current date is fetched by name and the
  importer records which date it obtained, which the page shows.
- **Russian Ministry of Defence claims** are not connected: no machine feed was
  found. Russian claims reach the page only through the state-tagged agency
  feeds already seeded.
- **Granularity.** Settlement cells are simplified to a vertex budget; where
  the simplified cells still exceed the bound for a dense oblast, that oblast
  falls back to dots, and the legend shows both states.

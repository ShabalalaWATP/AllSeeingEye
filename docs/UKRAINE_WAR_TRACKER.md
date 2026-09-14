# Ukraine war tracker

A left-rail workspace at `/conflicts/ukraine` that shows reported territorial control, the
belligerents' own figures, published assessments and retained reporting on Russia's war in
Ukraine. Phases 1 to 4 of `docs/UKRAINE_WAR_TRACKER_PLAN.md` are delivered: the map with
flagged provider layers, headline figures including visually confirmed losses and documented
civilian harm, grouped updates, the timeline, force organisation, the equipment catalogue,
the three news lenses with charts and the sources footer.

## What the page shows

- **Map.** A 2D mercator map fitted to Ukraine with oblast outlines (geoBoundaries, ODbL),
  Russian-held and contested areas dissolved from settlement cells, and the settlements
  within 25 km of a non-Ukrainian-held place as dots. Hovering a dot names the settlement,
  its reported status, the three source votes and the date the status began. The legend
  and a method note say that this is a reported line, not observed positions. Without
  WebGL the oblast table carries the same numbers.
- **Latest updates.** Retained items from the last 14 days that concern the war, grouped
  by who reports them: assessments (ISW, MoD news), Ukrainian reporting (Kyiv Independent,
  Ukrinform, Pravda), Russian and independent Russian (Meduza; Interfax, the MFA and TASS
  are labelled state media) and international. Lens chips (equipment, workforce,
  casualties, strikes, diplomacy) are bounded vocabulary matches, never judgements.
- **Headline figures.** The General Staff of Ukraine's cumulative claims of Russian losses
  for six categories with the day's stated increase and a 30-day sparkline of daily
  increases, each badged `Claimed`; the reported count of Russian-held places badged
  `Reported`; Oryx totals per side with the destroyed, damaged, abandoned and captured
  split and a month of daily totals, badged `Visually confirmed`; and the latest month of
  civilians killed and injured verified by the UN monitoring mission, badged `Documented`.
  A table lists every claimed category.
- **Timeline.** A phase ribbon from 2014 to the current year over dated event cards with a
  theme filter; each card carries plain English, a source link and, where Commons holds a
  licensed image of the subject, a captioned image.
- **Force organisation.** Two expandable trees (Russia, Ukraine) of reported command
  structure: command, ministry, general staff, groupings and services, corps and branches.
  Nodes show the reported commander (linking to the public figures tracker where a roster
  record exists), a strength estimate naming whose, links and an as-of date.
- **Equipment by speciality.** Ten specialities (drones; communications and electronic
  warfare; air defence; land-attack missiles and glide bombs; artillery; small arms; tanks;
  infantry fighting vehicles and carriers; aviation; naval), each with sub-headings and a
  Russia and a Ukraine column of cards: image, role, description, origin, reported numbers
  naming whose, links and an as-of date. A compare toggle renders the speciality as a table.
- **Lenses.** Equipment, workforce and casualty news: for each lens a stacked column chart
  of retained items per day by reporting group over the window and the matching items. The
  casualties lens also carries the HRMMU monthly table and the curated casualty references
  (Mediazona and BBC named dead, UALosses, the presidential statement, Russian ministry
  claims not collected, the Kiel support tracker), each with its basis and date.
- **Provider layers.** With a flag set, the map draws DeepStateMap's occupied, liberated,
  unknown and pre-2022 areas or OCHA's weekly line in provider hues distinct from the VIINA
  vote, and WarSpotting's geolocated photographed losses as markers with a hover tooltip.
  A note under the legend names the provider, its status (ready, stale, unavailable) and its
  terms, or says why the layer is off. The page never substitutes one provider for another.
- **Sources.** Attribution, licence and the doctrine in plain words.

## Data and cadence

| Element | Source | How it arrives |
| --- | --- | --- |
| Control snapshot | VIINA 2.0 (Zhukov and Ayers, Harvard), ODbL | Operator command `uv run ase import-ukraine-control`, daily. Downloads the current year's LFS release (about 24 MB) and the 31 MB tessellation, keeps the latest day per place, dissolves areas with shapely, writes `resources/ukraine_control.json` (about 700 KB, at most 12,000 settlements). |
| Oblast outlines | geoBoundaries UKR ADM1, ODbL | `uv run ase import-ukraine-oblasts`, rarely. Writes `resources/ukraine_oblasts.json` (about 110 KB). |
| General Staff claims | russianwarship.rip mirror of the General Staff posts | Feed connector `ukraine_general_staff`, every six hours, last 90 days, one event per day with the figures in attributes. Grade C, credibility cannot be judged, tagged `interested_party`. |
| ISW assessments | WordPress posts index of understandingwar.org | Feed connector `isw_assessments`, hourly, ten newest posts titled "Russian Offensive Campaign Assessment"; title, link, date and a plain-text excerpt under 400 characters. |
| Kyiv Independent, Bellingcat | Public RSS | New seeds in the outlet list, under the normal source controls. |
| Reference notes | Hand-written seeds `ukraine_equipment_seeds.json`, `ukraine_forces_seeds.json`, `ukraine_timeline_seeds.json` | `uv run ase import-ukraine-reference` resolves each seed through the Wikidata entity client (explicit `wikidata_id` wins, otherwise a search whose label shares a word), adds the article link, and caches the Commons image named by P18 as a 480 px JPEG under 60 KB with its licence and credit, into `resources/ukraine_reference.json` and `resources/ukraine_images/`. Around 110 images, 3.7 MB. |

| Oryx losses | `leedrake5/Russia-Ukraine` daily CSV mirror (MIT) of Oryx | `uv run ase import-ukraine-losses`, daily. Fetches the newest day file within seven days and a month of totals, keeps plain equipment types mapped to the page's specialities, writes `resources/ukraine_losses.json`. |
| Civilian harm | HRMMU monthly pages at ukraine.ohchr.org plus `ukraine_casualty_references_seeds.json` | `uv run ase import-ukraine-casualties`, monthly. Reads the listing and each monthly page for the fixed sentence with killed and injured; months without it keep their link and no figures. Writes `resources/ukraine_casualties.json`. |
| Frontline providers | DeepStateMap `api/history/last` or the OCHA `UKR_Front_Line` layer | Runtime, behind `ASE_UKRAINE_DEEPSTATE_ACCESS=granted` or `ASE_UKRAINE_OCHA_HUMANITARIAN=true`: one bounded request every six hours (DeepState) or seven days (OCHA), the last good snapshot kept and served as stale on failure. Off by default. |
| Spotted losses | WarSpotting monthly API | Runtime, behind `ASE_UKRAINE_WARSPOTTING=true`: the current and previous month every six hours, at most 3,000 markers. Off by default. |

Loaders are cached per process, so restart the API after re-running an importer. The page
polls its board every five minutes while visible.

## Endpoints

- `GET /api/conflicts/ukraine` returns the board: day number and its basis (claimed by the
  General Staff, or computed from 24 February 2022), grouped updates with lenses, the claim
  series, the control summary and freshness stamps. `private, no-store`.
- `GET /api/conflicts/ukraine/control` returns the settlements, areas and outlines.
  `private, max-age=3600`; the payload changes only when the operator re-imports.

- `GET /api/conflicts/ukraine/frontline` and `/spotted` return a provider state (disabled,
  ready, stale, unavailable) with its reason, terms and, when ready, the geometry or markers.
  `private, max-age=900`.
- `GET /api/conflicts/ukraine/reference` returns the specialities, themes, equipment,
  forces, phases, events and the image manifest; 404 until the operator has imported.
- `GET /api/conflicts/ukraine/images/{id}.jpg` serves one cached image from the package
  (`private, max-age=86400`); the page fetches it through the session and shows it as an
  object URL, so no external host joins the Content Security Policy.

All require a session and revalidate it like the other trackers.

## Doctrine

Nothing on the page is verified by the application. Control status per settlement is the
source's majority vote of Wikipedia crowd maps, those maps boosted by geocoded news,
DeepStateMap and ISW polygons; ISW no longer contributes in 2026, which the votes show.
The General Staff is a party to the conflict reporting its own count of the adversary's
losses. ISW is a named institute with a declared analytical stance. State-controlled
feeds keep their caution. DeepStateMap, ISW control-of-terrain geodata and the UN OCHA
frontline layer are not drawn: their terms require the rights holder's permission or a
humanitarian purpose. `docs/FRONTLINES_AND_UNREST.md` and the map's Conflict panel carry
the access routes, and the plan's section 9 holds a request text the operator may send to
DeepState. Setting a provider flag is the operator's declaration that the terms are met; the
code only reads the flag. Oryx counts are photographed losses and undercount by design;
HRMMU figures are verified civilian casualties and the mission says the true numbers are
higher, above all in occupied territory.

## Reference content and its limits

The notes were written by hand from public reporting up to mid-2026 and dated on each entry;
the 2026 phase and the July 2026 command change rest on the encyclopaedic summary current at
the time of writing and say so. Nothing in them is intelligence. Numbers are public estimates
that name their source (Oryx counts are visually confirmed and undercount by design; General
Staff figures are claims). Wikidata provides the identifier and article; where an item has no
Commons image the card runs without one; where no Wikidata item exists the seed keeps a
hand-written link. Re-run the importer after editing a seed, and review image licences and
credits in the catalogue before committing.

## Verification

`backend/tests/test_ukraine.py` covers the VIINA parser and dissolve on a synthetic
tessellation, the bounds, the outline simplifier, the packaged snapshots, the claim
round-trip through event attributes, the lens vocabulary, the update grouping and war
relevance rule, both connectors on saved fixtures, the board service and the two
endpoints. `tests/test_ukraine_reference.py` covers the seed files, the packaged catalogue and images,
seed resolution on fakes, the bounds and validation, and the two endpoints.
`tests/test_ukraine_figures.py` covers the Oryx and HRMMU importers on mock transports,
the packaged figures, the bounds, the lens series, the three provider parsers, the flagged
providers' caching and stale states, and the board and provider endpoints.
`frontend/src/features/ukraine/ukraine.test.tsx` covers the page without
WebGL, the tabs and lenses, the claim badges and links, a failed board, the rail entry
and the layer colours; `reference.test.tsx` covers the timeline filters, the force
trees, the equipment headings, compare table and captioned images, and a missing catalogue. The DEV-only route `/dev/ukraine-preview` frames the page with
fixture data and a reduced copy of the real snapshot for visual checks; it needs no
account and sends no credential.

# Ukraine war tracker

A left-rail workspace at `/conflicts/ukraine` that shows reported territorial control, the
belligerents' own figures, published assessments and retained reporting on Russia's war in
Ukraine. Phase 1 of `docs/UKRAINE_WAR_TRACKER_PLAN.md` is delivered: the map, headline
figures, grouped updates with lenses, and the sources footer. Timeline, force organisation,
equipment, losses and casualty importers follow in later phases.

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
  increases, each badged `Claimed`, plus the reported count of Russian-held places badged
  `Reported`. A table lists every claimed category.
- **Sources.** Attribution, licence and the doctrine in plain words.

## Data and cadence

| Element | Source | How it arrives |
| --- | --- | --- |
| Control snapshot | VIINA 2.0 (Zhukov and Ayers, Harvard), ODbL | Operator command `uv run ase import-ukraine-control`, daily. Downloads the current year's LFS release (about 24 MB) and the 31 MB tessellation, keeps the latest day per place, dissolves areas with shapely, writes `resources/ukraine_control.json` (about 700 KB, at most 12,000 settlements). |
| Oblast outlines | geoBoundaries UKR ADM1, ODbL | `uv run ase import-ukraine-oblasts`, rarely. Writes `resources/ukraine_oblasts.json` (about 110 KB). |
| General Staff claims | russianwarship.rip mirror of the General Staff posts | Feed connector `ukraine_general_staff`, every six hours, last 90 days, one event per day with the figures in attributes. Grade C, credibility cannot be judged, tagged `interested_party`. |
| ISW assessments | WordPress posts index of understandingwar.org | Feed connector `isw_assessments`, hourly, ten newest posts titled "Russian Offensive Campaign Assessment"; title, link, date and a plain-text excerpt under 400 characters. |
| Kyiv Independent, Bellingcat | Public RSS | New seeds in the outlet list, under the normal source controls. |

Loaders are cached per process, so restart the API after re-running an importer. The page
polls its board every five minutes while visible.

## Endpoints

- `GET /api/conflicts/ukraine` returns the board: day number and its basis (claimed by the
  General Staff, or computed from 24 February 2022), grouped updates with lenses, the claim
  series, the control summary and freshness stamps. `private, no-store`.
- `GET /api/conflicts/ukraine/control` returns the settlements, areas and outlines.
  `private, max-age=3600`; the payload changes only when the operator re-imports.

Both require a session and revalidate it like the other trackers.

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
DeepState.

## Verification

`backend/tests/test_ukraine.py` covers the VIINA parser and dissolve on a synthetic
tessellation, the bounds, the outline simplifier, the packaged snapshots, the claim
round-trip through event attributes, the lens vocabulary, the update grouping and war
relevance rule, both connectors on saved fixtures, the board service and the two
endpoints. `frontend/src/features/ukraine/ukraine.test.tsx` covers the page without
WebGL, the tabs and lenses, the claim badges and links, a failed board, the rail entry
and the layer colours. The DEV-only route `/dev/ukraine-preview` frames the page with
fixture data and a reduced copy of the real snapshot for visual checks; it needs no
account and sends no credential.

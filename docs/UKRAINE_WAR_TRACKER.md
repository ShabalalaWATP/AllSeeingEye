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
- **AI digest.** A fortnightly summary of battlefield and political change, written by the
  assigned model from the sources already on this page. See "The fortnightly AI digest".
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
- **Force organisation.** Two expandable trees, Russia first and Ukraine below it, of reported
  command structure from the supreme command down to every formation of regiment size and
  above that the public Wikipedia order of battle lists (about 340 Russian and 320 Ukrainian
  entries). The hand-written upper tiers keep their own wording; the imported formations state
  which public tree they came from and when. Battalions, companies, individual ships and
  irregular volunteer groups are left out. A "Find a unit" box lists matches by name or
  commander and opens the chain down to the chosen one. Nodes show the reported commander
  (linking to the public figures tracker where a roster record exists), a strength estimate
  naming whose, links and an as-of date.
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

## Daily operation

Run from `backend/` with the virtual environment; each command is bounded and idempotent
and rewrites one packaged file. Restart the API afterwards because loaders are cached.

```bash
uv run ase import-ukraine-control        # daily: VIINA control snapshot (about 55 MB download)
uv run ase import-ukraine-losses         # daily: Oryx newest day and a month of totals
uv run ase import-ukraine-casualties     # monthly: HRMMU pages and curated references
uv run ase import-ukraine-reference      # after editing a seed: Wikidata and Commons images
uv run ase import-ukraine-oblasts        # rarely: geoBoundaries outlines
```

Schedule the first two with the operating system's scheduler if wanted; the application
installs none. Every importer takes `--contact` for the User-Agent and `--destination`
for a path outside the package. Review `git diff` of the packaged JSON before committing
it: a changed release stamp, a missing month or a shrunken image count is visible there.

If the control import fails, the previous snapshot stays in place and the page keeps
showing its assessment date. If HRMMU changes the wording of its monthly summary, the
month keeps its link and shows no figures until the sentence pattern in
`ukraine_casualties_import.py` is updated. If the Oryx mirror stops updating, the page
shows the last recorded day; the mirror's freshness is visible on the card.

## Endpoints

- `GET /api/conflicts/ukraine` returns the board: day number and its basis (claimed by the
  General Staff, or computed from 24 February 2022), grouped updates with lenses, the claim
  series, the control summary and freshness stamps. `private, no-store`.
- `GET /api/conflicts/ukraine/control` returns the settlements, areas and outlines.
  `private, max-age=3600`; the payload changes only when the operator re-imports.

- `GET /api/conflicts/ukraine/digest` returns the latest digest with its provenance and the
  few before it, plus the status (`ready`, `none`, `generating`, `unavailable`,
  `validation_failed`), a reason when there is one and whether the fortnight has ended.
  `private, no-store`. Reading it starts a generation only when the fortnight is up.
- `POST /api/conflicts/ukraine/digest/refresh` asks for a digest now. Administrators only,
  audited and rate limited; the work runs in the background and the same payload comes back.
- `GET /api/conflicts/ukraine/frontline` and `/spotted` return a provider state (disabled,
  ready, stale, unavailable) with its reason, terms and, when ready, the geometry or markers.
  `private, max-age=900`.
- `GET /api/conflicts/ukraine/reference` returns the specialities, themes, equipment,
  forces, phases, events and the image manifest; 404 until the operator has imported.
- `GET /api/conflicts/ukraine/images/{id}.jpg` serves one cached image from the package
  (`private, max-age=86400`); the page fetches it through the session and shows it as an
  object URL, so no external host joins the Content Security Policy.

All require a session and revalidate it like the other trackers.

## The fortnightly AI digest

One bounded model call every 14 days writes a short digest of what changed, so a reader who
cannot follow the page daily still gets a plain-language account with its evidence attached.

**Evidence pack.** At most 40 trimmed, dated items drawn only from what the board already
gathered: up to six ISW assessment excerpts, up to fourteen battlefield headlines and up to
ten political headlines from the Ukraine-relevant feeds, the latest General Staff claim with
the statement that it is one side's claim, settlement control change inside the fortnight
from the imported VIINA snapshot, Oryx totals per side with their as-of date, and the latest
HRMMU month with its period. Labels are capped at 180 characters and details at 420. Each
item carries an id (`e1`, `e2` and so on), its feed source id, its date and its link. Where a
strand has nothing, the pack says so in plain words rather than leaving a gap: no control
snapshot imported, no settlement change recorded inside the fortnight, no Oryx import, no
HRMMU import, no assessment collected, no claim collected. The pack records the exact feed
source ids and the date range that fed it.

**The call.** One request to the globally assigned assessment profile, capped at 3,000
completion tokens, with a strict JSON schema: a restated period, a battlefield strand and a
political strand (each a summary plus two to five changes, every change carrying its text and
the evidence ids it rests on), two to four things to watch and one to three caveats. The
prompt requires UK English, plain language, no em dashes, attribution of every claim to its
evidence ids, Russian and Ukrainian official statements written as claims rather than facts,
no invented place names, unit names, casualty figures, territorial percentages or links,
"reporting suggests" where sources disagree, and a plain statement when the fortnight held
little verifiable change. The pack is labelled untrusted evidence, never instructions.

**Mechanical validation before storing.** Every evidence id must exist in the pack and appear
at most once per change; every number in the text must appear in the pack (compared after
stripping commas and leading zeros, so "1,000,000" and "1000000" are the same figure); every
ISO date must fall inside the period; the restated period must match the pack exactly; no
text may contain a URL or an em dash; the payload must stay inside its length bounds. A
failure is fed back once as a correction and the call is made again. If the second answer
also fails, nothing is stored and the page says the checks rejected the answer.

**Cadence and cost.** `DIGEST_INTERVAL` is 14 days. A reader who opens the page after that
starts one generation in the background; readers never start anything else, and a failed
attempt waits six hours before another is tried. An administrator can ask for one sooner: the
request is audited (`ukraine_digest_refresh_requested`), limited to two per administrator per
hour and four across the installation per day, and the work still runs in the background.
Cost per fortnight is therefore one call, or two when the first answer fails validation:
roughly 8,000 to 12,000 prompt tokens and up to 3,000 completion tokens, charged to the
system allowance as `system:ukraine_digest` (ADR 0019). The provider audit trail records the
call under purpose `ukraine_digest`.

**What is stored.** The last six digests only (`DIGEST_RETENTION`), in `ukraine_digests`:
period, payload JSON, model, generated time, token counts, the feed source ids, the evidence
item count and the citations the digest actually named. Prompts are never stored, and the
full evidence window is not stored: only the frozen citations behind the stored assessment.
The generation holds no database transaction across the model call and takes the shared
admission guard only for the final write.

**Honest limitations.** The digest reads retained reporting, not the war. It can only be as
good as a fortnight of free feeds, which are uneven, English-weighted and incomplete. The
checks are arithmetic and string checks: they can show that a figure was copied from the
pack, never that the model understood the fortnight or weighted it sensibly. Control change
depends on the operator having imported a VIINA snapshot; without one the digest says so.
No digest has yet been produced against a real model in this repository, so the wording
quality is unproven.

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
`tests/test_ukraine_digest.py` covers the evidence pack (every strand, the bounds, the
trimming, the plain statements when a strand is missing), the prompt and schema, the single
retry and every mechanical check. `tests/test_ukraine_digest_service.py` covers the
fortnightly cadence, the retention bound, the system attribution, the administrator refresh
with its authorisation, audit and limits, the model-off, no-evidence, exhausted-allowance and
provider-failure states, the SQL store and the two endpoints;
`tests/test_ukraine_digest_migration.py` covers migration `0056` both ways.
`frontend/src/features/ukraine/ukraineDigest.test.tsx` covers the panel in every state
(ready, none, generating, stale, unavailable, rejected, load failure), the history selector
and the administrator control, including a refused refresh.
`frontend/src/features/ukraine/ukraine.test.tsx` covers the page without
WebGL, the tabs and lenses, the claim badges and links, a failed board, the rail entry
and the layer colours; `reference.test.tsx` covers the timeline filters, the force
trees, the equipment headings, compare table and captioned images, and a missing catalogue. The DEV-only route `/dev/ukraine-preview` frames the page with
fixture data and a reduced copy of the real snapshot for visual checks; it needs no
account and sends no credential.

# Public figures tracker

A curated roster of current heads of state, heads of government, named senior
ministers and chiefs for the United Kingdom, United States, Russia, China and
Belarus, and the leaders of
NATO, the United Nations, the European Commission and the European Council, shown on
the map as circular portraits and on `/trackers/figures` as a board. Each marker is
placed by the newest retained public report that names the office-holder, or at the
seat of office when nothing located names them. The feature never tracks people; it
summarises what public reporting already says.

## Scope and doctrine

- Office-holders only. The roster contains the office, the incumbent's public name and
  aliases as recorded on Wikidata, and a seat of office. No private individuals,
  family members, staff, schedules, travel records or device data are collected.
- A placement is a reporting fact, not presence. The basis is always stated:
  `reported_place` (a geolocated report names the person), `reported_country`
  (only country context is available) or `seat` (a default shown at the seat of
  office). Rings on the map and labels in every list carry the basis.
- Absence of reporting never means an official is at home. The board and the
  inspector say so explicitly, and the seat placement is described as a default.
- Office releases and state media are interested-party sources; they enter the store
  through the ordinary feed grading and are shown with their grade.
- Mentions are bounded: the first 4,000 characters of title, translated title and
  summary, at most one mention per person per report, and the newest five reports
  per figure are returned.

## Roster import

`uv run ase import-public-figures` refreshes `backend/src/ase/resources/public_figures.json`
from Wikidata (CC0) and Wikimedia Commons. It runs only from the CLI, never at request
time, and it is the only network path in the feature.

- Countries and organisations are a fixed list in `adapters/geo/public_figures_targets.py`.
- Incumbents come from the country items (`P35` head of state, `P6` head of
  government) and, for organisations, from open-ended `P39` position statements.
- Named senior posts are fixed Wikidata position items in `POSITIONS`: six for the
  UK (defence, foreign, chancellor, home, Chief of the Defence Staff, Chief of SIS),
  twelve for the United States (vice president, State, Defense, Treasury, Attorney
  General, Homeland Security, Chairman of the Joint Chiefs, CIA, DNI, FBI, Speaker,
  UN ambassador), five for Russia (foreign, defence, Security Council secretary, FSB
  director, Duma chairman), nine for China (foreign, defence, NPC chairman, CMC vice
  chairman, vice president, CPPCC chairman, state security, vice premier, public
  security) and two for Belarus (foreign minister, deputy prime minister). The
  incumbent is the newest open-ended holder with a recorded start date, because many
  historical holders on Wikidata lack an end date. They carry the `senior_official`
  role and the country seat. The roster held 103 figures on 13 September 2026.
- Office titles prefer the country's declared office item, then the person's newest
  current post whose label reads like the role, then a plain "Head of state" or
  "Head of government". Two roster entries (North Korea's premier, Latvia's prime
  minister) carried the plain fallback on 13 September 2026; review them after each
  import.
- Labels use English with the multilingual default as a fallback, because several
  incumbents have no English `rdfs:label` on Wikidata.
- Portraits are the person's `P18` image, fetched at 160 px, centre-cropped, masked
  to a 64 px circle, quantised and stored as base64 PNG (2 to 4 KB each). The
  Commons licence short name, artist credit (HTML stripped) and file page URL are
  kept per image. Review the licences before committing a refreshed roster; the 86
  current portraits are public domain, Creative Commons, OGL, KOGL or GODL, and one
  official (the Chief of SIS) has no Commons portrait and uses the neutral bust.
- Wikimedia's robot policy requires a contact in the User-Agent. The default is the
  repository URL; pass `--contact` to change it. The importer pauses two seconds
  between queries and retries a 429 once after the advertised wait.
- The importer's output message names the exception type only; no hostnames or
  response bodies are echoed.

Multi-capital countries return one row per capital; the first row wins. Countries
where one person holds both offices produce a single
`head_of_state_and_government` entry.

## Name matching

`domain/public_figures.py` matches names deliberately narrowly:

- the full name, multi-word aliases of at least ten characters with one
  non-title word of four or more letters, and a distinctive surname of at least
  five letters;
- realm suffixes ("of Sweden") are dropped before the surname is taken, title words
  ("His Majesty", "President") never match alone, and a small deny list removes
  surnames that are also common given names or shared with other public people
  (Silva, Costa, Sharif, Alexander, Charles, Salman, Haakon, Gustaf, Saud);
- a name shared by two roster people is dropped entirely; Charles III is one person
  holding three roster entries, matched once and placed identically for each.

Denials and reported plans still count as mentions. The placement basis, not the
matcher, tells the reader what the mention establishes.

## API and layering

- `GET /api/figures` returns the roster with placements, mention counts, the latest
  five reports per figure and the roster retrieval date. It requires a signed-in
  session, revalidates the session after computing the board and is marked
  `private, no-store`. Portraits travel as base64 in the payload so no separate
  unauthenticated image route exists.
- `application/public_figures.py` scans up to 3,000 NEWS, POLITICAL and CONFLICT
  events from the last 72 hours of the bounded in-memory store. Nothing is persisted.
- `container/public_figures.py` loads the packaged roster once per process and
  validates every field (bounded lengths, roles, coordinates, base64 alphabet).

## Frontend

- The map layer is off by default. The "Public figures" panel on the left rail
  toggles it, lists the visible figures with their basis, filters by name, office or
  country, and can hide seat defaults. Selecting a figure flies to the placement and
  opens an inspector with the basis, its explanation, the recent reporting with
  grades and the portrait credit.
- Markers are the portrait in a ring coloured by basis (cyan reported place, amber
  reported country, grey seat). Figures without a portrait use a neutral bust.
- The layer loads only for a signed-in identity, forgets its data when the identity
  or workspace revision changes, and refreshes every five minutes while on.
- `/dev/figures-preview` (development builds only) frames the panel, inspector and
  board with fixture data and three roster portraits for layout checks.

## Verification, 13 September 2026

Backend: 17 focused tests (roster bounds and licences, matcher rules, placement
precedence, loader rejections, the authenticated board, importer office ranking and
entry merging, portrait cropping, a canned SPARQL and Commons import, the 429 retry
and the CLI) pass. Ruff, formatting, mypy strict and the import contracts pass.
Frontend: eleven tests across the hook, layers, panel, inspector and tracker page
pass alongside typecheck, lint and the full suite. The panel, inspector and board
were checked visually on the development preview route with real portraits. The
live import was run twice against Wikidata to produce the packaged roster; the
marker rendering on the deck.gl globe was verified by layer tests only.

## Reporting sources for placements

Placements can only come from reporting the store retains, so the feeds matter as
much as the roster. On 13 September 2026 six feeds were added for this purpose:
GOV.UK Ministry of Defence, Prime Minister's Office and Home Office news, White
House news and US Department of Defense news as official B-grade statement feeds,
and CGTN China as C-grade state-controlled media. All were fetched live before
being seeded. Official releases are interested-party sources and carry the
`official` tag; state media carries `state_controlled` with doubtful credibility.

Tried and left out: the Kremlin English feed serves only plain HTTP (its TLS
handshake fails), the US State Department feed returns 407, the Chinese MFA and
Belarusian presidential, MFA and defence sites return HTML rather than a feed,
Xinhua's English RSS has not updated since 2017, and BelTA's English site returns
403. BelTA's Russian-language feed works but Cyrillic text would not match the
English names and aliases in the roster, so it was not added for this purpose.
Belarusian and Chinese officials therefore depend on wire, broadcaster and
regional English reporting, and most will sit at their seat most of the time.

## Follow-ups

- Wikidata lists the incumbent on the retrieval date. A change of office is not
  visible until the roster is re-imported, so the roster date is shown everywhere.
- Head-of-government coverage depends on Wikidata's `P6` statement; some countries
  return only a head of state.
- Russia's Chief of the General Staff, SVR director and presidential press secretary,
  the US national security adviser, China's Taiwan Affairs Office director and
  Belarus's defence minister, KGB chairman and Security Council secretary have no
  position item with a jurisdiction and current holder on Wikidata, so they are not
  in the roster. Adding them needs a hand-curated entry, not an import rule.
- Reporting that names an official without a geolocation leaves the marker at the
  seat. A later step could geocode the report's place names through the existing
  gazetteer path.

# Reference notes for aircraft, vessels and aircraft types

The map shows aircraft and vessels by the identifiers they broadcast. Reference notes
give those identifiers public background: a name, a one-line description, an operator
or flag, and links. They are background, never confirmation of identity; identifiers
are reused, mistyped and spoofed, and every note says so.

## What is packaged

`backend/src/ase/resources/reference_entities.json` holds three tables:

| Table | Key | Source | Count on 13 September 2026 |
|---|---|---|---|
| `vessel` | MMSI (nine digits) | Wikidata items with an MMSI (`P587`) and an English Wikipedia article; IMO, flag and type when recorded | 2,962 |
| `aircraft` | civil registration (`P426`), separators removed | Wikidata items with a registration and an article; many are notable incidents, which the description states | 373 |
| `aircraft_type` | ICAO type designator | Curated in `reference_aircraft_types.json`: 39 common military and government types with a Wikipedia link each | 39 |

The Wikidata tables are refreshed by `uv run ase import-reference`, which runs only from
the CLI, sends a contact in the User-Agent and retries a 429 once. The aircraft type
notes are hand-maintained because Wikidata has no usable type-designator property; the
code alone never distinguishes a civil airframe from a military variant, and the A330
and 747 notes say so.

Not imported: ICAO 24-bit addresses (three items on Wikidata), so lookups use the
registration and type an ADS-B provider decodes; MMSIs for lighthouses and AIS base
stations, which the vessel table does include when they have an article.

## Lookup

`GET /api/reference?kind=vessel|aircraft|aircraft_type&keys=a,b,c` returns matching
notes for at most 50 keys, requires a signed-in session, revalidates it after the
lookup and is marked `private, no-store`. Keys are normalised in the domain (`MMSI
165327752` and `165327752` match; `n-x-211` matches `NX211`). Nothing is persisted
and no network is used at request time.

## Frontend

The event inspector asks for notes only when the event carries an identifier: MMSI
for maritime positions, registration and type for aircraft. Matches render as a
"Reference notes" block with the key that matched, the name, description, detail and
links, followed by the identity caveat. No match or a failed lookup renders nothing.

## Follow-ups

- Facilities (ground stations, data centres) carry their own website and Wikipedia
  links inside the infrastructure snapshot rather than through this table.
- Curated notes for named naval vessels without an MMSI on Wikidata would need a
  hand-maintained table; none is included.

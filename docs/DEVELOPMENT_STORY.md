# Development Story

A concise, chronological record of how The All Seeing Eye is being built. Maintained by the development-story keeper; newest entries at the bottom.

## 2 September 2026: design

- Alex asked for a full design for an AI OSINT fusion app: a 3D globe as the primary view with a map mode (OS Maps, satellite, hybrid), free data sources across news, social, foreign-language media, aviation, disasters and more, LLM-written reports following the British probability yardstick and NATO intelligence doctrine with graded sources, two roles, a login flow with account requests and password reset, dark mode throughout, SOLID and secure by design, and the React Bits Evil Eye as branding.
- Four research passes verified the mapping stack (MapLibre GL JS 6 globe, OS Data Hub free tier, satellite and dark base maps, the Evil Eye component), about 120 free data sources across every category, and the doctrine (PHIA 2025 yardstick and confidence ratings, JDP 2-00 fourth edition, NATO AJP-2 and AJP-2.1, ICD 203, the NATO OSINT Handbook, the Berkeley Protocol).
- The proposal was written as eight documents plus seven ADRs under `docs/`, and published as a summary page. Key ideas: one unified Event model; a bounded in-memory live tier with evidence freezing as the only path to durable storage; deterministic grading before generation; a validator that enforces the yardstick, confidence ratings and citations; the intelligence cycle as the product's information architecture.

## 3 September 2026: approval and Phase 0 start

- Alex approved the plan and every recommendation with two amendments: the 3D globe is the default view for every session, and the logo is specifically the React Bits Evil Eye component. The ADRs moved to Accepted; the open questions record the recommended answers as decisions.
- Toolchain check on the Windows 11 host: git 2.51, Python 3.13, uv 0.11, Node 22, npm 11 and the Docker CLI present; pnpm installed at user level through npm because corepack could not write its shims without administrator rights; `just` and `pre-commit` absent (run through `uvx` or install with `uv tool`); the Docker daemon not running, so PostgreSQL via compose stays unverified until it is started.
- Repository initialised on `main` with the approved documents, the project `CLAUDE.md`, the Phase 0 auth API contract (`docs/api/AUTH_API.md`) and the master implementation plan as the first commit.
- Two implementation workers were launched in parallel on disjoint paths (backend plus root infrastructure; frontend). The first attempt was cut short by a usage limit before either wrote code; both were relaunched once the limit reset.

## 4 September 2026: Phase 0 built, reviewed and accepted

- The subagent workers kept stalling on long tasks (the stream watchdog fired after ten minutes without progress, usually right after a batch of parallel file reads). The backend and infrastructure were therefore written directly in the main session; the frontend worker got most of the way (63 source files including the registry copy of the Evil Eye) before stalling, and its output was finished and integrated in the main session. Reviews only completed once the reviewer briefs demanded one tool call at a time.
- Backend: a layered FastAPI service (domain, application, adapters, API, infrastructure) with import-linter contracts, argon2id passwords, rotating refresh tokens with family reuse detection, CSRF double-submit, rate limits and lockout, admin-approved account requests with activation and reset links, an audit log, Alembic migration 0001, and a CLI. 87 tests at 98 percent coverage.
- Two findings during backend testing are worth remembering. None of the top 1,000 (and only ten of the top 10,000) common passwords reach the 12-character minimum, so a naive deny list never fires; the policy now also checks the password's core with digits and punctuation stripped. And SQLAlchemy's asyncio bridge runs ORM code in greenlets, which coverage.py silently misses without `concurrency = ["greenlet", "thread"]`, making a fully tested service look 89 percent covered.
- Frontend: Vite, React 19, TypeScript strict, Tailwind 4, React Router 7, Zustand and zod; the Evil Eye copied verbatim from the React Bits registry with two documented props added; auth and admin pages; and the MapLibre GL 6 globe as the root route. 86 tests at 96 percent coverage.
- Three globe problems surfaced only in a real browser. MapLibre's stylesheet forces `position: relative` on the map element, defeating absolute positioning, so the container needed an explicit height. The OpenFreeMap dark style paints land at 5 percent grey and water at 11 percent, invisible on a sphere, so paint overrides move it onto the app palette. And Vite's dependency pre-bundling relocated the MapLibre module so its module worker (resolved with `new URL(..., import.meta.url)`) fell through to the SPA index page: vector tiles silently never parsed while raster tiles worked. Excluding `maplibre-gl` from pre-bundling fixed it.
- The code-quality review found one must-fix (a reset link could reactivate a deactivated account) and the security review found two highs (all clients shared one rate-limit bucket and audit IP behind Caddy; no request body cap). All findings were fixed: deactivation now voids outstanding links, uvicorn trusts the proxy's forwarded headers on the compose network, bodies are capped at 64 KB with 413, tracebacks are logged, argon2 parameters are pinned, and CI actions are pinned to commit SHAs with semgrep and trivy added.
- Acceptance: the full flow (request, approve, activate, sign in, globe) was walked in the embedded browser, and the globe was confirmed in Chrome as well. Phase 0 is complete apart from the static brand assets.

## 5 September 2026: Phase 1 fusion core and the live globe

- Backend fusion core written in the main session: the unified `Event` model, a bounded in-memory store with per-category retention and a memory budget, an in-memory bus, the normaliser pipeline, a health registry with circuit breakers, a scheduler with timeouts, jitter and backoff, and a feed HTTP client that refuses private addresses, caps bodies and sends conditional requests. Five keyless connectors (USGS, GDACS, NASA EONET, NOAA SWPC, CISA KEV) feed `/api/events` and the server-sent event stream. 123 backend tests pass on SQLite and on PostgreSQL.
- Docker Desktop was started, so the compose stack was verified for the first time: migrations ran on PostgreSQL, the API container reported healthy, and Caddy served the SPA with its own policy while passing the API through with the strict one. Docker Hub pulls through the Desktop proxy timed out repeatedly; the standard postgis image never arrived and the alpine variant is used instead, and the web image build needed pnpm's retry settings copied in through `.npmrc`.
- Frontend live layer: `EventSource` cannot send a bearer header, so the stream client is a small fetch-based server-sent events reader that reconnects with backoff and asks the session for a fresh token when the server says goodbye or answers 401. The events store keeps a bounded mirror; deck.gl draws one scatterplot layer per category through a `MapboxOverlay` control on the MapLibre engine; a layer panel, a ticker and an inspector sit over the globe. The dev API showed six healthy sources and around 970 live events on the sphere within seconds of signing in.
- Small lessons from the test run. Editing files with Python's `write_text` on Windows silently turned every line ending into CRLF and produced whole-file diffs, so edits now write bytes. Accessible names concatenate inline spans without spaces, so a switch reading "Disasters" and "1" needs a text node between them to be found as "Disasters 1". Importing a fixture from another test file re-registers that file's tests, so shared fixtures live under `src/test/`. The deck.gl overlay is mocked in jsdom like the map itself; the layers are real deck.gl instances, which lets tests call their pick handlers.
- News and conflict feeds. Twenty-six candidate RSS and Atom URLs from the source catalogue were fetched politely; twenty-one answered with a feed (RSS 2.0, RSS 1.0 RDF and Atom, one with a byte-order mark, one 750 KB), and five answered 404 or 403 (Kyiv Independent, Focus Taiwan, NHK World, ISW, Kyodo) and were left out. One generic connector handles the three formats by local tag name, strips HTML from bodies with the standard-library parser, reads GeoRSS points where present and takes ISO country codes from the US State Department's category domains. The seeds are typed Python rows rather than the YAML file the roadmap imagined, which keeps them under mypy and avoids a YAML dependency.
- GDELT's GEO API answered 404 to every documented form of request and the DOC API answered 429 with a one-call-per-five-seconds limit, so geolocated news comes from the raw 2.0 export files instead: `lastupdate.txt` names the newest 15-minute zip (about 40 KB, 660 rows, 61 tab-separated columns), and the connector keeps the protest and conflict CAMEO root codes with coordinates, grades them C and sets credibility by GDELT's source count. GDELT country codes are FIPS, not ISO, so they are kept as attributes until country resolution lands.
- Country resolution without a GIS dependency. `scripts/build_countries.py` downloads Natural Earth's public-domain 1:110m admin-0 countries (about 800 KB), keeps ISO codes, names and geometry, rounds coordinates to three decimals and packages 177 countries, 287 polygons and 10,305 points as a 175 KB resource. Natural Earth marks France, Norway and Kosovo with ISO code -99, so the script falls back to the ADM0 code for them. The domain holds an even-odd ray-casting test, an adapter indexes polygons by bounding box, a pipeline stage fills `country_iso` on located events, and `/api/countries` publishes names, bounds and centroids. The centroid is the centre of the largest polygon's box so that France lands on France rather than in the Atlantic between it and French Guiana.
- The frontend gained a nation filter (a combobox over the country list: a full name or code selects, Enter completes a prefix) that scopes the layers, counts, ticker and a new country panel to one nation and flies the camera to its centroid at a zoom derived from its bounds. With news feeds live the ticker is mostly headlines, which is expected until stories are clustered in Phase 2.
- Military aircraft joined from adsb.lol's keyless v2 `mil` endpoint (76 aircraft in the sample, 35 with positions; airplanes.live answered 403 from this host). Each aircraft keeps one event id so its marker moves on every 60-second poll, and the ten-minute aviation retention drops aircraft that stop reporting.
- A dev-loop trap worth recording: after the API was "restarted" twice, it still served old code. Windows had let several uvicorn processes bind 127.0.0.1:8000 at once and handed connections to the oldest, a worker orphaned from an earlier session that no task list or process query could see. The fix was to run the API on 8001 and make the Vite proxy target configurable through `ASE_DEV_API_TARGET` in the git-ignored `frontend/.env.local`; the stale listener stays until the machine restarts. With the right process answering, the countries endpoint, GDELT (150 conflict events) and ADS-B (37 aircraft) all showed up on the globe, and the nation filter scoped the view to the United States with 391 live events.
- Base layers. Satellite is EOX's Sentinel-2 cloudless mosaic added as a raster source under the first line layer of the dark style, so boundaries stay on top; hybrid keeps the vector labels and satellite hides them. Ordnance Survey tiles go through `/api/tiles/os/{layer}/{z}/{x}/{y}.png`: the key lives only in `ASE_OS_MAPS_KEY`, the route requires a session, addresses are validated against the free plan's zoom range, tiles are cached in a byte-bounded LRU so the 600-per-minute allowance is not spent on re-draws, and `/api/capabilities` lets the browser hide the OS buttons when no key is set. MapLibre's `transformRequest` attaches the bearer token to tile requests, and only to our own origin, so third-party tile servers never see it. The Caddy content security policy now allows the EOX tile host.
- Terminator, lite mode and readout. The subsolar point comes from a low-precision solar position (declination and Greenwich sidereal time from days since J2000), the terminator is the curve where the sun sits on the horizon, and the night side is that curve closed over whichever pole is dark, drawn as a single translucent deck.gl polygon rebuilt on the half-minute clock tick. Lite mode zeroes the atmosphere blend, swaps animated flights for jumps, drops the terminator and holds the Evil Eye still; base layer, terminator and lite mode persist through zustand's storage middleware, while the view mode is deliberately left out so every session starts on the globe. The coordinate readout keeps the last cursor position after the pointer leaves the map, which is what makes it clickable to copy.
- The admin source page lists every feed with its organisation, category, grade, poll interval, health, last poll and last error, and its reset button clears the circuit breaker through the existing endpoint. Building it moved the clock hook and the relative time formatter out of the globe feature into the shared library, since features must not import each other.

## 5 September 2026: Phase 2 begins with the grading engine

- Credibility now comes from the doctrine's rules rather than from each connector's guess. The domain module clusters events into stories with stemmed title tokens (a crude stemmer so "enters", "entered" and "ending" meet), an inverted index to find candidate pairs, Jaccard similarity of 0.4 with at least three shared tokens inside a 48-hour window, and, for disasters, the same subtype within 150 km and 12 hours so a USGS quake and its GDACS alert become one story. Independence follows the registry's parent organisation, and near-identical text in another organisation is folded as syndication rather than counted as corroboration. Two or more independent corroborations confirm; one makes an item probably true; instruments and authoritative registries (USGS, GDACS, EONET, SWPC, CISA KEV) are probably true on their own; state-controlled outlets stay possibly true; other lone items are possibly true when something else in the same category sits in the same country or within 150 km this window, and otherwise cannot be judged. Every item carries a sentence explaining its grade.
- The first thresholds were too strict: three real headlines about the same event ("RSF forces enter El Fasher after weeks of siege", "Sudan: RSF fighters enter El Fasher as siege ends", "RSF enters El Fasher, ending the siege") shared too few identical tokens until stemming and a lower threshold were added. Headline clustering stays approximate, as the doctrine document already says; the contradiction rules that would produce the doubtful and improbable grades are not built yet.
- The scheduler regrades the categories each poll touches and republishes neighbours whose grade moved, so an item can climb from 6 to 1 as corroboration arrives. The store gained a `put` that replaces events regardless of content hash, because grades are not content.

## 5 September 2026: Phase 1 reviews

- The code-quality and security reviewers ran in parallel with one tool call at a time, which is now the only way they finish. Neither found a must-fix bug. The security review's highest finding was a DNS rebinding gap: the feed client resolved a host to check it, then let the HTTP library resolve it again to connect, so a hostile feed's DNS server could answer the check with a public address and the connection with a private one. The client now connects to the address it checked, sending the original name in the Host header and the TLS handshake, and resolves redirect targets against the original URL rather than the pinned one.
- Also fixed from the reviews: the GDELT connector trusted the zip's declared size, so the inflated bytes are now counted with a hard stop; HTML stripping and http(s)-only link validation moved into the normaliser so every connector gets them, and the security document no longer claims a sanitiser library that was never added; the live stream ends at the presented token's real expiry rather than a fresh fifteen minutes, and each user may hold four streams at once; the store enforces its memory budget at insertion and announces what it dropped at the next prune; attribute values are capped at 500 characters; the CISA link check no longer accepts `httpfoo://`; the browser stream client no longer opens a connection when it was stopped while fetching a token; the country list retries after a failed load; `Country` moved into the domain behind a `CountryDirectory` port so the API stops importing an adapter; and the RSS seeds split into helpers, official feeds and outlets. Bandit's four remaining low-severity notes (type-only XML imports, jitter from the standard random module) are marked as deliberate; `pip-audit` and `pnpm audit` report no known vulnerabilities.

## 5 September 2026: the LLM gateway

- Model access is a profile: any OpenAI-compatible endpoint (OpenAI, Ollama, LM Studio, vLLM) with a name, base URL, model, the pipeline roles it may play (direction, assessment, devil's advocate), token and temperature limits, and a key. Keys are encrypted with Fernet under `ASE_ENCRYPTION_KEY` (any 32-character string, hashed to the Fernet key), stored in migration 0002's `llm_profiles` table, and only ever leave the server as their last four characters; without the setting the API answers 409 and the admin page explains what to set. Local endpoints on private addresses are allowed on purpose, because a model on localhost is the normal self-hosted case, and the security document records that the trust boundary there is the admin role rather than the feed client's SSRF guard.
- The gateway posts chat completions with JSON-schema response formatting and returns the content plus token usage and latency; its errors quote the status code and a 200-character excerpt of the body, never the request or the key. The connection test asks for exactly `{"ok": true}` and reports whether the model answered, answered with something else, or could not be reached, and every attempt lands in the `llm_usage` log and the audit log. The admin Models page creates, edits (a blank key field keeps the stored key), tests and deletes profiles with a two-step confirmation. The `cryptography` package is the one new backend dependency.

## 5 September 2026: the report pipeline

- The doctrine became code before any prompt was written. A domain module holds the yardstick bands with their ranges, the forbidden ICD 203 phrases, the hedge words and the confidence phrases as longest-first matchers, so "highly unlikely" is never read as "unlikely" and "very likely" is caught before "likely". The report body is a set of frozen dataclasses with a lenient parser (unknown fields dropped, lengths bounded, enums checked) and a JSON schema handed to the model as its response format. The linter applies the rules the doctrine document lists: one term per judgement matching its probability field, no hedges in judgements, confidence present and never in the same sentence as a term, reporting that cites and carries no terms, unknown citations stripped with a warning, no URLs from outside the cited evidence, assumptions with judgements and alternatives with two or more, a confidence ceiling from the information base, and a change marker whenever a previous version exists.
- Templates are typed rows (INTSUM, INTREP, Country Brief, Ask the Eye) with their section guidance, evidence strategy and token budget. Evidence is selected from the live store by credibility, reliability, recency, severity and a per-source cap, items whose text looks like instructions are screened out and counted, and the survivors are frozen as evidence items with labels E1 onward. The quality-of-information check is computed, not asked for, and sets the ceiling the validator enforces.
- Generation composes the doctrine preamble, the template guidance, the scope, the quality check and the evidence blocks; parses and validates the model's JSON; retries once with the findings quoted back; and stores the result as ready, needs review or failed together with the findings, the frozen evidence, the quality statistics, the rendered Markdown, the model, tokens, latency and attempt count (migration 0003). Every attempt lands in the usage log and the audit log. Users may generate ten reports an hour; the reports API lists, reads, exports Markdown and lets owners or admins delete.
- Tests script the model with a fake gateway: a sound body passes first time, invalid JSON then a sound body takes two attempts, a doctrine breach twice ends in needs review with the yardstick finding attached, and a gateway that never answers ends in failed. Writing them exposed that the sample body cited an evidence label the small test store could not supply, which is exactly the case the citation rule exists for.
- The Reports pages replaced the rail's Phase 2 placeholder: a generate form (product, nation from the country list, window, and a question for Ask the Eye), a list with status badges, and a reader that puts the key judgements first with the yardstick term and confidence as chips, shows every evidence label beside the claim it supports, folds validator notes on ready reports and shows them prominently on reports that need review, and ends with the evidence annex, where only http(s) links become anchors. The Markdown export copies to the clipboard for now, because a bearer-authenticated download needs a fetch-and-save path that is still to come.

## 5 September 2026: report versions and the Markdown download

- Regenerating a report adds a version rather than a report. The scope is rebuilt from the stored record, the previous version's key judgements are quoted to the model, and the validator insists on a change marker, so a regenerated report has to say whether the picture moved. The record carries the latest version number and status; every version keeps its own frozen evidence, findings and Markdown, and the API reads any version by number. The generation loop moved into its own module when the use case reached the file limit.
- The reader gained a version strip (each number a link, the current one marked), a Regenerate button that reloads the latest version, and a Download button that fetches the Markdown through the authenticated client and hands it to the browser as a file through a short-lived object URL, with a file name slugged from the title. Copy to clipboard stays for people who want to paste.

## 5 September 2026: direction, devil's advocacy and archiving

- Ask the Eye now starts with a direction call. A profile playing the direction role turns the question into one PIR, SIRs, EEIs and headline-style search terms; the terms put matching evidence ahead of the rest, and the requirements are quoted to the assessment model with an instruction to answer by EEI. The direction is stored beside the version and rendered as a Direction section. The first cut also filtered evidence to the model's category guess; a test showed that dropping a relevant item, so categories are recorded but never used to filter.
- Devil's advocacy is a checkbox on the generate form and part of the stored scope, so regeneration repeats it. After the body validates, a profile playing the devil role is asked for the strongest honest case that the first key judgement is wrong, citing labels only. Unknown labels are stripped, a URL discards the view, and the advocate can lower that judgement's confidence one step but never raise it. Every call lands in the usage log under its own purpose, and both calls degrade to warnings when no profile plays the role or the call fails; the report itself still lands.
- Cited URLs are preserved after generation by a background task. The Wayback availability API is asked for a snapshot taken since publication; otherwise Save Page Now is asked for one, with a pause between requests and no retries, because the service rate-limits and refuses many domains. The snapshot address is written onto the frozen evidence, the Markdown is rendered again so the export carries it, and the reader shows an archive link beside each source link. `ASE_ARCHIVE_ENABLED=false` keeps cited URLs on the host.

## 5 September 2026: the product rethink

- With Phases 0 to 2 committed, Alex asked for a hard look at what the map can really show, what the analysis features really are, and which free feeds really answer. Rather than trust the catalogue, every candidate endpoint was fetched from the development host with the project's User-Agent, and the results went into `02_DATA_SOURCES.md` section O. The surprises: aviation is far richer without keys than assumed (adsb.lol answers military, interesting, LADD, PIA, emergency and 250-mile point queries, and OpenSky answers anonymous bounding boxes), the Smithsonian volcano feed does carry coordinates, MeteoAlarm survives only as per-country Atom feeds, NGA's anti-shipping path is gone, ISW's current control-of-terrain layer is not discoverable, the Bluesky public AppView refuses this host, and GDELT's DOC API rate-limits on the first call.
- The feature inventories in `04_FEATURES_AND_VIEWS.md` (sections 11 and 12) now say, feature by feature, what is built, what comes next with a verified feed, what waits on a key only Alex can obtain, and what is no longer promised. The master plan gained a Phase 3 checklist in three slices (disasters and conflicts first, then aviation, then maritime warnings, space and cyber) and a blockers list ordered by visible impact: a NASA FIRMS key for fires and a configured LLM endpoint matter more than anything else.

## 5 September 2026: tracker boards

- The trackers went live as boards computed from the live store on request, never stored: for every hazard (connector subtypes folded into nine hazards) and every curated conflict (a packaged list of 23 wars and tension areas with countries, a bounding box, belligerents and keywords), activity in the last day and week against the week before, red alerts, the worst and newest item, the countries touched, and a detail view with a fourteen-day timeline and the events themselves. Conflict areas gather everything inside the box plus everything filed under their countries, so a news item with no coordinates still counts as reporting. The Trackers rail entry replaced its Phase 3 placeholder with two boards and two detail pages, each able to scope the globe to its nation.
- Ten connectors followed for the disaster and humanitarian feeds verified that morning: NHC advisories for two basins (the `nhc:Cyclone` block gives centre, wind, pressure and movement), JTWC (the RSS lists the active systems and each warning text is fetched for its "NEAR 20.6N 141.6W" position and winds), the Smithsonian weekly volcano report, the two tsunami warning centres, EMSC earthquakes, NWS severe weather with polygon centroids, WHO Disease Outbreak News and IFRC GO emergencies. Each was written against a trimmed live capture kept as a fixture, and the RSS module now shares its small XML helpers instead of every connector growing a copy.
- Two tracker products followed. A Conflict Assessment is scoped by a curated conflict: evidence comes from its bounding box and its countries, the conflict's keywords rank matching items first, and the curated summary and belligerents reach the model as background it is told never to cite. A Disaster SITREP is scoped by hazard, so only that kind of disaster (plus humanitarian reporting) is selected. Each tracker detail page links to the generate form with the product and scope already chosen.
- The globe learnt three things the trackers needed. Aircraft, cyclones and volcanoes are drawn as icons (SVG masks tinted with the category colour, aircraft rotated to their track) instead of dots; below zoom 3 located events are binned into grid cells per category and drawn as sized circles with counts, and a click on one flies the camera in; and the layer panel gained a time window (1 h to 7 d, or everything retained) that every layer, count and the ticker obey. The engine now reports its zoom after every camera move so the page can decide when to cluster.

## 5 September 2026: aviation without keys

- The rethink's biggest surprise was put to work. The adsb.lol connector became a family sharing one parser: the military, LADD and PIA lists, an emergency-squawk connector that asks for 7500, 7700 and 7600 every minute and grades them severe, and an area connector that asks for every aircraft within 250 nautical miles of eight watched areas (Black Sea, eastern Mediterranean, Red Sea, Gulf, Baltic, Taiwan Strait, Korea, South China Sea). Every airframe keeps one event id whichever query saw it, so a military jet over the Black Sea is one marker that moves, not two, and an aircraft's military identity survives being seen by an area query. The integrity fields (`nac_p`, `nic`) and squawk now travel with each event for the interference map and the emergency board.
- Baselines are the one durable addition the architecture allowed for "normal levels": a background sampler writes, every five minutes, the hour's maximum of military aircraft per nation, aircraft per watched area and emergency squawks into a small table (migration 0005), and the aviation board compares now with the 30-day mean. The same sampler feeds the GNSS interference map, which follows the published GPSJam method over one-degree cells and a rolling day; the threshold for "poor accuracy" is recorded as an assumption in the domain module. An Aviation Activity Report template hands the board's figures to the model as background it may use but never cite.
- The aviation tracker reached the app: a board with military, interesting, LADD and PIA counts, every nation and watched area against its baseline in plain words (above, steady, below, no baseline yet), emergency squawks first, and a link to the activity report; on the globe a "GNSS interference" switch draws the amber and red cells and refreshes them every five minutes, and emergency aircraft turn the critical colour. The test fixtures module had grown past the file limit and was split by responsibility (events, reports, trackers) behind one re-exporting entry point.

## 5 September 2026: warnings, satellites and outages

- Six more connectors covered the keyless parts of the maritime, space and cyber modules. NAVAREA warnings arrive as free text, so a small parser lifts positions written as 39-16.00N 076-35.00W and classifies each warning from its wording (security, GNSS interference, military exercise, hazard, navigation). Space stations are propagated with SGP4 from CelesTrak elements that are cached for two hours because the site refuses earlier repeats; upcoming launches sit at their pads; the planetary K index is one refreshed event. Ransomware claims and internet outage alerts are country-level, which exposed a gap: nothing placed such events on the globe. The country stage now gives an event that has a nation but no coordinates the nation's centroid, marked as country-level confidence, and the same rule lifts the humanitarian records onto the map.
- Boards followed for the three modules, each computed from the live store when the page opens: maritime warnings tallied by NAVAREA and kind with the notable ones first; stations overhead with their altitude, the launch schedule and the K index; outage signals and ransomware claims by nation and group beside the week's exploited vulnerabilities. Two more templates (Maritime Activity Report, Cyber Summary) take their board as background. That closes Phase 3's acceptance for every module except social, which is Phase 5: a board, a globe layer and a product for conflicts, disasters, aviation, maritime, space and cyber.

## 5 September 2026: areas of interest and collection plans

- Direction moved from a single question to standing requirements. An area of interest is a bounding box or a set of nations; a collection plan names an area or nations, one to eight priority intelligence requirements, and under each up to twelve specific requirements with keywords and categories. The codes (PIR-1, SIR-1.2) are assigned by the domain, never typed. Plans and areas persist (migration 0006) and are owned: anyone signed in can read them, only the owner or an admin can change or delete them.
- Nothing about a plan is precomputed. Opening one queries the last week from the live store inside the area (or the plan's nations, or everything) and lists, per requirement, the items whose title or summary carry its keywords or fall in its categories, newest first.
- A report can be scoped by a plan. The plan's area and nations select the evidence, its keywords rank it, its description reaches the model as uncited background, and its requirements go to the assessment model as the direction, so the direction call is skipped. The first PIR is the question unless another is asked, the title carries the plan name and the scope records the plan so regeneration repeats it.
- The container had grown past the file limit with the direction factories and became a package: the core (settings, sessions, repositories, auth and admin wiring) and a feature mixin holding the report, tracker and direction factories. The mixin declares, for the type checker only, the attributes it borrows from the core, which is what let it be split without a circular import.
- The Direction rail entry replaced its Phase 4 placeholder: areas and plans on one page with compact forms (requirements are typed one per line as text, keywords and categories separated by bars), and a plan page with the evidence per requirement and a Generate assessment button that opens the report form already scoped.

## 5 September 2026: indicators and alerts

- Warning arrived as standing rules. An indicator watches nations or a box, categories, keywords and a severity floor, and fires when at least a threshold of matching items were published inside its window; a cooldown keeps it from firing every cycle while the situation persists. A background loop evaluates every enabled indicator once a minute against the live store, in its own sessions, and survives a bad cycle.
- An alert takes four routes. It persists (thirty days, then pruned), it is published on the in-process bus so the stream carries it to open pages as an `alert` message, it goes to a webhook when `ASE_ALERT_WEBHOOK_URL` is set (the feed client's public-host guard, one POST, no retry) and, when the indicator names a report template, a report is generated as the indicator's owner with the indicator's nation and window as its scope and the alert keeps the report id. Email waits for a transport that does not exist yet.
- The roadmap's acceptance for the phase held in a test: an indicator over synthetic conflict events fired in one evaluator cycle, the alert appeared on the bus and in the API, the notifier was called and a report was produced. The Warning rail entry shows the alerts with acknowledgement and report links above the indicators and a compact form, and the top bar carries an alert count refreshed every minute.

## 5 September 2026: scheduled products

- Standing orders arrived: a schedule names a product, optionally a nation or a collection plan, a UTC hour and a cadence (daily, weekdays or weekly on a chosen day). The next run is booked when the order is created or changed, and a runner in the app lifespan checks every minute for orders that have fallen due, produces each one as its owner (so ownership and the per-user report limit apply as if the owner had pressed Generate) and books the following run. The schedule keeps the last report or, when production failed, the error text, so a stale order is visible rather than silent.
- Products that need a conflict or a hazard cannot be scheduled yet, and Ask the Eye can only be scheduled through a plan, which supplies the question. The Reports page gained a Schedules section under the report list with the next run, the last outcome and a compact form.

## 5 September 2026: the ops room

- The wall-screen mode the feature list had promised since the proposal arrived as the last Phase 4 slice. Pressing `O` anywhere opens the globe with no rail and no top bar; the engine gained a `spin` that eases the camera fifteen degrees east every thirty seconds and chains the next step on `moveend`, so the planet turns without a timer fighting the map. Lite mode and the flat map keep it still. The ticker stays, the brand mark and an exit hint sit in a corner, and the unacknowledged alerts of the last day stack in the other, refreshed every minute. Escape restores the chrome, and the flag is never persisted, so a fresh session always opens the normal shell.

## 5 September 2026: social listening and languages

- Phase 5 opened with the feeds that answered without a key. Bluesky's public view was probed again and still refused this host, so it stays out. Mastodon hashtag timelines work on any instance that leaves its public preview on; a connector polls the operator's instances and hashtags from a packaged watch list, reduces each post to text, keeps the account, hashtags, boosts and replies as attributes, and files everything at doctrine's floor (reliability E, credibility 6) because a public post is nobody's report. Outlet YouTube channels and subreddit listings are plain Atom feeds, so they became seeds for the existing RSS connector; the channels keep their outlet's reliability, the subreddits sit at the floor. Reddit answered the first feed and rate-limited the next three when they were polled within seconds, which is exactly why every subreddit polls on its own quarter-hour.
- Language detection joined the pipeline as a stage that only touches events whose feed could not name a language, filling from the title (and the summary when the title is short). The design had named lingua; installed, its wheel brought 291 MB of models to a home machine that does not need them, so py3langid (4.5 MB, restricted to the twenty-four languages the feeds carry, with a confidence floor) took its place and the data sources document says so. Under test the container runs the stage with a null detector; the real detector has its own unit test on English, Ukrainian and French headlines.

## 5 September 2026: translation queued, and a handoff

- Foreign titles now have a path to English. A `Translator` port takes (text, language)
  pairs and answers with English or nothing; a queue over the live store takes up to twenty
  untranslated titles from the last day every half minute, translates them in one call,
  collapses repeated titles inside the batch, caches by language and title so a story seen
  through several feeds costs one translation, keeps an hourly call budget, and writes the
  result back with `put` rather than `upsert` because the content hash has not changed. The
  bus carries the updated events so open pages refresh, and the ticker, tracker rows and
  country panel now show the English title when there is one. The LLM adapter behind the
  new `translation` profile role and the container wiring are the next step.
- `docs/HANDOFF_PROMPT.md` was written so another agent can continue: the conventions, what
  exists phase by phase, the work in progress, what is left in order, the verified feed
  reality, the environment traps and the checks that must pass before a commit.

## 6 September 2026: translation connected to the live pipeline

- The translation role now has an adapter and lifespan wiring. It selects an enabled encrypted profile, sends one ordered structured-output request per batch and records usage through short database sessions. The admin form exposes the role. The queue counts failed calls against its hourly budget, bounds attempted-event state and checks the current title before merging a result, so an in-flight translation cannot resurrect a pruned event or overwrite a revised grade. Direct store replacement now obeys the memory budget too.
- The starting snapshot passed 229 backend tests (95.36 percent coverage) and 226 frontend tests (90.20 percent branches). Four pre-existing application imports of `structlog` broke the framework-free import contract; standard-library logging with structured `extra` fields restored it.

## 6 September 2026: social board and collection-plan watchlists

- The social board computes a rolling day's platform, instance, hashtag and located-post views from the live store. Its sampler writes only hourly keyword counts, including zeros, with a 32-term ceiling and 30-day retention. Bursts compare the most recent complete hour against earlier complete hours with a minimum sample count. Raw posts remain transient unless frozen into report evidence.
- Enabled collection plans now supply bounded literal Google News RSS queries. A fair rotating schedule, per-query interval, global request ceiling and bounded validator cache limit load on both the host and Google. Publisher URL resolution happens only for cited frozen evidence.
- The live signature-free batchexecute probe returned HTTP 200 with no decoded URL. Current opaque links require HTML-derived signature data in the researched decoder, which would violate the no-scraping decision. Legacy embedded URLs are decoded locally and checked for public hosts; modern Google links are retained, and the unresolved capability stays visible in the plan.

## 6 September 2026: administrator second factor and saved-report tools

- Administrators can enrol, confirm and disable an optional TOTP factor with password rechecks. Pending and active secrets are encrypted, pending enrolment expires, and a conditional database update consumes each time step once. Factor changes revoke refresh sessions. Password resets retain the factor; local password-confirmed CLI recovery handles a lost authenticator. Migration 0009 stores the factor separately from user records.
- Frozen report versions can be exported as PDF or DOCX and compared in the reader. Renderers run off the event loop with bounded concurrency, preserve citations and validation findings, and fetch no external images or document resources. A three-page PDF was visually checked. DOCX content and structure were checked, but this host has no office renderer for visual verification. Unsupported PDF font characters are represented explicitly as Unicode code points rather than silently lost.
- An optional embeddings profile enables semantic search over saved reports. Indexing is explicit and batched, and only the latest version of each of up to 1,000 reports is indexed. Stale versions and profile changes invalidate matches. Migration 0010 stores bounded JSON vectors so SQLite development and PostgreSQL deployments behave alike without an extension; ADR 0008 records the trade-off.

## 6 September 2026: performance, accessibility and recovery

- Expiry pruning no longer reconstructs the expired-ID set for every item. The repeatable benchmark measured median pruning time at 12,000 events falling from 3,005.59 ms to 6.20 ms on this host (synthetic workload, not an end-to-end rendering benchmark). The browser applies its 5,000-event cap after merging and clears selections that were evicted.
- The globe memoises layers by relevant data and clustering scale. MapLibre and deck.gl have separate vendor chunks; the globe application chunk is about 30 KB. Vendor bundles still exceed Vite's warning threshold and deck preloads on login. Removing recursive dependency grouping caused a real browser initialisation error, so safe execution ordering was retained. Reduced motion, hidden pages and synchronous camera completion no longer restart or recursively spin the map. Native time-window radios, nation-field focus and a skip link have keyboard regression tests.
- Backup tooling uses SQLite's online snapshot API, integrity checks and a strict manifest, and restores only into new destinations. Secrets require explicit opt-in. PostgreSQL support uses argument lists for dump/create/restore commands without printing credentials. The scripts do not install a schedule or retention policy; the operator procedure records those responsibilities.

## 6 September 2026: security review and integration

- The ASVS 5.0 level 2 review found token redemption races, report regeneration without an owner/admin check, and model transport/error handling gaps. Conditional token consumption and report permission checks received regressions. Model transports now stream within byte and time budgets, refuse redirects and compressed responses, and return status-only errors so upstream text cannot copy a key into usage or saved reports. Deep structured model output fails safely at each parser boundary. Chat requests share a concurrency ceiling of two.
- The shared feed client now explicitly requests identity encoding and rejects other encodings before reading their body, preventing HTTPX decompression before the byte cap. Redirect handling is forced through the public-host check even for an injected client. This may exclude an upstream that ignores identity negotiation; no HTML scraping or paid fallback was introduced.
- A forced PostgreSQL transaction interleaving showed that row-only family revocation could miss a concurrently inserted descendant. Migration 0011 adds durable family markers, checked by every refresh claim, with safe opportunistic retention cleanup. The regression confirms that even an unmarked late descendant cannot refresh. CI now runs this PostgreSQL-specific case explicitly.
- Final integration review found that advocacy-only citations needed URL resolution too, and that usage writes held SQLite's writer lock through outbound calls. Six regressions first reproduced the omissions and real `database is locked` errors, then passed after citation labels were combined and usage writes were deferred until all outbound stages finish. Report and usage persistence still commit or roll back together.
- Final verification passed 467 backend tests on SQLite (one PostgreSQL-only skip, 96.11 percent coverage) and 262 frontend tests (97.82 percent lines, 91.34 percent branches). A full 462-test PostgreSQL 17 run passed, followed by 36 report/gateway checks after the final production changes. Ruff, mypy, import contracts, ESLint, TypeScript and file-length checks passed. Locked dependency audits, Bandit, Gitleaks and Semgrep passed; Semgrep's 13 false positives were narrowly annotated with source-backed explanations and its error gate remains enabled.
- Real browser checks found fonts inlined against `font-src 'self'` and a missing production MapLibre module worker. The build now emits fonts and both worker modules as files. Chrome then rendered country tiles, markers and both projections, exercised social/report/admin states, downloaded valid PDF/DOCX files and checked keyboard focus and reduced motion. Caddy served both `.mjs` assets with HTTP 200 and JavaScript MIME types. These checks used an isolated in-memory app, not the operator's data.
- Real backup/restore CLI drills on fresh SQLite and PostgreSQL 17 preserved all 19 tables, both frozen report versions and decrypted credentials/TOTP with the preserved test key. Disposable databases, browser helpers and servers were removed afterwards. Container vulnerability checks and the final build follow-up are recorded in the security review.
- Final container scans found unused vulnerable pip vendors in the API base image and vulnerable Alpine/Go dependencies in the official Caddy image. Removing the unused API toolchain and rebuilding the same standard Caddy release with locked patched dependencies cleared the HIGH/CRITICAL gates. The Caddy build retained all 132 modules, configuration and low-port capability; local HTTPS, static assets and read-only API routing checks passed. Build/update instructions and exact scanned image identifiers are recorded for repeatable release checks.

## 6 September 2026: broader quality and team-workspace improvement

- The expanded goal is tracked in `MASTER_FIX_IMPROVEMENT_PLAN.md` on
  `codex/app-improvement`. A clean baseline audit found substantive analytical
  validation, corroboration, report-period and session-lifecycle gaps, plus the
  absence of manager roles and team authorisation. The existing layered monolith
  and bounded live store remain the foundation.
- Four report-period regressions now pass after reproducing narrow/wide selection
  errors and stale saved dates. The producer uses the resolved requested period;
  adding a version persists its current period and cutoff without rewriting the
  historical version or original creation date. The API regeneration check
  verifies that newly out-of-period evidence disappears while history stays frozen.
- Map, conservative grading, strict model-output validation, session hardening and
  team management are being integrated as separate responsibilities. Team roster
  management alone is not described as completed operational-record isolation.

## 6 September 2026: private workspaces and integrated analyst workflow

- User, manager and administrator roles now have explicit team membership and
  personal/team operational records. SQL filtering precedes limits, related records
  must share scope, and generation, search, exports and background jobs revalidate
  authority after slow work. Alert streams release idle database connections,
  filter each alert and notify clients when access changes. Open private pages
  also refresh authority on focus and every minute without blanking unchanged data.
- Account settings provide password changes with current-password and enrolled
  authenticator proof, atomic session/link revocation and safe failure auditing.
  Concurrent administrator, reset and credential transitions received SQLite and
  PostgreSQL regressions. Legacy scope migrations preserve records and frozen
  evidence, inventory conflicting links and produce readable audit entries.
- New model responses receive strict structural and citation validation. Topic
  similarity, copied reporting and translations do not become verified evidence.
  Frozen evidence retains language, precision, capture times, hashes and declared
  provenance; version dates describe the selected historical version. PDF, DOCX
  and Markdown carry the same review limits and provenance, and the browser reader
  links judgements to expandable evidence.
- The eight map choices remain alongside the root 3D globe and Evil Eye. Login,
  account, team, map and report views have browser-tested narrow layouts, compact
  controls and keyboard/focus behaviour. Keyed OS choices explain unavailability.
- Integrated frontend verification passed 351 tests across 74 files, with 98.04
  percent line and 91.95 percent branch coverage. ESLint, both TypeScript projects,
  Prettier and the production build passed. Large map/deck vendor chunks remain
  an explicit build warning. The full SQLite backend run passed 673 tests with one
  PostgreSQL-only skip and 96.10 percent branch-inclusive coverage. Ruff, mypy
  (278 source files), import contracts, file-length and pre-commit checks passed.
- The full PostgreSQL 17 run passed 675 tests. Both database migration round-trips
  preserved legacy data and readable audit entries. Three resource warnings from
  the SQLite coverage run were traced to unclosed test fixture connections;
  five affected tests then passed with resource warnings treated as errors.
- Bandit, Semgrep, source/staged Gitleaks and dependency audits passed in their
  checked scopes. Both containers built and passed the configured fixable
  HIGH/CRITICAL gate. The full inventory retains 54 unfixed API package findings
  (18 CVEs), including three CRITICAL matches, and zero web findings at those
  severities. `security/API_BASE_IMAGE_TRIAGE.md` records exact image IDs,
  component/reachability checks and supported-update/release follow-up. No
  package was forcibly removed, vulnerability ignored or operator risk accepted.
- Updated architecture, doctrine, feature inventory, API/operations guidance,
  ADRs and the master improvement/security records. The milestone is committed
  locally on `codex/app-improvement`. There is no Git remote or hosted CI result;
  no operator database migration or deployment was performed.

## 6 September 2026: automated research and report evidence weighting

- Alex redirected the product towards quick automated OSINT research and sourced
  reports for an operator, with teams providing basic sharing. The product
  direction now prioritises bounded on-demand collection, clear coverage,
  follow-up questions and evidence inspection. Cases, assignments and reviewer
  queues are outside that direction; broader collection is a subsequent milestone.
- Reviewed the public PHIA 2025 uncertainty/analytical standards and UK JDP 2-00
  fourth edition. The app retains the PHIA likelihood vocabulary and NATO-style
  source/item grading. The new `ase-evidence-v1` matrix is explicitly application
  policy, not calibrated truth or full doctrinal certification.
- The matrix fixes weak-padding and whole-pool confidence defects. Judgements use
  only their own cited support/opposition, strongest eligible contributions per
  declared organisation/copy group, and explicit limits on unknown provenance.
  Frozen engine assessments record explanations, confidence ceilings and final
  confidence after advocacy. Legacy reports are not rescored.
- Added typed assessment/methodology responses, a report summary, expandable
  evidence explanations and the 36-cell guide with all seven PHIA bands.
  Markdown/PDF/DOCX share the saved result; archive updates preserve it. Retrieval
  now favours diverse relevant reporting, shares parent-organisation caps and
  defers copied titles/content without discarding backfill or counterevidence.
- Independent scoring review found no remaining actionable defect. Focused core
  matrix tests measured 100 percent statement/branch coverage. PostgreSQL report
  assessment/export/production tests passed all 53 cases on a disposable 17.10
  instance; the container was removed and absence verified. Six representative
  PDF pages were visually checked; DOCX content checks passed, but an office
  renderer remains unavailable.
- Final full frontend coverage passed 359 tests with four workers: 98.04 percent
  lines, 91.70 percent branches. The initial default-concurrency run had three lazy-page
  timeouts while other checks competed for CPU; the recorded full pass used
  reduced concurrency without changing thresholds or repository runner defaults.
  Browser QA also exposed report-table clipping and citation focus/default-link
  behaviour. Both were fixed, with pointer/keyboard checks at 1440, 390 and 320
  pixels, no page overflow and preserved modified-click behaviour. The final full
  run includes the new regression and consistent synthetic fixtures.
- The full SQLite suite passed 719 tests with two PostgreSQL-only skips and 96.16
  percent combined statement/branch coverage in 422 seconds. Ruff, mypy over 284
  source files, both import contracts, Bandit and file-length checks passed.
  No source dependency, operator migration or deployment was added. Real model
  research quality remains unmeasured until a model is configured and a suitable
  evaluation set is exercised. All pre-commit gates passed, including Gitleaks;
  its prose false positive was resolved by clearer wording, without exclusions.
  The verified milestone is committed on `codex/report-evidence-scoring`, with no
  remote or push. Scoring, product direction, API, operations, ADR and scoped
  security-review documents were updated together.


## 6 September 2026: bounded automated research implementation in progress

- Started the full operator-research milestone on `codex/automated-research` from
  `99c1e16`. No new milestone commit or remote is present. The new
  [master automated-research plan](MASTER_AUTOMATED_RESEARCH_PLAN.md) retains the
  full acceptance checklist; earlier Phase 5/6 and scoring checks are historical.
- Added private question-led quick/detailed collection with bounded request/time
  budgets and explicit provider receipts. Supported components include undocumented
  Google News RSS editions, configured social feeds, SEC CIK/identity candidates,
  current DNS and .com/.net RDAP. Publisher/account claims remain unverified;
  edition selection does not establish translated coverage. Optional Companies
  House integration is still being implemented. No raw corpus or scraping added.
- Every registered source now has an explicit qualitative inherited-grade basis,
  scope and limitations. Frozen evidence retains that policy and scalar attribution,
  identity/locator/time hints. No accuracy percentages or historical review dates
  were invented. Source-rating/attribute tests reached 100 percent coverage across
  five new modules, with 51 focused and 65 broader regressions recorded separately.
- Added immutable research context with separate publication/capture/observation
  timestamps, unmerged identity candidates and declared source/copy cautions.
  Strict saved codecs preserve historical methods and unknown legacy metadata.
  Context/SQL/API tests passed 34 cases at 100 percent new-module line/branch
  coverage. Citation checks expose captured excerpts and review cues without
  claiming that lexical support proves entailment.
- Detailed research challenge processing now has bounded initial queries, one
  shared contrary-evidence collection budget and final per-judgement batch review.
  New selected evidence may trigger redrafting; a failed redraft retains the
  original body and evidence together. Missing review remains explicit. The
  challenge/context SQL and shared Markdown/PDF/DOCX paths passed focused scripted
  production tests, 22 cases in this slice. Follow-up and upload handoffs remain
  under combined integration; model agreement is not independent corroboration.
- Added `/research`, authenticated `/sources`, and saved receipt/citation/rating
  disclosures. The question UI passed 10 focused tests; the reader/source slice
  passed 41 tests with type/build checks. Browser fixtures at 1440, 390 and 320
  pixels covered request scope, errors/retry, disclosure, citation focus and search.
  Upload/follow-up/context/challenge controls are still integrating.
- Added migration `0015` for saved schedule questions/research options and `0016`
  for opt-in deterministic change summaries and schedule-origin alerts. These
  compare evidence/assessment records, not semantic importance or verified factual
  corrections. Final combined database/background/UI checks remain outstanding.
- Isolated document extraction preserves PDF physical pages, CSV row/line ranges,
  JSON pointers and DOCX paragraphs under byte/text/structure limits. Its shared
  worker passed 90 focused tests with 94.92 percent scoped coverage; an actual
  Windows Job rejected an allocation beyond its 512 MiB limit. POSIX isolation has
  unit-test evidence here, not an actual POSIX runtime check.
- Media adapters passed 56 tests with 97.39 percent scoped coverage, including
  synthetic English OCR and H.264/VP9 media checks; the event bridge passed 11 tests
  at 100 percent. A hash-verified FFmpeg 9.0.1 runtime is local under ignored
  `data/`. Distribution media tools were added to the API Dockerfile, but the
  changed image has not yet been built or scanned. Metadata, frame offsets and
  hashes are clues, not authenticity findings.
- The private upload endpoint passed 44 tests with 97.24 percent scoped coverage,
  including a real 76 KiB text upload through application and worker, disconnect
  cancellation and cleanup. Exact-user/security-version binding, 15-minute logical
  expiry and bounded storage apply. Physical expiry is lazy on store access;
  original bytes and sanitised preview bytes do not become event/receipt JSON.
- These slices passed their reported static and focused security checks. They do
  not establish final full-suite coverage, hosted CI, production readiness or
  real-model quality. The configured-model question and representative labelled
  evaluation remain open. No operator database/configuration or deployment was
  changed, and no commits or pushes were made for this unfinished milestone.

## 6 September 2026: automated research integration and remaining release gates

This entry supersedes the earlier same-day component-integration status, while
preserving those earlier test results as historical evidence.

- Integrated private upload previews and report handoff, authorised frozen-evidence
  follow-ups, challenge/context/citation disclosures, request progress and contextual
  research actions across existing views. Private document/media focus never sends
  extracted terms to public search. Saved reports retain selected evidence and
  bounded input metadata without the transient input ID or raw preview bytes.
- Added optional Companies House company profiles/name candidates and SSLMate
  certificate-transparency records. Both use operator-configured account keys and
  return unavailable without a request when unset. SSLMate uses the free authenticated
  allowance and first-page unexpired exact-hostname issuances, not full certificate
  history. Quick domain research uses DNS A; detailed adds AAAA, MX and NS.
- The authenticated source catalogue now includes every known research edition,
  social source, record provider and private import ID. All research profiles are
  F/unassessed with specific basis and limits. Unknown origins gain no declared
  independence from platform/edition names; collector endpoints share organisations.
  Eleven tests cover catalogue filtering, safe source output and actual saved-report
  freezing. Ruff, mypy and Bandit passed; package-targeted coverage encountered a
  NumPy import failure and is not reported as a pass.
- Added optional `X-Research-Run-ID` and exact-user/security-version progress polling.
  Generation stays synchronous, with a 600-second deadline and disconnect cancellation;
  progress expires after 30 minutes. Saving can win cancellation, so the client must
  inspect Reports before retrying an uncertain result. Private input access expires
  after 15 minutes with lazy physical cleanup and an 8 MiB upload limit.
- Scoped integration passed 145 PostgreSQL tests and actual migration verification.
  Twenty-three schedule regressions include rejection of document/media schedules,
  whose transient inputs cannot support unattended recurrence. Contextual actions
  passed 35 focused tests and browser checks. These counts overlap other suites.
- PDF international-text changes passed 15 tests at 98.77 percent scoped coverage.
  Bundled fonts support Greek/Cyrillic, with explicit fallback for unsupported
  Arabic/CJK; this is not full Arabic shaping or CJK rendering support.
- Full frontend coverage passed 453 tests across 90 files in 112.25 seconds:
  98.24 percent lines, 91.32 percent branches and 96.12 percent functions. Production
  build and type checks passed. A full ESLint failure in progress handling was fixed
  with a scoped pass; the final full lint rerun remains pending at this entry.
- The initial new API image built successfully. Actual Linux TXT/CSV/PDF/PNG,
  Tesseract, H.264 MP4 and VP9 WebM extraction checks passed. Worker/Tesseract
  512 MiB per-process address-space limits were observed; a 550 MiB allocation
  failed. Real stopped-worker cancellation and timeout reaped children and removed
  temporary files. This is a killable resource boundary, not a filesystem/network
  sandbox or aggregate process-tree memory cap. Native parser compromise could
  retain service-user access to the writable application-data mount.
- Initial-image Trivy reported zero fixable HIGH/CRITICAL findings, alongside 233
  unfixed package-level findings (7 CRITICAL, 226 HIGH), including duplicates.
  These are not 233 validated reachable application attack paths. Reachability has
  not been established; no clean-security or remediation claim is made.
- Long-running session revalidation passed 140 focused security tests. Four
  independent paused-upload/report logout/expiry checks returned 401 without
  retaining input or report. Full backend coverage, final image-snapshot rebuild
  and security checks, the configured real-model endpoint and quality evaluation
  remain pending. No deployment, operator-data change, new commit or remote push
  is claimed. The master plan retains the full acceptance checklist.
- Updated architecture, source contracts, product direction and the new
  [automated research API](api/AUTOMATED_RESEARCH_API.md) together. Official provider
  contracts and application budgets are distinct from successful live availability
  probes and research-quality measurements.

### Automated research integration verification, 6 September 2026

- Committed the integrated implementation as `de72899`. It includes question-led
  collection, explicit source policy, private uploads, frozen follow-ups, per-judgement
  challenges, source/context inspectors, monitored questions and basic scoped sharing.
- Full backend: 1,428 passed, two PostgreSQL-only skips, 96.47% coverage. A separate
  19-test PostgreSQL run passed both skipped cases and the final report/upload session
  guards. Earlier PostgreSQL research/migration verification passed 145 cases.
- Full frontend: 453 passed, 98.24% lines and 91.32% branches. Full ESLint, TypeScript,
  production builds and desktop/narrow browser checks passed. Fixtures were synthetic.
- Fixed a reproducible request cancellation hang: Starlette's polling cancel scope
  could swallow watcher cancellation. The watcher now awaits ASGI disconnect messages
  directly; targeted and whole-suite regressions passed.
- Ruff/formatting/mypy, architecture boundaries, file length, Bandit, dependency audits,
  Gitleaks and Semgrep passed. Two Semgrep annotation-import false positives use the
  existing narrow suppression convention; XML parsing still uses defusedxml. The
  bundled font licence is preserved byte-for-byte, including upstream whitespace.
- Final API/web images built and passed the fix-available HIGH/CRITICAL gate. All 397
  checked API source/package files match the image; actual Linux document/OCR/video,
  memory-limit, cancellation and timeout checks passed. Unfixed package advisories and
  same-user parser isolation limits remain recorded in the security review.
- No operator data was migrated and no deployment or remote push occurred. The only
  outstanding research-quality acceptance item needs the intended model endpoint/name
  and human review of the included eight synthetic evaluation cases.

### 6 September 2026: evaluate the automated research stages

- Added optional synthetic provider replay through the actual private collection
  service, preserving production request limits and the detailed all-judgement
  challenge/redraft workflow. Separate correction and unavailable-coverage cases
  do not expose reference rubrics or hidden challenge packets to the initial draft.
- Fixed an evaluation interruption defect: a first-case exception previously lost
  all recorded calls. A failing regression reproduced it; exception and cancellation
  tests now verify retained calls and explicit incomplete status without arbitrary
  exception text. Replay configuration is checked before model gateway creation.
- Recorded queries, receipts and frozen analysis support review. Cross-draft raw
  citation scores remain uncomputed because evidence labels can change; reviewers
  retain each prompt and response. Replay does not measure live search relevance.
- Verification: 62 combined evaluation/collection/production regressions passed;
  36 evaluation tests passed with 94.06% branch-inclusive harness coverage. Ruff,
  formatting, mypy (374 files), Bandit and file-length checks passed. Initial narrow
  coverage invocation inherited the whole-app coverage target; corrected command
  scoped measurement to the harness, without changing repository thresholds.
- Updated evaluation instructions and the active plan. No model endpoint was
  contacted, real credentials read, operator database changed or deployment made.
  Actual-model runs and representative human-reviewed labels remain outstanding.

### 6 September 2026: administrator AI connections

- Added the requested OpenAI `gpt-5.6-luna` Max preset, account model discovery,
  encrypted key entry and explicit configure/test/apply controls. Kept the
  existing Chat Completions adapter with reasoning-compatible completion budgets
  and propagated settings through all text stages and the evaluation harness.
- Added global defaults, team overrides, return-to-global and reuse of the same
  saved connection for multiple audiences. Running research captures its settings
  before outbound calls; saved report versions expose non-secret routing metadata.
  Shared feed translation remains global and embeddings keep their separate role.
- Protected active profiles from in-place changes. New text profiles remain drafts
  until tested and applied; existing migrated legacy selection is preserved until
  a global replacement is deliberately applied. Migration `0017` preserves old
  encrypted configuration and refuses a downgrade that would lose routing policy.
- Focused independent review reproduced and closed stale team confirmation and
  direct-enable workflow bypasses. Durable assignment revisions, ordered probe
  generations and original-session rechecks protect activation. Credential changes
  cannot silently reuse a key at a different endpoint; network errors are sanitised.
- SQLite/PostgreSQL migration checks and 42 PostgreSQL lifecycle/routing tests
  passed on disposable databases. Browser checks used synthetic responses at
  desktop and narrow widths. Broader suite results are recorded in the
  [connection plan](AI_CONNECTIONS_PLAN.md); scoped review limits are recorded in
  [the security review](security/AI_CONNECTIONS_REVIEW.md).
- Added operator instructions, ADR 0012 and a credential-free Luna evaluation
  profile. No real provider call, operator migration, deployment or remote push
  occurred. The administrator must enter the key through the app and test actual
  account access; representative research-quality evaluation remains outstanding.

### 6 September 2026: a dedicated administrator workspace

- Moved administration into a separate guarded shell with its own overview,
  navigation and mobile menu. Account requests, users, teams, AI connections,
  source controls, audit history and administrator security are grouped by purpose.
  The research interface exposes one administrator-only entry and retains its
  normal globe root. Administrators default to `/admin` after sign-in; explicit
  deep links are preserved.
- Added current-account verification before the shell mounts, on window focus
  and every 30 seconds while visible. Checks use the captured token without
  automatically refreshing it; stale responses cannot alter a newer login.
  Failed verification hides protected content and provides retry/research actions.
  This is bounded periodic observation, not immediate pushed revocation.
- A scoped access review passed 115 administrator endpoint denial checks. It
  reproduced an activation-link response reaching an administrator revoked during
  email delivery. Approval and reset-link routes now check the original session
  and current role before releasing results. All eight failing regressions now
  pass while preserving the already authorised account/token/audit transaction.
- The independent 48-test identity/administration selection and seven existing
  report-session regressions passed. Ruff, formatting, strict mypy, Bandit and
  architecture boundaries passed; OpenAPI export is unchanged. Browser checks
  exercised desktop/narrow layouts, keyboard navigation and administration-only
  loading with synthetic services. Final frontend results are recorded in the
  [access review](security/ADMIN_WORKSPACE_REVIEW.md).
- Updated architecture, security guidance, operator instructions and the active
  plan. No schema migration, new dependency, real email, operator data change,
  deployment or remote push was involved.

### 6 September 2026: native Amazon Bedrock connections

- Added an explicit Bedrock provider using native Converse and encrypted bearer
  API keys. The administrator editor accepts an AWS region and manual model or
  inference-profile ID, retaining saved-configuration testing and confirmed global
  or team assignments. No IAM role, automatic renewal or AWS catalogue is implied.
- Routed direction, assessment, challenge, review and translation through the
  captured provider. Adapted outbound structured schemas to AWS's subset while
  preserving application validators; scripted production proves invalid report
  repair still occurs. Native reasoning blocks are discarded, and incomplete or
  refused responses fail safely with bounded requests and sanitised errors.
- Final quality review found that native default reasoning could exhaust smaller
  legacy stage caps despite a larger tested budget. Bedrock stages now use the
  configured completion budget; 49 focused adapter and production regressions pass.
- Migration `0018` preserves legacy OpenAI hashes and assignments, expands encrypted
  credential and model identifier storage, and records provider in frozen routing.
  Review identified that rolling back new provider-bearing report metadata would
  make it unreadable to the prior strict reader; downgrade now refuses that case
  before DDL instead of rewriting historical reports.
- Added operator instructions and ADR 0013. The standalone evaluation CLI remains
  OpenAI-compatible. No live AWS call, operator migration, deployment or remote push
  occurred. Validation evidence is recorded in the connection plan and scoped review.

### 6 September 2026: midnight-blue account entrance

- Reworked public account pages around a large original Evil Eye, prominent app
  name and faint technical grid on deep navy. Added shared sign-in, signup and
  recovery navigation. Signup still requests administrator approval; login,
  authenticator codes, reset tokens and role-dependent destinations are unchanged.
- Kept the forms on a calm surface, with restrained entry and navigation motion,
  visible keyboard focus and reduced-motion support. The layout stacks into a
  compact branded header at narrow widths. No dependencies or external assets were
  added; the colour treatment is scoped to account pages.
- Browser resizing reproduced a stale 232-pixel canvas inside a 640-pixel eye
  container. Added container resize observation and verified matching 640-pixel
  canvas/container dimensions after mobile-to-desktop resizing. Vendor attribution
  records this small lifecycle adaptation; the original shader remains intact.
- Reviewed implementation and access implications sequentially because the requested
  review worker did not initialise. No authentication or backend policy changed.
  Browser checks used an isolated local frontend with no operator API connection.
- Removed cold lazy-module timing from login assertions and preloaded the globe
  module before layer-performance tests after observing unrelated loading-time
  failures. Authentication, routing and layer-behaviour assertions remain explicit.
- Final verification: 505 frontend tests across 96 files passed, with 98.46% line
  coverage and 91.86% branch coverage. Lint, TypeScript, formatting, production build
  and file-length checks passed. Desktop and 390/320-pixel browser checks verified
  navigation, visible focus, reduced motion and no horizontal overflow. Existing
  map/deck build size warnings remain. No deployment or remote push occurred.

### 6 September 2026: black account-page refinement

- Replaced the navy palette with near-black surfaces, neutral grey text and subtle
  white grid squares. Removed the Recovery tab while retaining forgotten-password
  access and its existing flow.
- Reduced the eye's internal scale to give the outer flames room, moved the edge
  feather beyond the artwork and removed negative mobile offsets. Desktop and
  320-pixel browser captures show the complete eye within its panel.
- All 39 focused account/brand tests passed; lint, types and build passed. No
  authentication, API or approval policy changed. Coverage was not remeasured for
  this small refinement; the previous full-suite results are recorded above.

### 6 September 2026: personal MFA and required administrator verification

- Replaced the public tagline with "AI-assisted OSINT collection and analysis."
  and removed "Research workspace". Removed the optional code disclosure from
  password login; the server now opens a separate verification or enrolment step.
- Added personal email/authenticator setup and removal, support for both methods,
  and MFA proof during password changes. Administrators must retain at least one
  factor and cannot receive a session until mandatory enrolment is complete.
- Added purpose-bound expiring challenges, email-code hashing, atomic consumption,
  attempt limits, session security-version invalidation and persistent administrator
  MFA assurance. Migration `0019` preserves existing authenticator state and makes
  old administrator sessions require fresh sign-in.
- Added verified TLS SMTP delivery and host-only recovery of both factors. No code
  is exposed through fallback links. Updated authentication and MFA operations docs.
- Independent security review found production traceback locals could disclose
  authentication secrets. A synthetic regression reproduced this, then passed with
  local-variable rendering disabled. Re-review found no further material issue.
- Browser verification used synthetic responses at desktop and 390-pixel widths,
  with no console errors. Backend operator data and real email services were untouched.
- Broad frontend checking exposed two timing-sensitive tests outside authentication:
  awaited the upload's parent busy effect and preloaded tracker route modules before
  rendering. Behaviour assertions remain intact; no product changes were required.

- Final code review identified personal verification errors incorrectly using session
  expiry responses and abandoned login responses replacing a later identity. Personal
  proof mistakes now return 422; MFA verification aborts on unmount and checks the
  current session before installation. Regression tests cover retained sessions,
  single-attempt accounting, corrected retries and abandoned completions.

- Final frontend verification: 517 tests across 97 files passed, with 98.38% line
  and 91.98% branch coverage. A further six-case login run verified the explicit
  request-abort assertion. TypeScript, ESLint and production build pass; existing
  map/deck chunk-size warnings remain. Ruff, mypy, Bandit, import boundaries,
  file-length and staged secret scanning pass.

- Full backend run: 1,684 passed, 14 environment-dependent cases skipped, with
  96.31% combined coverage. Two legacy test assumptions failed: a demoted account's
  password step was expected to fail instead of returning a challenge, and an LLM
  lifecycle test used the account snapshot from before mandatory enrolment changed
  its security version. Both were corrected without production changes and their
  affected suites passed separately (14 and 32 tests). The lifecycle tests now
  explicitly assert that their intended final session callback runs.

- Final combined backend rerun passed all 46 cases across access-session revocation,
  LLM lifecycle, personal MFA and exception hardening, with appended combined coverage
  of 96.42%. Focused code re-review confirmed both final findings are resolved.
  No production migration, live mail, deployment or remote push was performed.


## 6 September 2026: personal profiles and recovery

- Replaced the basic account screen with Profile, Security, Research defaults and
  Reports sections. Added private persisted preferences and editable display names.
- Connected research and report preferences to actual request defaults, frozen
  follow-ups, presentation prompts, report dates and preferred export buttons.
  Evidence grading and English judgement validation remain unchanged.
- Added current/other device management and ten single-use recovery codes with
  password/factor proof. Codes are hash-only and security-version scoped. Added
  local SVG authenticator QR rendering through the pinned qrcode package, plus
  tzdata for portable IANA timezone validation.
- Security review identified a revoked-family profile race and cross-account
  retries of pending browser actions. Fixed both with under-lock revalidation
  and synchronous identity-bound cancellation; added regressions.
- Code review exposed the existing Arabic/Chinese PDF font limitation through new
  output preferences. Shared notices recommend DOCX or Markdown before export.
- Synthetic desktop and 390-pixel browser checks verified account layout, name
  saving, security sections and the contextual PDF warning. Initial browser mock
  routing intercepted source modules; the harness was corrected before UI checks.
  No live account, SMTP/model call or operator database was used.
- Added profile operations and updated MFA and authentication API documentation.

- Final frontend run: 552 tests across 103 files passed, with 98.12% line and
  91.83% branch coverage. Three old exact-payload assertions were updated for the
  new report language/style fields; their 13 focused cases also passed. A final
  18-case MFA run covers the completed local QR and recovery sign-in UI.
- Production build, TypeScript, ESLint, formatting, OpenAPI consistency, Ruff,
  mypy, import boundaries, Bandit, file-length and staged Gitleaks checks pass.
  Frontend and Python dependency audits found no known vulnerabilities; the local
  application package is not indexed by PyPI. Existing map/deck chunk warnings remain.

- Full backend run: 1,741 passed and 14 environment-dependent cases skipped, with
  96.38% combined coverage. One report lifecycle assertion expected the old frozen
  scope without language/style. Updated those two expected fields, with no further
  production change, and reran the report suite with combined coverage retained.

- Final report-suite rerun passed all five cases; appended backend coverage is
  96.40%. All final file-length and diff checks pass. The milestone is committed
  locally on `main`; no remote is configured. Database migrations, real SMTP
  delivery and configured-model evaluation remain operator follow-up.


## 6 September 2026: regional research and map expansion planning

- Reviewed current source seeds, research limits, language settings and shared
  MapLibre/deck.gl architecture before planning the next expansion.
- Prepared a sequenced implementation backlog plus Russia/China/Iran source and
  geospatial specifications, with official source references and explicit access,
  licence, original-language and coverage limitations.
- The map audit identified country-centroid false precision, seam/polar clustering
  limits and the need to keep private report overlays out of public event SSE.
  The plan extends both existing projections through the same engine.
- Added dependency/ownership/acceptance tables, bounded retention and migration
  approach, real-model quality gates, source onboarding and real GPU checks.
- Documentation only. No application source, credentials, operator database,
  provider activation or deployment changed during this planning task.

- Independent plan review added immutable map-view revisions, initial snapshot/SSE
  reconciliation and existing live-layer truncation disclosure, and clarified the
  language/source/map dependency sequence. Local links, encoding, file-length and
  diff checks were performed; application tests are unchanged by these documents.

## 6 September 2026: bounded research expansion

Implemented regional source collection, editable collection previews, persistent
admin admission controls, shared private report mapping and source-aware records.
Added frozen claim inspection and evidence packages, personal library annotations,
and Chinese PDF fonts. Country-level findings no longer acquire invented points.
Source-release and export cancellation reviews produced race-condition fixes;
report deletion explicitly removes personal annotations on SQLite as well.

Synthetic browser QA rendered globe and flat projections. The 390-pixel layout
had no horizontal overflow, and closing the map removed its canvases. This is a
functional browser check, not completion of the plan's full GPU benchmark matrix.
The regional evaluation cases remain synthetic and await human/model evaluation.
Detailed feature limits are in RESEARCH_EXPANSION_OPERATIONS.md.

## 6 September 2026: automatic query translation foundation

Added a bounded single-call translation stage using the existing LLM gateway.
Strict parsing preserves requested language/term alignment and rejects changed,
missing or introduced numeric identifiers and quoted phrases. Original terms,
model identity and known token usage survive the result; provider errors are not
copied into findings. Cancellation propagates and failed output has no retry.
Twenty-two focused tests, Ruff, mypy and import-boundary checks passed.

This stage is not yet wired into report production. Remaining integration must
use the frozen team/global translation profile, preserve operator variants, freeze
transformation provenance and account for calls in report totals. Replanning must
share one collection deadline/request/item allowance across both passes; calling
collection twice with fresh limits would violate the plan. No model-quality or
end-to-end multilingual research completion is claimed by these unit tests.

## 6 September 2026: query translation integrated into research

Wired the translation stage into production collection through frozen model routing,
with in-memory usage accounting until final authorisation. Explicit operator variants
win, private document/media inputs are excluded, and empty source selections make
no translation call. Receipts now preserve original/translated terms, model, outcome
and task provenance; old plans retain compatible defaults. The preview explains the
additional run-time call and saved plans show unverified translation meaning.

Validation: 42 focused translation/collection/regression tests passed; a broader
55-test production/routing/progress group passed. After avoiding unnecessary plan
calls for ineligible queries, 22 production/provider tests passed. Frontend typecheck,
scoped lint and 16 focused metadata/planning tests passed. Real-model linguistic
quality, operator configuration and shared-budget replanning remain outstanding.

The collection layer now also accepts a run-local shared budget for serial passes.
It retains one deadline, consumes requests before outbound work and counts unique
retained IDs across passes. Thirty-five focused budget/collection/plan/challenge
tests passed; focused coverage was 96.59%. This is the budget foundation, not an
enabled automatic replan: service lifecycle and bounded receipt merging remain.

## 6 September 2026: one bounded empty-search revision

Connected the shared-budget collector to one model-proposed revision for empty
successful general research. The service holds one admission slot, freezes the
provider inventory and rejects scope changes. Nonempty or declined revisions use
remaining requests on unattempted original sources. Exact operator variants and
protected identifiers/quotes survive. Cancelled callbacks retain attempted-call
accounting without swallowing cancellation. Empty results are not evidence of absence.

Added two-pass frozen receipts, legacy-compatible parsing, API types, UI and document
export details. Source summaries are labelled outcomes, not HTTP request totals.
The service/budget suites passed 54 focused tests (98.39% scoped coverage); subsequent
model/lifecycle/plan tests passed 41 cases, and production regressions passed 31.
Frontend pass-receipt tests passed 15 cases. Full-plan acceptance and actual-model
semantic quality remain open; these tests do not establish field research accuracy.

Follow-up review reproduced a provenance bug: a revision changing only translated
terms was labelled as the initial translation. Added a failing regression and fixed
classification using the revised-pass marker. Review also identified repeated fixed
operator queries consuming the reserved pass; effective routed-task comparison and
per-source continuation passed review. The final focused backend group passed 54
tests, including a SQL/admin disable-during-replan acceptance case. Ruff and mypy
passed. The initial frontend run reported 15 timing/element-readiness failures;
the two-worker control narrowed these to two lazy-module readiness tests. Explicit
module-loading waits fixed both (16 focused tests passed). The subsequent full
run passed 662 tests but encountered two new map regression tests while their
fixes were still being edited. Those now pass in the focused map suite; a clean
full run against frozen frontend files is still required.

## 6 September 2026: saved-map foundations

Recorded the persistence/access and exact-revision acceptance contract in
`SAVED_MAP_VIEW_IMPLEMENTATION.md`. Shared camera/viewport support is in progress.
Reproduced and fixed canonical GeoJSON label loss on reload, and added a shared
one-million-operation topology ceiling across each import. Existing file/feature/
vertex limits alone allowed many individually small polygons to accumulate costly
intersection checks. The browser map parser passed 13 focused cases after these
fixes. Server canonical validation and Unicode label parity are being implemented.
The final browser parser group passed 14 cases including Unicode round trips;
the camera group passed 28 cases with typecheck and scoped lint. A new full
frontend coverage run passed all 683 tests with 90.21% branch coverage (95.84%
statements, 94.69% functions, 97.01% lines). Frontend lint and production build
passed; the existing map bundle-size advisory remains. Saved-view persistence,
API/UI integration and real WebGL acceptance remain open.

The server geometry parser passed 67 cases with 99.44% scoped coverage. Added
immutable map-state values, versioned serialisation, hashes bound to report version
and evidence, and charged revision storage sizes. State validation shares the
topology budget across all overlays and the AOI. The combined state/geometry run
passed 105 tests; four additional constructor-invariant tests brought the focused
state group to 42 passing cases. Repository storage and access integration are in
progress, with no operator database migration.

The saved-map foundation now has repository storage and migration `0024`, with
exact report-version anchoring, conditional revision appends, archive-inclusive
usage accounting and parent/view SQL visibility. A reproduced deletion regression
confirmed retained orphan map geometry; explicit parent-report cleanup fixed it.
List/count SQL excludes canonical state payloads. Ten repository/cleanup/migration
tests passed on disposable SQLite, and 111 geometry/state tests passed with 96.51%
scoped coverage. A preliminary coverage command accidentally retained the global
`--cov=ase` scope and failed at 42.05%; the corrected explicitly scoped run above
does not establish full backend coverage. Mypy (473 files), import boundaries,
Bandit and file-length checks passed. Application/API/UI and quota enforcement
remain unfinished; no operator migration or PostgreSQL acceptance is implied.
The parent report/library/team-scope regression group passed 26 cases after
cleanup wiring. Pre-commit Ruff/format, secret scan, file length, frontend lint
and typecheck all passed before committing this foundation.

## 6 September 2026: saved-map access and API integration

Added current-session and parent-scope checks, locked quota enforcement, immutable
revision conflicts, audit events and evidence/content integrity checks. Archive
link updates are deliberately excluded from the frozen evidence digest. Seventeen
service cases passed with 90.96% scoped coverage; 18 API cases and 16 body/header
cases passed. Map endpoints now support bounded overlay bodies above the ordinary
64 KiB request cap, while authentication precedes expensive geometry validation.
All map error responses carry no-store. Caddy configuration validation passed in
a disposable network-isolated container. Mypy and import boundaries passed.
PostgreSQL migration to head and all 45 API/service/repository/cleanup cases passed
on an owned disposable database, which was removed after testing. A separate
file-backed SQLite quota race test passed. Frontend saved-view controls remain in
progress; no operator database or deployed proxy was changed.
The concurrent last-slot quota check also passed against disposable PostgreSQL.
Frontend review identified lost first-overlay imports, stale authority after
rejected mutations, replayed selection on map reopening, date-filter semantics
and team write-control mismatches. The UI owner is fixing these before combined
frontend acceptance; no saved-map UI completion claim is made.

## 6 September 2026: saved-map controls and browser verification

Completed the save/revise/browse/archive controls and exact report/map revision
links. State includes the camera, projection, basemap, date/source filters,
selection, multiple overlays and retained AOI. Fixed the review findings above,
plus delayed file reads overwriting newer overlay edits and lower-bound-only date
filters displaying All dates. All 23 focused frontend cases passed, along with
TypeScript, scoped ESLint, Prettier, the production build and configured Bandit.
The build retains its existing bundle-size advisory. Full suites remain pending.

A synthetic Chrome harness used real Intel Iris Xe WebGL rendering. Globe and
flat maps rendered, saving/reloading restored the flat projection, manual camera
coordinates survived close/reopen, the 390-pixel layout had no horizontal overflow,
and simulated access invalidation removed private content and both canvases. API
responses were fixtures; no operator account/database was used. This is not full
seam/pole/performance acceptance. Temporary harness/cache files were preserved in
ignored data storage after automated review rejected their deletion.

Documented the next AOI research boundary: source-specific spatial support,
immutable origin references, destination scope, observation dates and exclusion
of unrelated global context. Existing country filters do not establish polygon
support. The new contract preserves the wider regional/map implementation scope.

The full backend run finished with 2,197 passes, 14 skips and six failures at
96.19% coverage. Updated stale PDF-warning assertions and a catalogue collection
fixture to the current planning/replan protocol. All 18 affected PDF/font/catalogue
cases then passed; Ruff checks passed. Production behaviour and coverage thresholds
were unchanged. Full frontend coverage was started after the backend run ended.
That frontend run passed all 698 tests in 124 files, with 95.79% statements,
90.11% branches, 94.52% functions and 96.99% lines. Production build and staged
secret scanning passed; the map export, AOI launch and broader acceptance backlog
remain open.

## 7 September 2026: area selection and spatial research foundations

Added explicit numeric, viewport-envelope and two-corner area selection to saved
report maps. Drafts need review before Apply or Save; existing arbitrary polygons
remain intact. Date-line and wide rectangles preserve their canonical extent.
Added canonical area/hash fields to research plans and receipts, explicit provider
spatial admission and legacy defaults. Forwarded the capability through both
provider wrappers and rendered its limitations in plan views.

Added exact map-origin resolution and final scope/integrity revalidation to report
generation. Strict area collection excludes unrelated global context. Review
identified repeated catalogue requests during detailed contrary collection; the
regression failed before the fix and now verifies explicit unavailable search
receipts while retaining model evidence review. Full API launch/provider integration
remains unfinished, as recorded in the AOI implementation contract.

Focused groups passed: 75 spatial/planner/collector, 34 challenge, 16 origin,
31 area/map UI and 11 plan UI/parser tests (overlapping groups). A synthetic browser
harness confirmed visible globe and flat-map area outlines, explicit draft review,
date-line split geometry on save, mobile bounds and private-layer invalidation.
The integrated backend group passed all 99 tests. An additional composed
application test passed for creation and regeneration after the map had a newer
revision, retaining the original area and admitting no global context. The full
frontend suite passed 715 tests in 126 files: 95.82% statements, 90.14% branches,
94.70% functions and 97.01% lines. Mypy, import boundaries, configured Bandit and
file-length checks passed. The native-provider and HTTP launch gates remain open.
The production build and all staged pre-commit hooks passed, including secret
scanning, full frontend lint and typecheck. The build retains its bundle-size
advisory. No operator database, source connection or deployment was changed.

### 7 September 2026: authorised exact-map research previews

The research-plan endpoint now resolves saved map/revision identifiers and an
explicit destination team through the existing origin checks. It returns exact
geometry and report-version provenance without external collection or model calls.
Preview does not grant disclosure consent; report generation still requires it.
Ordinary previews remain compatible, and the frontend parser retains map provenance.
The operator launch form and native spatial provider remain unfinished.

Read-only code/security review found no confirmed defects. Endpoint regressions
cover old revisions after a newer save, personal/team isolation, membership and
session revocation, tampered revisions and rejection of client-supplied geometry.
The 19 preview/planning tests passed with 100% coverage of the two new modules;
the earlier 31-test preview/planning/origin group also passed. Twelve frontend
plan tests, mypy (483 source files), import boundaries, scoped lint, typecheck,
file-length checks and production build passed. An initial targeted coverage
invocation accidentally retained the whole-backend source scope and failed that
coverage gate despite nine passing tests; the corrected scoped run retained the
90% threshold and passed. No new whole-backend coverage result is claimed.

The next evidence integration must preserve original satellite geometry and
separate acquisition, publication, retrieval and snapshot times. The AOI contract
now records the existing saved-map hash compatibility requirement and explicit
collection/selection/export acceptance. No live provider or operator database changed.

### 7 September 2026: original observation geometry retention

Added immutable bounded source geometry and observation metadata to events and
frozen evidence. Original coordinates survive snapshot, persistence and evidence
package export without annotation topology limits or invented centroids. Existing
evidence omits absent fields and retains a pinned legacy saved-map digest.
Package JSON now uses the canonical persistence serializer; its timestamp strings
therefore use ISO formatting consistently. Private-store estimates include geometry.

Security review found that export checked aggregate size after constructing large
JSON trees. Early geometry preflight and incremental per-member encoding now keep
output under the shared 8 MiB limit, including the manifest. A regression verifies
rejection before evidence trees are materialised. Follow-up review found no
remaining actionable issue in the fix.

The 80-test integration group passed, covering new metadata, exports, frozen
provenance, saved maps and map-origin checks. The 50-test geometry/store/export
group passed with 93.60% coverage across its four targeted modules; the existing
90% threshold remains unchanged. Ruff, format, mypy (485 files), both architecture
contracts, scoped Bandit and file-length checks passed. No new full-suite coverage
claim, live collection, migration or deployment is implied. Native area research
still needs honest nullable publication times, temporal selection and API/UI wiring.

### 7 September 2026: observation-time research selection

Added an explicit time basis shared by store queries, collection admission and
report ranking. Area observations use acquisition time, other reporting uses
publication time, and bounded intervals include the start and exclude the end.
Current-registry tags cannot bypass area date constraints. Point-only bbox filtering
no longer discards already-admitted area footprints. Existing ordinary research
keeps its publication basis.

Review found stale publication-only wording in receipts supplied to the drafting
model and exports. Receipts now freeze their actual time basis independently of
the optional plan, and API/parser/coverage UI retain it. Missing legacy fields
continue to mean publication. Evidence prompts and exports label structured
observation times; freeform source metadata and geometry arrays stay out of prompts.
Tests verify that instruction-like observation metadata is not interpolated there.

The 70-test integration group passed, covering date boundaries, mixed evidence,
storage, collection, selection, document exports and composed area generation.
Eighteen frontend receipt/plan tests passed; the 11 affected receipt tests passed
again after the generated-type fixture update. Mypy checked 487 files; both
architecture contracts and scoped Bandit passed. Production build passed with the
existing bundle-size advisory. No live source, operator database or deployment
changed. Nullable publication contracts and native provider/API/map launch remain
required before area collection can be exposed to operators.

### 7 September 2026: preserve unknown publication dates

Publication dates can remain unknown across events, frozen evidence, API responses,
research timelines and exports. Known-date serialisation is preserved. Undated
records cannot acquire publication recency from retrieval time, satisfy temporal
context tests or trigger automatic archival. Explicitly supplied private inputs
remain selectable with unknown dates; public date-window searches exclude them.
Frontend schema/sorting/formatting/map-day guards prevent epoch-date fabrication.

The first focused backend run passed 36 cases and failed one new test that called
the event DTO's generic validator instead of its existing `from_event` converter.
After correcting the test, its four-case file passed. The passing group includes
composed area creation/regeneration with null publication and retained acquisition
metadata. Twenty-four frontend format/store/map tests passed; typecheck, Ruff,
format, mypy (487 files), architecture contracts and file-length checks passed.
Read-only code/security review found no confirmed defect. The full backend suite
passed 2,307 tests with 14 skipped and 96.13% coverage. The production frontend
build passed with its existing bundle-size advisory. All 720 frontend tests in
127 files passed: 95.83% statements, 90.17% branches, 94.70% functions and 97.01%
lines. Full-source Bandit, staged Gitleaks and file-length checks also passed.
No source was enabled, operator database migrated or deployment performed.

### 7 September 2026: native spatial catalogue research adapter

Copernicus catalogue research now uses the existing fixed-host, bounded STAC
client through production research composition and persisted source admission.
Original footprint type/coordinates and acquisition metadata survive frozen
evidence; publication remains unknown and no event centroid is invented. Content
hashes include geometry and observation changes. Empty, unavailable and truncated
coverage remain distinct, and question terms are not sent to the spatial endpoint.

The catalogue and compatibility groups passed 66 tests across three invocations,
including actual-container SQL disable-before/during checks and shared-store
isolation. Mypy, architecture contracts and scoped Bandit passed. Live-source
acceptance, observation API/map presentation and the operator launch form remain
unfinished. No operator database or deployment changed.

### 7 September 2026: inspect frozen source observations

Report evidence DTOs and generated client types expose retained original geometry
and observation metadata. The evidence annex and selected-map-evidence panel show
acquisition/processing times, catalogue identity, cloud cover, attribution and
source limitations. Unknown publication remains separate, zero cloud cover is
not treated as missing, and legacy evidence has no invented observation fields.

Thirty-two focused backend tests and 24 frontend tests passed. Both type checks,
formatting and file-length checks passed. Read-only review found no confirmed
correctness, privacy or compatibility defect. Original-footprint rendering and
the operator map-to-research launch form remain unfinished.

### 7 September 2026: bounded frozen-footprint map display

Source geometry has a selectable layer in both projections, with source-first
shared preparation across optional overlays, the research area and temporary
catalogue footprints. Large source polygons retain their coordinates while using
the same topology checks; annotation limits remain unchanged. Unsupported shapes
have labelled omissions. Explicit selection fits complete components, including
seam envelopes, without creating event centroids. Access invalidation clears layers.

Review found and verified fixes for duplicate pre-budget parsing and unnecessary
revalidation on camera changes. The full frontend run passed 733 tests with 95.77%
statements and 90.05% branches. Follow-up callback/bounds tests passed, then display
compatibility passed 49 backend tests and 26 focused frontend tests. The v1 hash
contract remains unchanged; new maps use v2, and old maps require an explicit
operator upgrade before source footprints appear. Real GPU acceptance, saved
acquisition-time filtering and the operator launch workflow remain unfinished.


### Explicit saved timeline basis, 7 September 2026

Map state now records publication or acquisition-where-recorded time filtering.
Legacy publication defaults remain omitted from canonical persistence, preserving
old revision hashes. New unsaved report maps inherit the frozen research receipt's
time basis; restored saved maps retain their own basis. Timeline options, range
filters and evidence-list dates use the same choice, without retrieval fallback.
The existing inclusive map cutoffs remain unchanged.

A loader regression exposed independent overlay/AOI parsing before the shared
bounded renderer. That duplicate parsing is removed. An unsupported retained
overlay no longer prevents the anchored report from opening; the renderer owns
bounded preparation and omission reporting. Exact report/version access checks
remain unchanged.

Focused verification: 57 backend state/compatibility cases and 27 frontend timeline,
saved-view and anchored-link cases passed. The loader regression failed before the
fix and passed afterwards. Type checks and scoped lint passed before the loader
follow-up; final build/check results are recorded separately. Read-only review found
no time-basis blocker. This remains uncommitted work pending broader checks and
save/restore integration acceptance. The map-to-research launch remains unfinished.

The subsequent full frontend run passed all 740 tests in 132 files, including
saving an explicitly changed time basis: 95.75% statements, 90.12% branches,
94.62% functions and 96.96% lines. The production build, final scoped loader lint
and file-length checks passed. The existing bundle-size advisory remains.
The historical launch must add an explicit collection interval: the current
create-report contract only supports a rolling window. Collection, selection,
report periods and regeneration must agree without changing actual creation time.

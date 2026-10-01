# Source and export delivery: KAN-130, KAN-131, KAN-132, KAN-133, KAN-134, KAN-139, KAN-140

Branch: `codex/KAN-130-sources-exports`, originally based on `69696286` and integrated with final forecast prerequisite `13b140e0` by normal merges. [Draft PR #95](https://github.com/ShabalalaWATP/AllSeeingEye/pull/95) is stacked on forecast PR #94. The final prerequisite includes the SSE shutdown repair, corrected historical migration tests/guard, repaired CI parent and patched brace-expansion lockfile entries.
KAN-131 is integrated from the independently implemented publisher-roster branch and retains its genuine 24-hour measurement acceptance.

## Delivered behaviour

- **KAN-130:** native UN consolidated XML and EU FSF 1.1 XML imports use the existing atomic, immutable snapshot command. XML input and normalised output are each capped at 32 MiB, with at most 100,000 named records. DTDs, entities and external references are forbidden. Separate authorities retain source digest, list version, publication date and declared reuse terms. Missing configuration produces an authority-specific unavailable receipt. Names and aliases are candidate matches, not identity verification or a clearance verdict.
- **KAN-131:** fifteen verified native publisher feeds preserve publisher ownership, language and reviewed regional routing. They retain headline metadata, carry translation-on-demand flags and consume no automatic translation calls or cache hits. The combined inventory contains 154 executable research providers, below the existing 160-provider cap. The [roster record](../NATIVE_PUBLISHER_ROSTER.md) preserves source-specific decisions, live probe evidence and the reproducible 24-hour measurement command.
- **KAN-132:** an authenticated, rate-limited GLEIF name lookup performs one request and returns at most ten candidates. The editor discloses transmission of the typed name and requires separate confirmation of a candidate. It does not fetch while typing or automatically select a result. Existing exact-LEI research continues unchanged.
- **KAN-133:** daily, in-process EPSS and NVD enrichment is independent of the CISA known-exploited fact. FIRST supplies probability, percentile and score date. NVD supplies CVSS version, base score, vector, scoring source and NVD record modification date when present. The UI sorts by EPSS with missing values last and labels both scores separately. Missing or failed enrichment is absent, never a synthetic zero.
- **KAN-134:** three research-only HAPI v2 providers return up to twenty dated rows each for one selected country: IDPs, food security and operational presence. Each retains quantities, units, administrative identifiers, reference periods and the underlying HDX resource UUID in frozen evidence. No conflict-event endpoint is queried. HDX is labelled a distributor, not independent corroboration. Empty, unavailable, failed and timed-out attempts are distinct.
- **KAN-139:** an offline STIX 2.1 writer uses one exact saved report version. It emits a report, frozen evidence notes, explicitly present CVE identifiers, canonical MITRE group references and advisory references. It emits no indicators or numerical confidence. Repeated exports with the same marking are byte-identical. The UI requires a TLP:GREEN, TLP:AMBER or TLP:RED selection. The API performs both the session fence and the established exact-version release check. The existing STIX 2.1 built-in TLP markings are used, not a custom TLP extension.
- **KAN-140:** GeoJSON/KML export uses the already loaded, filtered client events with an optional research-area restriction. It caps output at 5,000 eligible located events, preserves approximate-location labels and reports excluded source IDs. It stores nothing on the server. Eligibility is an explicit, reviewed source-ID mapping for USGS earthquakes and four NASA FIRMS VIIRS sources; unreviewed sources are excluded. No prose licence substring is interpreted as permission.

## Operator configuration and provenance

No source credentials, downloaded sanctions lists, production databases or production settings were used.

For UN/EU, obtain the source file directly from the authority after reviewing its current terms. Run, from `backend`:

```text
uv run ase import-designations source.xml --cache-dir snapshots --authority un_sc --version YOUR-VERSION --published-at PUBLISHER-UTC-TIMESTAMP --licence "ACTUAL APPLICABLE TERMS"
```

Use `--authority eu_fsf` for EU FSF 1.1 XML. Set `ASE_UN_SC_SNAPSHOT_PATH` or `ASE_EU_FSF_SNAPSHOT_PATH` to the resulting JSON file. Version names cannot overwrite prior snapshots. Import validates structure and bounds, not file authenticity. Query execution never downloads a sanctions list. Both integrations remain unavailable until explicitly configured.

The [UN list page](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list) provides the official authority entry point. UN material must not be assumed to have an open-data licence; the operator must review the applicable [UN terms](https://www.un.org/en/about-us/terms-of-use) for the selected file and intended use. The current file-specific reuse decision remains an operator gate; no source file has been enabled by this change.

The [European Commission sanctions resources](https://finance.ec.europa.eu/eu-and-world/sanctions-restrictive-measures/overview-sanctions-and-related-resources_en) and [official data catalogue](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions) identify FSF/XML 1.1. The [FSF user manual](https://circabc.europa.eu/d/a/workspace/SpacesStore/9cf02a9e-7604-4178-a21d-d0b6bdcb4114/MA_FSF_EN.pdf) documents crawler URLs containing a logged-in user's token, which visitors cannot obtain. This implementation neither generates nor stores such a URL. Check current registration/access and file-specific conditions before import. The [Commission legal notice](https://commission.europa.eu/legal-notice_en) has exceptions to its default reuse policy, so it is not blanket permission for every record or purpose.

For HAPI, generate an application identifier through the [official HAPI API](https://hapi.humdata.org/docs) using the operator's own application name and email, then configure `ASE_HAPI_APP_IDENTIFIER`. The identifier encodes contact information and is treated as a secret. It is sent only in `X-HDX-HAPI-APP-IDENTIFIER`, bound to the exact HTTPS HAPI origin; it is never placed in the URL or frozen evidence. HAPI dataset-specific terms and revision/methodology limitations remain attached through the resource reference. No operator identifier was provided here, so a live data-row response still needs an operator probe.

## Public probe record, 2026-09-30 UTC

These are actual bounded public requests, separate from synthetic tests. No active scan, credential or registration was used.

| Provider | Request and observed outcome | Evidence limits |
| --- | --- | --- |
| HDX HAPI | Guarded GET `https://hapi.humdata.org/openapi.json`: successful JSON, 280,618 bytes, SHA-256 `605a139f815184eca37ca461c3048f4bc12443e216ba740c91a27458c9c7fb7a`. Schema declares `/api/v2/affected-people/idps`, `/api/v2/food-security-nutrition-poverty/food-security` and `/api/v2/coordination-context/operational-presence`, `data` arrays and alternative identifier header. | This is a live public schema probe, not a live data-row probe. Authenticated shape acceptance is outstanding. |
| FIRST EPSS | Guarded GET `https://api.first.org/data/v1/epss?cve=CVE-2021-44228&limit=1`: one row, EPSS `0.999990000`, percentile `1`, score date `2026-09-29`. | Availability and shape at probe time, not continuous uptime or prediction accuracy. |
| NVD | Guarded GET `https://services.nvd.nist.gov/rest/json/cves/2.0?hasKev&kevStartDate=2026-09-01T00:00:00.000&kevEndDate=2026-09-30T00:00:00.000&resultsPerPage=1`: successful `vulnerabilities` response, `cisaExploitAdd`, `lastModified`, `metrics.cvssMetricV31` and `metrics.ssvcV203` observed. | Proves the public bounded CVSS route works. Earlier HTML policy requests failed; a later rendered-browser review directly verified the published terms and public rate limit. The [dated review](../source-audit/KAN-133-nvd-terms-review.md) records the evidence and verified application notice. |

The [FIRST FAQ](https://www.first.org/epss/faq) and [data/API documentation](https://www.first.org/epss/data) describe freely available EPSS scores and attribution. The adapter uses at most ten batches of one hundred CVEs daily, within the API's 2,000-character CVE-filter bound. It uses one NVD `hasKev` request daily over the retained thirty-day KEV window, capped at one thousand returned records, with no pagination. Enrichment has a ten-second total deadline, including its lock wait, shortened when the CISA catalogue has used most of the normal sixty-second scheduler allowance. Internal expiry returns CISA records with any completed partial scores; outer cancellation still propagates. Both counters and failures are logged without private input. Failure stops that provider until the next daily allowance; the other provider can still succeed. Budgets reset on process restart, as do the in-memory score cache and retained feed state. The [verified public limit](../source-audit/KAN-133-nvd-terms-review.md) is five requests per rolling thirty seconds without a key. This one-request design fits that normal cadence; callers sharing an egress address must coordinate their aggregate usage. The Cyber vulnerability catalogue now displays the exact NVD non-endorsement notice above the data, including empty and unavailable-score states.

GLEIF's [API overview](https://www.gleif.org/en/lei-data/gleif-api/) and [API demonstration](https://api.gleif.org/demo) describe legal-name and legal-address-country filters. GLEIF candidates are fixture-tested here; no live company name was disclosed during development.

The map eligibility review uses [USGS data licensing](https://www.usgs.gov/data-management/data-licensing), [USGS acknowledgement guidance](https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs) and [NASA Earthdata use policy](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy). Export retains source links and attribution and does not imply endorsement. Expanding eligibility requires a new source-specific review.

## Verification and integration

- Focused backend suite: 163 passing tests covering imports, candidates, source admission/catalogue, enrichment, credential isolation, STIX schemas and release checks. Additional malformed-NVD/STIX bound checks: 11 passing tests in the two focused files.
- KEV deadline follow-up: all 16 tests in `test_kev_scores.py` and `test_cyber_kev_collection.py` pass. They cover stalled scoring, completed partial scores, exhausted catalogue allowance, daily request reservation and outer cancellation. Both changed source modules pass mypy and Ruff.
- Integrated KAN-131 verification: 221 tests pass across the native roster/audit, packaged catalogues, regional collection, allocation, source capabilities, RSS parsing and translation. Mypy passes for all ten integrated source modules; all source Ruff checks and three import-layer contracts pass. The resolved allocation profile file remains below 350 lines, and a composition assertion verifies all 154 providers fit the unchanged cap.
- Frontend: 12 tests passing across GLEIF confirmation, existing registry routing, KEV sorting/partial availability, STIX marking selection, existing Markdown export and live-map serialisation.
- Backend Ruff source checks, full mypy (1,389 source files) and all three import-layer contracts pass. Generated OpenAPI and TypeScript bindings are updated. Full coverage was not measured in this concurrent worktree.
- OASIS STIX schemas are vendored unchanged at commit `c4f8d589acf2bdb3783655c89e0ffb6e150006ae`, with original licence, provenance and only the recursive schema closure needed by this writer. Dev-only `jsonschema` validates offline; no production dependency was added.
- STIX limits: at most 1,000 frozen evidence records, 3,000 derived evidence objects and 8 MiB output. It rejects an oversized export rather than silently truncating it. All actor objects are reference identities, not incident attribution.
- Final prerequisite integration: 416 combined backend tests pass across source imports, roster/catalogue composition, translation, credentials, report authorisation, cooperative board reads, source admission, forecast lifecycle/counts/scope, feedback, startup imports, session fences and scheduler reliability. Full mypy passes for 1,448 source files; full backend Ruff, source formatting, all three import-layer contracts and the file-length hard gate pass. Frozen backend and frontend dependency installation succeeds, and both API artefacts were regenerated using `ase export-openapi` and `pnpm gen:api`.
- Combined frontend integration: all 22 tests in nine source/export and forecast component files pass with at most two workers. Type checking passes for both application and Node configurations, and full frontend lint passes. Coverage was not measured for this integration run.
- Independent review found that KML accepted XML-invalid Unicode. A regression first reproduced the parser error for U+FFFE/U+FFFF and lone surrogates. XML 1.0 character-range filtering fixes it while preserving valid supplementary-plane text. All five map export tests pass after the fix.
- Review-requested LEI release regressions pass for source deactivation, committed session revocation and token expiry while the external lookup awaits. In all three cases, neither the returned candidate name nor its LEI leaves the API. All five LEI API tests pass; no production change was needed for this boundary.
- Final repaired-parent check: all 20 tests in the LEI API, stream shutdown, stream connection-pool, stream revocation and session-fence files pass against `6d9a16fa` plus this source batch. The complete feature diff passes whitespace validation, including the authored schema provenance note normalised to LF. Independent source/export review has no unresolved confirmed findings.
- The subsequent prerequisite delta to `13b140e0` contains the lockfile repair, evidence documentation and a reviewed historical PostgreSQL test-helper consolidation, with no production/schema/API changes. A local frozen frontend install succeeds and `pnpm audit --audit-level high` reports no known vulnerabilities. Backend suites were not repeated for this dependency/test-documentation delta.
- KAN-44 overlap resolved: `cli_designations.py` imports dataset adapters lazily. The three source settings now enter through `container/feed_services.py`; `Container.__init__` is identical to the forecast prerequisite. Independent narrow review confirmed matching parameter types and preserved source-admission wiring. Source/allocation metadata was split to keep edited handwritten files below the normal size target. The existing HTTP adapter remains 354 lines because the scoped HAPI credential was added to its shared-header rejection list; the file-length hard gate accepts this narrow change.
- The initial frontend checks used Node 22.20.0, below the repository minimum. The current integration checks below use supported Node 24.19.0.

## Current main composition, 1 October 2026

The checked forecast prerequisite `61f08c47` was normally merged at `3345b3ff`.
The reviewed STIX and frontend compatibility candidates were applied as `78250203`
and `ae9ab728`. Main's extracted map composition, team-copy reader controls,
reviewed-source snapshot argument, report progress, persistent errors and focus
behaviour are retained. The live export now receives `quality.filtered` through
`GlobePageControls`, alongside the existing lazy planning panels. The merged
dependency files retain `pyjwt>=2.15.0` (resolved to 2.15.1) and dev-only `jsonschema`.
This batch adds no migration.

Main's team-copy contract deliberately retains stored Markdown verbatim. Its
canonical generated header can therefore still contain the personal original's
report identity. The new STIX endpoint now rebinds only that anchored, generated
UUID/version header to the authorised copy. Frozen narrative, explicit citations,
later inline identities, legacy Markdown and stored bytes are unchanged. This is
not a claim that existing raw-Markdown responses or evidence packages remove
personal source identities; that historical retention is outside this STIX change.
The original input/output bounds and exact-version release fence remain in force.

Verification on the composed branch:

- 50 backend report/export tests pass, including the actual team-copy STIX API,
  hidden personal provenance, current copy identity, membership removal during
  rendering, document release, reviewed-source projection and team-copy races.
- 183 further backend tests pass for LEI release races, GLEIF candidates, XML
  imports, HAPI credential isolation, partial KEV enrichment, publisher metadata,
  catalogue composition and the unchanged 154-provider inventory limit.
- 24 frontend tests in eleven files pass with two workers. The actual globe page
  exports the current location-quality selection while retaining the other loaded
  events in its local mirror. STIX marking, progress after dismissal, prevention
  of duplicate activation, focus preservation, failure/retry, reviewed-source
  query parameters, GLEIF lifecycle and KEV presentation are covered.
- Frozen private backend/frontend installs succeed. The actual `ase export-openapi`
  command and `pnpm gen:api` reproduce the merged contract artefacts unchanged.
  Full mypy passes for 1,525 source files; both TypeScript configurations pass.
  Full backend Ruff and formatting pass (2,680 files), all three import contracts
  pass, and the file-length hard gate passes with the recorded baseline warnings.
- Full frontend ESLint passes. Full Prettier checking reports twelve inherited
  failures, each verified byte-identical to the checked prerequisite. No unrelated
  formatting or threshold changes were made; the edited source/test files pass.
- Focused Bandit checks pass for STIX, LEI, XML and HAPI boundaries. Gitleaks scans
  the non-merge source commits above the checked prerequisite and finds
  no leaks. The feature diff passes whitespace validation.

These checks use SQLite and provider fixtures, not production databases or new
live-provider acceptance. Full coverage and PostgreSQL testing are not claimed
for this integration run. Independent review of the new identity-header boundary
and publication remain with the orchestrator.

No production release or merge into `main` is included. The orchestrator authorised draft publication after the repaired prerequisite and final focused checks. KAN-130 source-specific licence/access enabling, KAN-131 the genuine 24-hour measurement and KAN-134 live data-row validation remain explicit outstanding external acceptance, not fixture-test successes. KAN-133's published NVD terms and rate policy are verified, and its application non-endorsement notice is implemented and checked in the dated review.

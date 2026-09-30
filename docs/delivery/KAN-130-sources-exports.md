# Source and export delivery: KAN-130, KAN-132, KAN-133, KAN-134, KAN-139, KAN-140

Branch: `codex/KAN-130-sources-exports`, based on `69696286`.
KAN-131 is being delivered separately and retains its genuine 24-hour measurement acceptance.

## Delivered behaviour

- **KAN-130:** native UN consolidated XML and EU FSF 1.1 XML imports use the existing atomic, immutable snapshot command. XML input and normalised output are each capped at 32 MiB, with at most 100,000 named records. DTDs, entities and external references are forbidden. Separate authorities retain source digest, list version, publication date and declared reuse terms. Missing configuration produces an authority-specific unavailable receipt. Names and aliases are candidate matches, not identity verification or a clearance verdict.
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
| NVD | Guarded GET `https://services.nvd.nist.gov/rest/json/cves/2.0?hasKev&kevStartDate=2026-09-01T00:00:00.000&kevEndDate=2026-09-30T00:00:00.000&resultsPerPage=1`: successful `vulnerabilities` response, `cisaExploitAdd`, `lastModified`, `metrics.cvssMetricV31` and `metrics.ssvcV203` observed. | Proves the public bounded CVSS route works. NVD HTML developer and terms pages returned HTTP 403 locally and could not be opened by the web tool; current published terms and exact public rate policy still need direct operator verification before release. |

The [FIRST FAQ](https://www.first.org/epss/faq) and [data/API documentation](https://www.first.org/epss/data) describe freely available EPSS scores and attribution. The adapter uses at most ten batches of one hundred CVEs daily, within the API's 2,000-character CVE-filter bound. It uses one NVD `hasKev` request daily over the retained thirty-day KEV window, capped at one thousand returned records, with no pagination. Both counters and failures are logged without private input. Failure stops that provider until the next daily allowance; the other provider can still succeed. Budgets reset on process restart, as do the in-memory score cache and retained feed state. No optional NVD key is needed for this one-request design. Required release review: [NVD rate policy](https://nvd.nist.gov/developers/start-here), [API filters](https://nvd.nist.gov/developers/vulnerabilities), [terms](https://nvd.nist.gov/developers/terms-of-use).

GLEIF's [API overview](https://www.gleif.org/en/lei-data/gleif-api/) and [API demonstration](https://api.gleif.org/demo) describe legal-name and legal-address-country filters. GLEIF candidates are fixture-tested here; no live company name was disclosed during development.

The map eligibility review uses [USGS data licensing](https://www.usgs.gov/data-management/data-licensing), [USGS acknowledgement guidance](https://www.usgs.gov/information-policies-and-instructions/acknowledging-or-crediting-usgs) and [NASA Earthdata use policy](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy). Export retains source links and attribution and does not imply endorsement. Expanding eligibility requires a new source-specific review.

## Verification and integration

- Focused backend suite: 163 passing tests covering imports, candidates, source admission/catalogue, enrichment, credential isolation, STIX schemas and release checks. Additional malformed-NVD/STIX bound checks: 11 passing tests in the two focused files.
- Frontend: 12 tests passing across GLEIF confirmation, existing registry routing, KEV sorting/partial availability, STIX marking selection, existing Markdown export and live-map serialisation.
- Backend Ruff source checks, focused mypy and all three import-layer contracts pass. Generated OpenAPI and TypeScript bindings are updated. Full coverage was not measured in this concurrent worktree.
- OASIS STIX schemas are vendored unchanged at commit `c4f8d589acf2bdb3783655c89e0ffb6e150006ae`, with original licence, provenance and only the recursive schema closure needed by this writer. Dev-only `jsonschema` validates offline; no production dependency was added.
- STIX limits: at most 1,000 frozen evidence records, 3,000 derived evidence objects and 8 MiB output. It rejects an oversized export rather than silently truncating it. All actor objects are reference identities, not incident attribution.
- KAN-44 overlap: `cli_designations.py` imports dataset adapters lazily. Three narrow research-service configuration additions in `container/__init__.py` must move with the architecture branch's `feed_services.py` extraction. Source/allocation metadata was split to keep edited handwritten files below the normal size target.
- Frontend tools warn that the installed Node 22.20.0 is older than the repository's required 22.22.0. CI or release validation should use the declared runtime.

No branch was pushed or merged by this worker. KAN-130 source-specific licence/access enabling, KAN-133 current NVD terms/rate verification and KAN-134 live data-row validation are explicit outstanding external acceptance, not fixture-test successes.

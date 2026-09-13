# Military infrastructure: public source register

Reviewed: 13 September 2026. Scope: Russia, China, Belarus, Ukraine, Estonia,
Latvia, Lithuania, United States, Canada and Australia. China appeared twice in
the request and is counted once.

This is a source and data-quality register used by the optional country-level
Infrastructure source index. It is **not** an inventory of installations or a
facility map layer. It contains no site coordinates, site boundaries, or
present-day site-to-unit pairings.
Publicly named organisations are not evidence that a particular unit currently
occupies a particular facility. The companion machine-readable register is
[`military_infrastructure_sources.json`](../../frontend/src/features/globe/infrastructure/military_infrastructure_sources.json).

## Research finding

There is no single public, authoritative and consistently defined list of *all
major military locations* across these ten countries. “Major” is not a common
international classification. Even the US public [MilitaryINSTALLATIONS
directory](https://installations.militaryonesource.mil/view-all) says explicitly
that it lists only service-approved locations and **does not list every
installation**. The US [DISDI programme](https://www.acq.osd.mil/eie/imr/rpid/disdi/index.html)
offers a public dataset for major installations, ranges and training areas, but
its [release notes](https://www.acq.osd.mil/eie/imr/rpid/disdi/Downloads/release_notes.pdf)
also say the collection is not necessarily comprehensive and is for planning,
not surveyed boundaries. Australia publishes a major-base map in its annual
report. Several other official sources primarily describe command structure,
not an estate inventory. Treating these as equivalent coverage would produce a
misleading worldwide map.

The coverage split is material: the United States, Canada and Australia have
official public directories that describe facilities or support bases. The
other seven country sources in this review are principally legal, ministry or
force-structure pages. This is a classification of the sources examined, not a
claim that those seven countries publish no other material. A future product
should show that distinction before offering country comparisons.

| Country | Best official starting points | What they establish | Main limitation |
| --- | --- | --- | --- |
| Russia | [Official 2024 military-administrative division decree](https://publication.pravo.gov.ru/document/0001202402260031); [Russian Government ministry entry](https://government.ru/en/department/94/) | Statutory territorial command framework and ministry responsibility | Neither is a current comprehensive public installation or occupancy register. The 2024 decree must be checked for later amendments. |
| China | [Ministry of National Defense](https://eng.mod.gov.cn/2025xb/A_251795/index.html); [National Defense Law](https://eng.mod.gov.cn/2025xb/M/L_251592/16415117.html) | Official ministry and high-level framework for the Central Military Commission, theatre commands, services and arms | Ministry pages are organisational, not a public installation inventory. English pages may lag Chinese-language changes. |
| Belarus | [Ministry of Defence force structure](https://www.mil.by/ru/forces/structure/) | Ministry, General Staff, land forces, air and air-defence forces, and other high-level components | No comparable verified site inventory; the page is a command chart, not evidence of present site occupancy. |
| Ukraine | [Ministry of Defence overview](https://mod.gov.ua/pro-nas); [Armed Forces structure](https://www.zsu.gov.ua/suchasni-zbroini-syly-ukrainy/struktura-zbroinykh-syl-ukrainy) | Official service and command taxonomy, including newer branches | Wartime force structure and locations change rapidly. These pages do not establish current positions or installations. |
| Estonia | [Estonian Defence Forces overview](https://mil.ee/en/defence-forces/) | Public organisation and reserve-force context | A force overview is not a complete estate list. Avoid inferring base occupancy from unit/contact pages. |
| Latvia | [National Armed Forces structure](https://www.mil.lv/en/par-mums/about-national-armed-forces/structure) | Regular forces, National Guard and reserve framework | No comprehensive site register in this source. |
| Lithuania | [Lithuanian Armed Forces structure](https://www.kariuomene.lt/en/structure/23581); [Ministry structure](https://kam.lt/en/structure/) | Official force and ministry organisation | Organisational pages do not establish a complete facility inventory. |
| United States | [MilitaryINSTALLATIONS](https://installations.militaryonesource.mil/view-all); [DISDI programme](https://www.acq.osd.mil/eie/imr/rpid/disdi/index.html) and [dataset notes](https://www.acq.osd.mil/eie/imr/rpid/disdi/Downloads/release_notes.pdf) | Public installation directory and a defined planning dataset | The directory is explicitly selective; the geospatial release is not necessarily comprehensive and its site points are not surveyed landmarks. |
| Canada | [Bases and support units](https://www.canada.ca/en/department-national-defence/services/bases-support-units.html); [Canadian Army bases and units overview](https://www.canada.ca/en/army/corporate/bases-and-units.html) | Official base/support-unit names, service types and provinces, plus broad Army regional structure | Directory scope is support-oriented, not a certified complete list of all defence sites or current occupants. |
| Australia | [Defence base directory](https://www.defence.gov.au/about/locations-property/base-induction); [Defence Annual Report 2024–25](https://www.defence.gov.au/sites/default/files/2025-10/Defence-Annual-Report-2024-25.pdf) | Public base directory and a nationally defined major-base overview | The directory serves base induction; the annual-report map is a dated snapshot, not live occupancy data. |

[NATO's eastern-flank overview](https://nato.int/en/what-we-do/deterrence-and-defence/strengthening-natos-eastern-flank)
is a cross-check for the *presence of multinational Forward Land Forces at the
country level* in Estonia, Latvia and Lithuania. It is not a base inventory and
should not be interpreted as a fixed local unit roster.

## Source assessment

The ministry and armed-forces pages above are primary sources for their own
declared structures. That makes them strong evidence for names and official
relationships, but only within their stated scope. They are not independently
verified evidence of operational readiness, deployment or current occupancy.
The US, Canadian and Australian estate-oriented sources are more useful for a
future facility catalogue, but differ substantially in inclusion criteria.

Source assertions should be stored separately from assessed claims:

| Field | Intended meaning |
| --- | --- |
| `publisher`, `url`, `retrieved_at`, `published_at` | Traceable provenance; a missing publication date remains unknown. |
| `assertion_scope` | Organisation, estate directory, planning dataset or annual-report snapshot. |
| `country_code`, `admin_area` | Country and, where warranted, broad administrative context. |
| `facility_role` | Publicly described role such as training, air, naval, logistics or administration. |
| `review_state` | Unreviewed, corroborated, contradicted or superseded. |
| `freshness` | Explicit observation date, never an assumed live status. |

`published_at` in the JSON means the linked *page or report* date when one was
visible; it is not necessarily the date on which a law first took effect. During
this review, the Russian legal portal, Russian ministry page, Chinese ministry
pages and the large Australian annual-report PDF could be located through their
official indexes or search results but could not be fully fetched by the research
browser. Their metadata and scope should be rechecked before extraction. The
Belarusian, Ukrainian, Baltic, US directory, Canadian and Australian directory
pages were directly readable. This is a source-access limitation, not evidence
that the inaccessible material is incorrect.

Do not automatically convert a unit's public organisation page into a claim that
it occupies a named site today. Keep a source's own words and the analyst's
inference distinct. A source that reports an organisational change should
supersede, rather than silently overwrite, an earlier assertion. Absence from a
directory is not evidence that a facility does not exist.

## Preparation for a future Infrastructure category

The packaged JSON is deliberately a **source register**, not GeoJSON and not a
ready-to-render facility marker set. The map's optional country badges use the
country catalogue's centroids solely to open this register. Their coordinates
do not come from military sources and must never be interpreted as a site.
The panel shows publisher, coverage and known limitations. No source has been
bulk scraped or geocoded, and redistribution licences were not assessed in
this pass. Before ingesting content, verify each publisher's reuse terms,
field definitions and refresh behaviour.

A category should label its coverage as partial, show source dates on every
record, and distinguish permanent estate records from time-sensitive reporting.
It should never present a facility's type as proof of active use. The repository's
existing [infrastructure documentation](../MAP_INFRASTRUCTURE.md) already makes
the same distinction for cables and ground stations: a public marker does not
imply operational status.

## Open questions

1. What exact definition of “major” should apply across countries? The US
   size-based definition, Canada's support-base directory and Australia's
   annual-report selection are not equivalent.
2. Which publishers permit automated extraction and republication in this app?
   Public readability alone does not grant database reuse rights.
3. What update cadence is appropriate for each source? A dated annual report
   and a live web directory should not share the same freshness label.
4. How will a future layer communicate unknown coverage and retired or renamed
   organisations without suggesting that an old record is current?

# Source licences and attribution register

KAN-194 records source rights and current code defaults at revision
`13efceef48efbc6d5f2895e60c55076db5d40e3f`, inspected on 9 October 2026.
This is a due-diligence register, not legal advice, a signed provider agreement,
or approval to enable a source. Contentious interpretations require legal review.
No runtime configuration or provider permission changed as part of this register.

## Coverage and evidence limits

Every backend catalogue identity is listed below, including optional/keyed feeds,
on-demand research, all camera providers, map layers and packaged reference assets.
The completeness test takes the union of supported credential configurations so
that missing keys cannot hide a source. A row is not proof of licensing clearance.

The machine-readable inputs are packaged with the backend:
[source_licences.json](../backend/src/ase/resources/source_licences.json) and
[source_licence_policies.json](../backend/src/ase/resources/source_licence_policies.json).
Join a source's `policy` to `policies[policy]` for terms, dates, commercial and
hosted status, attribution, redistribution, risk and action. `source_url` is a
discovery/provenance link, not a substitute for `terms_url`. Unknown terms remain
null. `additional_policies` links enrichment providers whose conditions also apply;
the primary row's status never overrides those additional conditions.
`upstream_licence_note` preserves an existing code claim as an unverified lead.
These files are inventory only; KAN-195 owns runtime enforcement and KAN-165 owns
the public attribution presentation. Consumers must not interpret unknown or
permission-required records as approved, or treat conditional records as proof
that this deployment satisfies the conditions.

`terms_checked` means the cited terms were inspected, not that an agreement exists.
`partial_review` identifies narrower evidence or unresolved product rights.
`lookup_blocked` dates an inaccessible lookup; `lookup_inconclusive` dates a
search that did not establish applicable terms. Neither has a verification date.
Their links identify the attempted terms page or provider discovery page, not a
verified grant. `not_reviewed` has no terms-check or attempted-lookup date.
All dates use UTC. The code inventory date is separate from all of these.
`per_item_required` is a mixed/user-supplied content boundary with no blanket
provider grant. Each item's original rights and owner must be assessed separately.
For unchecked rows the missing primary terms link and date are outstanding work,
not a fabricated verification. Review the linked provider and exact product.

## Priority decisions for Alex

1. Obtain permission or replace EOX 2024 for a commercial offering. `hybrid` is
   the initial basemap and includes this imagery. The image-export declaration
   does not grant browser display or downstream image rights.
2. Resolve Cloudflare Radar and OONI non-commercial restrictions. Radar's token-only
   live/attack paths differ from its acknowledgement-gated research paths.
3. Review Telegram collection and AI use urgently against its current content
   terms. Review YouTube's refresh/deletion rules against frozen evidence and exports.
4. Obtain publisher rights for The Independent and CNA; audit other RSS publishers
   separately. RSS availability, a link or an excerpt limit does not grant reuse.
5. Keep DeepState API permission separate from the visual-content licence. Review
   ACLED's actual account agreement and permitted external transformations.
6. Complete per-camera owner/host rights and the remaining unverified products
   before treating any of them as commercially cleared. IODA's unverified terms must
   be resolved; its existing live feeds have different gates from research.
7. Obtain ISW's written permission for analytical/map/dataset integration. Check
   purpose restrictions as well as commercial status: Pennsylvania's documented
   camera programme is for current traffic information, which does not establish
   permission for an OSINT evidence archive.

[Unsent permission requests](source-audit/KAN-194-permission-requests.md) are for
Alex to review and send. [Replacement candidates](source-audit/KAN-194-replacements.md)
describe commercially usable options and their remaining conditions. adsb.fi,
Reddit, Open-Meteo, Global Fishing Watch and OpenSanctions have supplementary
records because they are not backend catalogue entries at this revision.

## Current defaults and row key

Defaults describe clean code configuration, not the running deployment or a
licensing decision. `scheduled` feeds also depend on `ASE_FEEDS_ENABLED`,
`ASE_FEEDS_DISABLED`, credentials where shown, and administrator source controls.
`on_demand` means an available request path, not background collection or default
display. `available_asset` means a packaged/reference asset is available; this does
not imply that its map overlay is selected. `off_until_configured` identifies a
missing prerequisite; `off_until_selected` is an initially unselected layer.
Optional credentials can raise limits without disabling public access. The
initial hybrid base map uses EOX imagery and OpenFreeMap labels. User preferences
can change that choice. Uploads and combined reports retain per-item restrictions.

In the rights column, **C** is commercial use and **H** is hosted/multi-user use:
`conditional` requires the cited conditions and deployment review;
`permission_required` has no verified project-specific grant; `unknown` is
unresolved. The linked policy supplies the row's attribution and redistribution
requirements. Actions are recommendations, not changes already made. A setting,
API key, login, paid plan or acknowledgement alone is not a copyright licence.

Inventory: **580 source identities**. Terms status by source: lookup_blocked: 106, lookup_inconclusive: 50, partial_review: 189, per_item_required: 6, terms_checked: 229.

## Camera index

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `camera:africa-live` [SkylineWebcams Africa](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:alaska` [Alaska 511](https://511.alaska.gov) | [terms/evidence](https://511.alaska.gov/about/disclaimer); partial_review; 2026-10-09 | unknown / unknown | [camera-alaska](#policy-camera-alaska) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:alberta` [Alberta 511](https://511.alberta.ca/api/v2/get/cameras) | [terms/evidence](https://511.alberta.ca/about/about); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-alberta](#policy-camera-alberta) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:arizona` [ADOT](https://az511.gov) | [terms/evidence](https://azdot.gov/disclaimer); partial_review; 2026-10-09 | unknown / unknown | [camera-arizona](#policy-camera-arizona) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:asfinag` [ASFINAG (Austria)](https://odo.asfinag.at/odo/rest/sec/resource/001/json/webcams) | [terms/evidence](https://media.asfinag.at/media/lsgfvnz1/webcam-informationen-durch-webcampartner.pdf); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-asfinag](#policy-camera-asfinag) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:asia-live` [SkylineWebcams Asia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:australia` [Transport for NSW](https://www.livetraffic.com/datajson/all-feeds-web.json) | [terms/evidence](https://data.nsw.gov.au/data/en/dataset/2-live-traffic-cameras); partial_review; 2026-10-09 | unknown / unknown | [camera-nsw](#policy-camera-nsw) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:autostrade` [Autostrade per l'Italia](https://www.autostrade.it/it/viaggia-sicuro/webcam) | [attempted page](https://www.autostrade.it/it/home); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-autostrade](#policy-camera-autostrade) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:baltic-live` [Baltic public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:bulgaria` [Bulgaria](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:caltrans` [Caltrans](https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CCTV/FeatureServer/0/query) | [terms/evidence](https://dot.ca.gov/conditions-of-use); partial_review; 2026-10-09 | unknown / unknown | [camera-caltrans](#policy-camera-caltrans) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:china-live` [China public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:connecticut` [CTroads](https://ctroads.org) | [attempted page](https://www.ctroads.com/about/disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-connecticut](#policy-camera-connecticut) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:czechia` [Czechia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:derbyshire` [Derbyshire County Council traffic cameras](https://apps.derbyshire.gov.uk/applications/traffic-cameras/camera-locations.asp) | [terms/evidence](https://www.derbyshire.gov.uk/council/performance/open-data/license/licence.aspx); partial_review; 2026-10-09 | unknown / unknown | [camera-derbyshire](#policy-camera-derbyshire) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:drivebc` [DriveBC](https://www.drivebc.ca/api/webcams/) | [terms/evidence](https://www2.gov.bc.ca/gov/content/data/policy-standards/data-policies/open-data/open-government-licence-bc); partial_review; 2026-10-09 | unknown / unknown | [camera-drivebc](#policy-camera-drivebc) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:durham` [Durham County Council](https://www.durham.gov.uk/trafficcameras) | [terms/evidence](https://www.data.gov.uk/dataset/2c4818e4-3da2-4bdb-a8d9-894d700f889a/https-datamillnorth-org-dataset-2kq9x-traffic-web-cameras); partial_review; 2026-10-09 | unknown / unknown | [camera-durham](#policy-camera-durham) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:eastasia` [OpenCCTV East Asia](https://opencctv.org/) | [attempted page](https://opencctv.org/about); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-opencctv](#policy-camera-opencctv) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:estonia` [Transpordiamet Tark Tee (Estonia)](https://tarktee.mnt.ee/) | [attempted page](https://tarktee.ee/#/en/datex); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-estonia](#policy-camera-estonia) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:europe-live` [SkylineWebcams Europe](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:fintraffic` [Fintraffic](https://www.digitraffic.fi/en/road-traffic/) | [terms/evidence](https://www.digitraffic.fi/en/terms-of-service/); terms_checked; 2026-10-09 | conditional / conditional | [camera-fintraffic](#policy-camera-fintraffic) | on_demand; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:florida` [FDOT](https://fl511.com) | [attempted page](https://teo.fdot.gov/architecture/architectures/d5/html/agreements/agreements.html); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-florida](#policy-camera-florida) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:france` [France](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:georgia` [GDOT](https://511ga.org) | [attempted page](https://511ga.org/about/disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-georgia](#policy-camera-georgia) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:germany` [Germany](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:greece` [Greece](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:hongkong` [Hong Kong Transport Department](https://data.gov.hk/en-data/dataset/hk-td-tis_1-traffic-snapshot-images) | [terms/evidence](https://data.gov.hk/en/terms-and-conditions); partial_review; 2026-10-09 | unknown / unknown | [camera-hongkong](#policy-camera-hongkong) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:hungary` [Magyar Kozut Utinform (Hungary)](https://www.utinform.hu/) | [attempted page](https://www.utinform.hu/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-hungary](#policy-camera-hungary) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:iceland` [Vegagerðin (Iceland)](https://gagnaveita.vegagerdin.is/api/vefmyndavelar2014_1) | [terms/evidence](https://www.vegagerdin.is/vegagerdin/gagnasafn/vefthjonustur/skilmalar-vefthjonustur); terms_checked; 2026-10-09 | conditional / conditional | [camera-iceland](#policy-camera-iceland) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:idaho` [Idaho 511](https://511.idaho.gov) | [terms/evidence](https://511.idaho.gov/about/privacy); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-idaho](#policy-camera-idaho) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:illinois` [Travel Midwest](https://travelmidwest.com/lmiga/cameraReport.json) | [terms/evidence](https://travelmidwest.com/About/InfoReusePolicy); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-illinois](#policy-camera-illinois) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:indiana` [INDOT TrafficWise](https://511in.org/api/graphql) | [attempted page](https://511in.org/about/disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-indiana](#policy-camera-indiana) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:iowa` [Iowa 511](https://www.511ia.org) | [terms/evidence](https://iowadot.gov/policies-statements/terms-use); partial_review; 2026-10-09 | unknown / unknown | [camera-iowa](#policy-camera-iowa) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:iraq-iran-live` [Iraq and Iran public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:ireland` [Transport Infrastructure Ireland](https://www.tiitraffic.ie/) | [terms/evidence](https://www.tii.ie/en/compliance/reuse-of-public-sector-information/); partial_review; 2026-10-09 | unknown / unknown | [camera-ireland](#policy-camera-ireland) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:israel-live` [Israel public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:italy` [Italy](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:japan` [Japan public webcams and MLIT rivers](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:kansas` [KanDrive](https://www.kandrive.gov) | [attempted page](https://www.ksdot.gov/travel/travel-conditions/kandrive); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-kansas](#policy-camera-kansas) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:latam-live` [SkylineWebcams Latin America](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:lithuania` [Lietuvos automobiliu keliu direkcija (eismoinfo.lt)](https://eismoinfo.lt/) | [attempted page](https://eismoinfo.lt/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-lithuania](#policy-camera-lithuania) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:louisiana` [LADOTD](https://511la.org) | [terms/evidence](https://511la.org/about/disclaimer); partial_review; 2026-10-09 | unknown / unknown | [camera-louisiana](#policy-camera-louisiana) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:luxembourg` [CITA (Luxembourg)](https://www.cita.lu/) | [terms/evidence](https://data.public.lu/en/datasets/cita-cameras-autoroute/); partial_review; 2026-10-09 | unknown / unknown | [camera-luxembourg](#policy-camera-luxembourg) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:lyon` [Metropole de Lyon (Criter)](https://data.grandlyon.com/) | [terms/evidence](https://www.data.gouv.fr/datasets/cameras-web-criter-de-la-metropole-de-lyon); partial_review; 2026-10-09 | unknown / unknown | [camera-lyon](#policy-camera-lyon) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:macedonia` [North Macedonia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:madrid` [Ayuntamiento de Madrid (Informo)](https://informo.madrid.es/) | [terms/evidence](https://datos.madrid.es/dataset/202088-0-trafico-camaras/information); partial_review; 2026-10-09 | conditional / conditional | [camera-madrid](#policy-camera-madrid) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:manitoba` [Manitoba 511](https://www.manitoba511.ca) | [attempted page](https://www.manitoba511.ca/about/disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-manitoba](#policy-camera-manitoba) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:massachusetts` [Mass511](https://mass511.com) | [terms/evidence](https://www.mass.gov/doc/developers-license-agreement-11132009/download); partial_review; 2026-10-09 | permission_required / permission_required | [camera-massachusetts](#policy-camera-massachusetts) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:michigan` [MDOT MiDrive](https://mdotjboss.state.mi.us/MiDrive/camera/list) | [attempted page](https://www.michigan.gov/mdot/Travel/safety/Efforts/ITS/SEMTOC); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-michigan](#policy-camera-michigan) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:middle-east` [Middle East public webcam streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:minnesota` [MnDOT 511](https://511mn.org) | [attempted page](https://511mn.org/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-minnesota](#policy-camera-minnesota) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:montreal` [Ville de Montreal](https://ville.montreal.qc.ca/circulation/sites/ville.montreal.qc.ca.circulation/files/cameras.json) | [attempted page](https://donnees.montreal.ca/dataset/cameras-observation-routiere); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-montreal](#policy-camera-montreal) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:netherlands` [Rijkswaterstaat](https://api.rwsverkeersinfo.nl/api/cameras/) | [terms/evidence](https://www.rijkswaterstaat.nl/copyright); partial_review; 2026-10-09 | unknown / unknown | [camera-rws](#policy-camera-rws) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:nevada` [NDOT](https://www.nvroads.com) | [attempted page](https://www.nvroads.com/about/disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-nevada](#policy-camera-nevada) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newbrunswick` [New Brunswick 511](https://511.gnb.ca) | [attempted page](https://511.gnb.ca/about/disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-newbrunswick](#policy-camera-newbrunswick) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newengland` [New England 511](https://newengland511.org) | [terms/evidence](https://newengland511.org/terms); partial_review; 2026-10-09 | unknown / unknown | [camera-newengland](#policy-camera-newengland) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newfoundland` [511 Newfoundland and Labrador](https://511nl.ca) | [terms/evidence](https://511nl.ca/terms); partial_review; 2026-10-09 | unknown / unknown | [camera-newfoundland](#policy-camera-newfoundland) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newyork` [511NY](https://511ny.org) | [terms/evidence](https://www.511ny.org/developers/resources); partial_review; 2026-10-09 | permission_required / permission_required | [camera-newyork](#policy-camera-newyork) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newzealand` [NZTA Waka Kotahi](https://trafficnz.info/service/traffic/rest/4/cameras/all) | [terms/evidence](https://www.nzta.govt.nz/about-us/our-data-and-official-information/use-our-data/terms-of-use); partial_review; 2026-10-09 | unknown / unknown | [camera-nzta](#policy-camera-nzta) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:northcarolina` [NCDOT](https://www.drivenc.gov) | [terms/evidence](https://www.ncdot.gov/about-us/how-we-operate/policy-process/Pages/terms-use.aspx); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-northcarolina](#policy-camera-northcarolina) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:northeast` [North East Traffic Cameras (Tyne and Wear UTMC)](https://netrafficcams.co.uk/all-cameras) | [terms/evidence](https://www.netraveldata.co.uk/?page_id=13); partial_review; 2026-10-09 | conditional / conditional | [camera-northeast](#policy-camera-northeast) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:northyorkshire` [North Yorkshire Council weather cameras](https://www.northyorks.gov.uk/nycc_weather_cameras/markers) | [terms/evidence](https://www.northyorks.gov.uk/your-council/websites-and-media/your-council/websites-and-media/terms-and-conditions); partial_review; 2026-10-09 | unknown / unknown | [camera-northyorkshire](#policy-camera-northyorkshire) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:norway` [Statens vegvesen (Norway)](https://www.vegvesen.no/trafikk/) | [terms/evidence](https://www.vegvesen.no/en/fag/technology/open-data/a-selection-of-open-data/what-is-datex/); partial_review; 2026-10-09 | unknown / unknown | [camera-norway](#policy-camera-norway) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:novascotia` [Nova Scotia 511](https://511.novascotia.ca) | [terms/evidence](https://511.novascotia.ca/about/about); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-novascotia](#policy-camera-novascotia) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:ontario` [Ontario 511](https://511on.ca/api/v2/get/cameras) | [terms/evidence](https://511on.ca/developers/resources); partial_review; 2026-10-09 | unknown / unknown | [camera-ontario](#policy-camera-ontario) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:oregon` [ODOT TripCheck](https://www.tripcheck.com/Scripts/map/data/cctvinventory.js) | [attempted page](https://www.tripcheck.com/Pages/API); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-oregon](#policy-camera-oregon) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:ottawa` [City of Ottawa](https://traffic.ottawa.ca/beta/camera_list) | [terms/evidence](https://traffic.ottawa.ca/en/traffic-map-data-lists-and-resources/faq); partial_review; 2026-10-09 | unknown / unknown | [camera-ottawa](#policy-camera-ottawa) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:pennsylvania` [511PA](https://www.511pa.com) | [terms/evidence](https://www.pa.gov/content/dam/copapwp-pagov/en/penndot/documents/programs-and-doing-business/onlineservices/511pa_developers_corner-tcs.pdf); partial_review; 2026-10-09 | permission_required / permission_required | [camera-pennsylvania](#policy-camera-pennsylvania) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:poland` [Poland](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:puertorico` [ACT Puerto Rico ITS](https://its.act.pr.gov/) | [attempted page](https://www.dtop.pr.gov/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-puertorico](#policy-camera-puertorico) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:quebec` [Quebec 511](https://ws.mapserver.transports.gouv.qc.ca/swtq) | [terms/evidence](https://www.donneesquebec.ca/recherche/dataset/camera-de-circulation); partial_review; 2026-10-09 | unknown / unknown | [camera-quebec](#policy-camera-quebec) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:queensland` [QLDTraffic (Queensland)](https://qldtraffic.qld.gov.au/) | [terms/evidence](https://www.data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api); partial_review; 2026-10-09 | unknown / unknown | [camera-queensland](#policy-camera-queensland) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:romania` [Romania](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:russia-live` [Russia public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:saskatchewan` [Saskatchewan Highway Hotline](https://hotline.gov.sk.ca) | [terms/evidence](https://www.saskatchewan.ca/copyright); partial_review; 2026-10-09 | unknown / unknown | [camera-saskatchewan](#policy-camera-saskatchewan) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:seasia` [OpenCCTV Southeast Asia](https://opencctv.org/) | [attempted page](https://opencctv.org/about); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-opencctv](#policy-camera-opencctv) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:serbia` [Serbia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:singapore` [Singapore LTA](https://api.data.gov.sg/v1/transport/traffic-images) | [terms/evidence](https://data.gov.sg/open-data-licence); terms_checked; 2026-10-09 | conditional / conditional | [camera-singapore](#policy-camera-singapore) | on_demand; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:slovakia` [Slovakia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:spain` [Spain](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:spain-dgt` [DGT (Spain)](https://www.dgt.es/.content/.assets/json/camaras.json) | [terms/evidence](https://nap.dgt.es/es/dataset/camaras-dgt-datex2-v3-7); partial_review; 2026-10-09 | unknown / unknown | [camera-dgt](#policy-camera-dgt) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:switzerland` [Switzerland](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:taiwan` [Taiwan Highway Bureau](https://thbapp.thb.gov.tw/services/cctv/thb) | [terms/evidence](https://data.gov.tw/dataset/29817); partial_review; 2026-10-09 | unknown / unknown | [camera-taiwan](#policy-camera-taiwan) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:taiwan-live` [Taiwan public webcam streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:tallinn` [Tallinn junction cameras](https://ristmikud.tallinn.ee/) | [attempted page](https://ristmikud.tallinn.ee/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-tallinn](#policy-camera-tallinn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:tfl` [Transport for London](https://tfl.gov.uk/info-for/open-data-users/) | [terms/evidence](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service); terms_checked; 2026-10-09 | conditional / conditional | [camera-tfl](#policy-camera-tfl) | on_demand; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:thailand` [Thailand public webcam streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:toronto` [City of Toronto](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/a3309088-5fd4-4d34-8297-77c8301840ac/resource/4a568300-c7f8-496d-b150-dff6f5dc6d4f/download/traffic-camera-list-4326.geojson) | [terms/evidence](https://open.toronto.ca/dataset/traffic-cameras/); partial_review; 2026-10-09 | unknown / unknown | [camera-toronto](#policy-camera-toronto) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:traffic-scotland` [Traffic Scotland](https://www.traffic.gov.scot/traffic-cameras) | [terms/evidence](https://www.traffic.gov.scot/copyright); terms_checked; 2026-10-09 | permission_required / permission_required | [camera-scotland](#policy-camera-scotland) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:turkey` [Turkey](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:uk-live` [UK public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:uk-local` [UK council, island and crossing cameras](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:us-published` [US published webcams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | [terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE); partial_review; 2026-10-09 | unknown / unknown | [osiris-curated](#policy-osiris-curated) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:utah` [UDOT Traffic](https://prod-ut.ibi511.com) | [terms/evidence](https://udottraffic.utah.gov/about/disclaimer); partial_review; 2026-10-09 | unknown / unknown | [camera-utah](#policy-camera-utah) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:westasia` [OpenCCTV West and Central Asia](https://opencctv.org/) | [attempted page](https://opencctv.org/about); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [camera-opencctv](#policy-camera-opencctv) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:westmorland` [Westmorland and Furness Council weather cameras](https://www.westmorlandandfurness.gov.uk/parking-streets-and-transport/streets-roads-and-pavements/weather-cameras) | [terms/evidence](https://www.westmorlandandfurness.gov.uk/disclaimer); partial_review; 2026-10-09 | unknown / unknown | [camera-westmorland](#policy-camera-westmorland) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:wsdot` [WSDOT](https://www.wsdot.wa.gov/traffic/api/) | [attempted page](https://wsdot.wa.gov/about/policies/travel-information-disclaimer); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [camera-wsdot](#policy-camera-wsdot) | off_until_configured; ASE_WSDOT_ACCESS_CODE | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:yukon` [511 Yukon](https://511yukon.ca) | [terms/evidence](https://511yukon.ca/about/disclaimer); partial_review; 2026-10-09 | unknown / unknown | [camera-yukon](#policy-camera-yukon) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Feed

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `acled_events` [ACLED political violence and protest events](https://acleddata.com) | [terms/evidence](https://acleddata.com/eula); terms_checked; 2026-10-09 | permission_required / permission_required | [acled](#policy-acled) | off_until_configured; ASE_ACLED_REFRESH_TOKEN or ASE_ACLED_ACCESS_TOKEN | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_areas` [Traffic over watched areas (adsb.lol ADS-B)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_emergency` [Emergency squawks (adsb.lol ADS-B)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_global` [Worldwide sampled sweep (adsb.lol)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_ladd` [LADD aircraft (owners limiting display)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_mil` [Military aircraft (adsb.lol ADS-B)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_pia` [PIA aircraft (privacy ICAO addresses)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_viewport` [Aircraft in requested map areas (adsb.lol)](https://adsb.lol/) | [terms/evidence](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `aisstream` [AISStream: global ship positions](https://aisstream.io/) | [terms/evidence](https://www.aisstream.io/documentation); partial_review; 2026-10-09 | unknown / unknown | [aisstream](#policy-aisstream) | off_until_configured; ASE_AISSTREAM_API_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `barentswatch_ais` [BarentsWatch AIS: Norwegian maritime zones](https://www.barentswatch.no/) | [terms/evidence](https://www.barentswatch.no/artikler/api-vilkar/); terms_checked; 2026-10-09 | conditional / conditional | [barentswatch](#policy-barentswatch) | off_until_configured; ASE_BARENTSWATCH_CLIENT_ID and ASE_BARENTSWATCH_CLIENT_SECRET | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bluesky_curated` [Bluesky curated accounts](https://bsky.app/) | [terms/evidence](https://bsky.social/about/support/tos); partial_review; 2026-10-09 | unknown / unknown | [bluesky](#policy-bluesky) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_active` [Active satellites (CelesTrak)](https://celestrak.org/) | [terms/evidence](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_military` [Public military satellite catalogue (CelesTrak)](https://celestrak.org/) | [terms/evidence](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_skynet` [Skynet public orbital elements (CelesTrak)](https://celestrak.org/) | [terms/evidence](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_stations` [Space stations and crewed vehicles (CelesTrak)](https://celestrak.org/) | [terms/evidence](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cisa_kev` [CISA Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | [attempted page](https://www.cisa.gov/about/website-policies); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cisa](#policy-cisa); [first-epss](#policy-first-epss); [nist-nvd](#policy-nist-nvd) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. Default KEV events also contain FIRST EPSS and NIST NVD/CNA severity enrichment. Apply all three provider policies and preserve score-source attribution in retained and exported evidence. |
| `cloudflare_radar_outages` [Internet outages (Cloudflare Radar)](https://radar.cloudflare.com/outage-center) | [terms/evidence](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN | high; request_permission, legal_review; Token-only path: research non-commercial acknowledgement does not cover this path. Review permission before hosted/commercial use. |
| `digitraffic_ais` [Fintraffic AIS: Finnish waterways](https://www.digitraffic.fi/en/marine-traffic/) | [terms/evidence](https://www.digitraffic.fi/en/terms-of-service/); terms_checked; 2026-10-09 | conditional / conditional | [digitraffic](#policy-digitraffic) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `emsc_earthquakes` [EMSC earthquakes (M4+)](https://www.seismicportal.eu/) | [terms/evidence](https://www.seismicportal.eu/terms.html); terms_checked; 2026-10-09 | conditional / conditional | [emsc](#policy-emsc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_public_noaa20` [NASA FIRMS: public NOAA-20 24-hour detections](https://firms.modaps.eosdis.nasa.gov/) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_public_noaa21` [NASA FIRMS: public NOAA-21 24-hour detections](https://firms.modaps.eosdis.nasa.gov/) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_viirs_noaa20` [NASA FIRMS: NOAA-20 thermal detections](https://firms.modaps.eosdis.nasa.gov/) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | off_until_configured; ASE_FIRMS_MAP_KEY or Admin FIRMS key | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_viirs_noaa21` [NASA FIRMS: NOAA-21 thermal detections](https://firms.modaps.eosdis.nasa.gov/) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | off_until_configured; ASE_FIRMS_MAP_KEY or Admin FIRMS key | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gdacs` [GDACS disaster alerts](https://www.gdacs.org/) | [terms/evidence](https://data.gdacs.org/About/termofuse.aspx); partial_review; 2026-10-09 | unknown / unknown | [gdacs](#policy-gdacs) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gdelt_events` [GDELT 2.0 media signals (unreviewed)](https://www.gdeltproject.org/) | [terms/evidence](https://www.gdeltproject.org/about.html#termsofuse); terms_checked; 2026-10-09 | conditional / conditional | [gdelt](#policy-gdelt) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gdelt_news` [GDELT geolocated news signals (unreviewed)](https://www.gdeltproject.org/) | [terms/evidence](https://www.gdeltproject.org/about.html#termsofuse); terms_checked; 2026-10-09 | conditional / conditional | [gdelt](#policy-gdelt) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `google_news_watchlists` [Google News watchlists](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gvp_weekly` [Smithsonian weekly volcanic activity report](https://volcano.si.edu/reports_weekly.cfm) | [terms/evidence](https://volcano.si.edu/gvp_termsofuse.cfm); partial_review; 2026-10-09 | permission_required / permission_required | [gvp](#policy-gvp) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ifrc_go` [IFRC GO emergencies](https://go.ifrc.org/) | [attempted page](https://go.ifrc.org/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ifrc-go](#policy-ifrc-go) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ioda_outage_events` [Internet outage event windows (IODA)](https://ioda.inetintel.cc.gatech.edu/) | [attempted page](https://ioda.inetintel.cc.gatech.edu/resources); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [ioda](#policy-ioda) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Live path has no IODA acknowledgement gate; complete rights review separately from the research path. |
| `ioda_outages` [Internet outage alerts (IODA)](https://ioda.inetintel.cc.gatech.edu/) | [attempted page](https://ioda.inetintel.cc.gatech.edu/resources); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [ioda](#policy-ioda) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Live path has no IODA acknowledgement gate; complete rights review separately from the research path. |
| `isw_assessments` [ISW Russian Offensive Campaign Assessments](https://www.understandingwar.org/) | [terms/evidence](https://understandingwar.org/fair-use-and-attribution-policy/); terms_checked; 2026-10-09 | permission_required / permission_required | [isw](#policy-isw) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `jtwc` [JTWC tropical cyclone warnings](https://www.metoc.navy.mil/jtwc/jtwc.html) | [attempted page](https://www.metoc.navy.mil/jtwc/jtwc.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [jtwc](#policy-jtwc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `launch_library` [Upcoming launches (Launch Library 2)](https://thespacedevs.com/llapi) | [terms/evidence](https://github.com/TheSpaceDevs/Tutorials/blob/main/faqs/faq_TSD.md#terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [launch-library](#policy-launch-library) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nasa_eonet` [NASA EONET natural events](https://eonet.gsfc.nasa.gov/docs/v3) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nga_navarea` [NAVAREA broadcast warnings (NGA MSI)](https://msi.nga.mil/NavWarnings) | [attempted page](https://msi.nga.mil/home); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [nga-navwarnings](#policy-nga-navwarnings) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nhc_atlantic` [NHC Atlantic advisories](https://www.nhc.noaa.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nhc_east_pacific` [NHC Eastern Pacific advisories](https://www.nhc.noaa.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `noaa_swpc_alerts` [NOAA SWPC space weather alerts](https://www.swpc.noaa.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `noaa_swpc_scales` [NOAA SWPC current space weather scales](https://www.swpc.noaa.gov/noaa-scales-explanation) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ntwc_tsunami` [National Tsunami Warning Center bulletins](https://www.tsunami.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nws_alerts` [NWS severe weather alerts](https://www.weather.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ptwc_tsunami` [Pacific Tsunami Warning Center bulletins](https://www.tsunami.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ransomware_live` [Ransomware victim claims (ransomware.live)](https://www.ransomware.live/) | [terms/evidence](https://www.linkedin.com/posts/ransomwarelive_ransomware-cti-threatintelligence-activity-7495041175930888193-G25S); partial_review; 2026-10-09 | unknown / unknown | [ransomware-live](#policy-ransomware-live) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reliefweb_reports` [ReliefWeb humanitarian reports (API)](https://reliefweb.int/) | [attempted page](https://reliefweb.int/terms-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [reliefweb](#policy-reliefweb) | off_until_configured; ASE_RELIEFWEB_APPNAME | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `swpc_kp` [Planetary K index (NOAA SWPC)](https://www.swpc.noaa.gov/) | [terms/evidence](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ucdp_candidate` [UCDP monthly candidate violence events](https://ucdp.uu.se/downloads/) | [terms/evidence](https://www.uu.se/en/department/peace-and-conflict-research/research/ucdp/frequently-asked-questions.html); terms_checked; 2026-10-09 | conditional / conditional | [ucdp](#policy-ucdp) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls; ASE_UCDP_ACCESS_TOKEN | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine_general_staff` [General Staff of Ukraine daily loss claims](https://russianwarship.rip/) | [attempted page](https://russianwarship.rip/en); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [russianwarship](#policy-russianwarship) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `usgs_earthquakes` [USGS earthquakes (past day)](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) | [terms/evidence](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits); partial_review; 2026-10-09 | conditional / conditional | [usgs](#policy-usgs) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `who_don` [WHO Disease Outbreak News](https://www.who.int/emergencies/disease-outbreak-news) | [terms/evidence](https://www.who.int/about/policies/publishing/copyright); terms_checked; 2026-10-09 | permission_required / permission_required | [who](#policy-who) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Map layer

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `map:data_centres` [Data centres](https://www.openstreetmap.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); terms_checked; 2026-10-09 | conditional / conditional | [osm](#policy-osm) | available_asset; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:energy_sites` [Energy sites](https://www.openstreetmap.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [mixed-osm-wikidata](#policy-mixed-osm-wikidata) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Review the combined OSM, Wikidata and curated-record provenance; retain each applicable notice. |
| `map:eox_s2cloudless` [Sentinel-2 cloudless imagery](https://s2maps.eu/) | [terms/evidence](https://cloudless.eox.at/license-non-commercial); terms_checked; 2026-10-09 | permission_required / permission_required | [eox-2024](#policy-eox-2024) | initial_hybrid_basemap; No display licence gate; image export requires suitable-use declaration | high; request_permission, legal_review; Prioritise commercial licence or replacement: 2024 imagery is selected by the initial hybrid basemap; export declarations do not grant display rights. |
| `map:ground_stations` [Satellite ground stations](https://www.wikidata.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [mixed-osm-wikidata](#policy-mixed-osm-wikidata) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:military_source_index` Military infrastructure source register (per-item) | terms unverified; per_item_required; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:nasa_gibs_daily` [NASA GIBS daily imagery](https://www.earthdata.nasa.gov/gibs) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | off_until_selected; Map imagery overlay choice (off by default); no licence acknowledgement | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:natural_earth_countries` [Country outlines](https://www.naturalearthdata.com/) | [terms/evidence](https://www.naturalearthdata.com/about/terms-of-use/); terms_checked; 2026-10-09 | conditional / conditional | [natural-earth](#policy-natural-earth) | available_asset; No source-specific prerequisite recorded | low; keep; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:nuclear_facilities` [Nuclear facilities](https://raw.githubusercontent.com/wri/global-power-plant-database/7a91cfbb2a4e272597acbc00506d61fc1ec73b3d/output_database/global_power_plant_database.csv) | [terms/evidence](https://github.com/wri/global-power-plant-database); terms_checked; 2026-10-09 | conditional / conditional | [wri-power](#policy-wri-power); [wikidata-structured](#policy-wikidata-structured) | available_asset; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. Packaged records include Wikidata entity/fact enrichment. Preserve that provenance separately from the base dataset or OSM geometry and do not clear linked media through CC0. |
| `map:openfreemap` [OpenFreeMap vector base maps](https://openfreemap.org/) | [terms/evidence](https://openfreemap.org/); terms_checked; 2026-10-09 | conditional / conditional | [openfreemap](#policy-openfreemap) | initial_hybrid_labels; Basemap choice; no credential required | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:photon_places` [Photon place search](https://photon.komoot.io) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [osm-service](#policy-osm-service) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:semiconductor_sites` [Semiconductor sites](https://www.openstreetmap.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [mixed-osm-wikidata](#policy-mixed-osm-wikidata) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Review the combined OSM, Wikidata and curated-record provenance; retain each applicable notice. |
| `map:submarine_cables` [Submarine cables](https://www.openstreetmap.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); terms_checked; 2026-10-09 | conditional / conditional | [osm](#policy-osm); [wikidata-structured](#policy-wikidata-structured) | available_asset; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. Packaged records include Wikidata entity/fact enrichment. Preserve that provenance separately from the base dataset or OSM geometry and do not clear linked media through CC0. |
| `map:terrain_elevation` [Terrain elevation tiles](https://github.com/tilezen/joerd/blob/master/docs/attribution.md) | [terms/evidence](https://github.com/tilezen/joerd/blob/master/docs/attribution.md); partial_review; 2026-10-09 | unknown / unknown | [tilezen-terrain](#policy-tilezen-terrain) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:valhalla_routing` [Valhalla routing](https://valhalla1.openstreetmap.de) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [osm-service](#policy-osm-service) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Mastodon

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `mastodon_defcon_social` [Mastodon hashtags (defcon.social)](https://defcon.social/) | [attempted page](https://defcon.social/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [defcon-social](#policy-defcon-social) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mastodon_eupolicy_social` [Mastodon hashtags (eupolicy.social)](https://eupolicy.social/) | [attempted page](https://eupolicy.social/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [eupolicy-social](#policy-eupolicy-social) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mastodon_journa_host` [Mastodon hashtags (journa.host)](https://journa.host/) | [attempted page](https://journa.host/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [journa-host](#policy-journa-host) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mastodon_mastodon_social` [Mastodon hashtags (mastodon.social)](https://mastodon.social/) | [attempted page](https://mastodon.social/terms-of-service); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [mastodon-social](#policy-mastodon-social) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## On demand or reference

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `cloudflare_radar_attack_trends` [Cloudflare Radar attack distributions](https://radar.cloudflare.com/security/application-layer) | [terms/evidence](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN | high; request_permission, legal_review; Token-only path: research non-commercial acknowledgement does not cover this path. Review permission before hosted/commercial use. |
| `economic-ecb` [ECB currency reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) | [terms/evidence](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mitre_attack` [MITRE ATT&CK actor reference](https://attack.mitre.org/groups/) | [terms/evidence](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/); terms_checked; 2026-10-09 | conditional / conditional | [mitre](#policy-mitre) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-aiddata-projects` [AidData Chinese development projects](https://www.aiddata.org/) | [attempted page](https://www.aiddata.org/datasets); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [aiddata](#policy-aiddata) | off_until_configured; ASE_AIDDATA_CATALOGUE_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-asset-register` Packaged infrastructure registers (per-item) | terms unverified; per_item_required; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-certificate-transparency` [SSLMate certificate-transparency records](https://sslmate.com/ct_search_api/) | [attempted page](https://sslmate.com/ct_search_api/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [sslmate](#policy-sslmate) | off_until_configured; ASE_CERTIFICATE_TRANSPARENCY_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-cloudflare-radar-layer3` [Cloudflare Radar layer3 target distribution](https://radar.cloudflare.com/) | [terms/evidence](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN and ASE_CLOUDFLARE_RADAR_NONCOMMERCIAL_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-cloudflare-radar-layer7` [Cloudflare Radar layer7 target distribution](https://radar.cloudflare.com/) | [terms/evidence](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN and ASE_CLOUDFLARE_RADAR_NONCOMMERCIAL_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-companies-house` [Companies House](https://developer.company-information.service.gov.uk/) | [attempted page](https://developer.company-information.service.gov.uk/overview); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [companies-house](#policy-companies-house) | off_until_configured; ASE_COMPANIES_HOUSE_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-companies-house-officers` [Companies House officers](https://developer.company-information.service.gov.uk/) | [attempted page](https://developer.company-information.service.gov.uk/overview); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [companies-house](#policy-companies-house) | off_until_configured; ASE_COMPANIES_HOUSE_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-companies-house-psc` [Companies House persons with significant control](https://developer.company-information.service.gov.uk/) | [attempted page](https://developer.company-information.service.gov.uk/overview); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [companies-house](#policy-companies-house) | off_until_configured; ASE_COMPANIES_HOUSE_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-contracts-finder` [Contracts Finder publication notices](https://www.contractsfinder.service.gov.uk/) | [attempted page](https://www.contractsfinder.service.gov.uk/TermsAndConditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [contracts-finder](#policy-contracts-finder) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-copernicus-footprints` [Copernicus satellite footprints](https://dataspace.copernicus.eu/) | [terms/evidence](https://dataspace.copernicus.eu/terms-and-conditions); partial_review; 2026-10-09 | unknown / unknown | [copernicus](#policy-copernicus) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-crossref` [Crossref scholarly metadata](https://www.crossref.org/) | [terms/evidence](https://www.crossref.org/services/metadata-retrieval/); terms_checked; 2026-10-09 | conditional / conditional | [crossref](#policy-crossref) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-eu_fsf` [EU financial sanctions imported snapshot](https://data.europa.eu/) | [terms/evidence](https://data.europa.eu/en/legal-notice); partial_review; 2026-10-09 | unknown / unknown | [eu-sanctions](#policy-eu-sanctions) | off_until_configured; ASE_EU_FSF_SNAPSHOT_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-ofac_sdn` [OFAC SDN imported snapshot](https://ofac.treasury.gov/) | [attempted page](https://ofac.treasury.gov/faqs/topic/1641); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [ofac](#policy-ofac) | off_until_configured; ASE_OFAC_SDN_SNAPSHOT_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-uksl` [UK Sanctions List imported snapshot](https://www.gov.uk/government/publications/the-uk-sanctions-list) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | off_until_configured; ASE_UKSL_SNAPSHOT_PATH | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-un_sc` [UN Security Council imported snapshot](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list) | [attempted page](https://www.un.org/en/about-us/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [un-web](#policy-un-web) | off_until_configured; ASE_UN_SC_SNAPSHOT_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-a` [Google Public DNS A records](https://developers.google.com/speed/public-dns/docs/doh) | [terms/evidence](https://developers.google.com/speed/public-dns/terms); partial_review; 2026-10-09 | unknown / unknown | [google-dns](#policy-google-dns) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-aaaa` [Google Public DNS AAAA records](https://developers.google.com/speed/public-dns/docs/doh) | [terms/evidence](https://developers.google.com/speed/public-dns/terms); partial_review; 2026-10-09 | unknown / unknown | [google-dns](#policy-google-dns) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-mx` [Google Public DNS MX records](https://developers.google.com/speed/public-dns/docs/doh) | [terms/evidence](https://developers.google.com/speed/public-dns/terms); partial_review; 2026-10-09 | unknown / unknown | [google-dns](#policy-google-dns) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-ns` [Google Public DNS NS records](https://developers.google.com/speed/public-dns/docs/doh) | [terms/evidence](https://developers.google.com/speed/public-dns/terms); partial_review; 2026-10-09 | unknown / unknown | [google-dns](#policy-google-dns) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ecb-gbp-reference-rate` [ECB GBP per EUR daily reference rates](https://www.ecb.europa.eu/) | [terms/evidence](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-eonet-area` [NASA EONET area hazard search](https://eonet.gsfc.nasa.gov/) | [terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-gleif-direct-parent` [GLEIF direct parent](https://www.gleif.org/) | [terms/evidence](https://www.gleif.org/en/meta/lei-data-terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [gleif](#policy-gleif) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-gleif-profile` [GLEIF legal entity profile](https://www.gleif.org/) | [terms/evidence](https://www.gleif.org/en/meta/lei-data-terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [gleif](#policy-gleif) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-gleif-ultimate-parent` [GLEIF ultimate parent](https://www.gleif.org/) | [terms/evidence](https://www.gleif.org/en/meta/lei-data-terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [gleif](#policy-gleif) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-hapi-food-security` [HDX HAPI food-security](https://hapi.humdata.org/) | [attempted page](https://hapi.humdata.org/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [hapi](#policy-hapi) | off_until_configured; ASE_HAPI_APP_IDENTIFIER | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-hapi-idps` [HDX HAPI idps](https://hapi.humdata.org/) | [attempted page](https://hapi.humdata.org/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [hapi](#policy-hapi) | off_until_configured; ASE_HAPI_APP_IDENTIFIER | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-hapi-operational-presence` [HDX HAPI operational-presence](https://hapi.humdata.org/) | [attempted page](https://hapi.humdata.org/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [hapi](#policy-hapi) | off_until_configured; ASE_HAPI_APP_IDENTIFIER | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ioda-outage-events` [IODA country outage event windows](https://ioda.inetintel.cc.gatech.edu/) | [attempted page](https://ioda.inetintel.cc.gatech.edu/resources); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [ioda](#policy-ioda) | off_until_configured; ASE_IODA_PUBLIC_DATA_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ons-cpih` [ONS UK CPIH monthly observations](https://www.ons.gov.uk/) | [terms/evidence](https://www.ons.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ons](#policy-ons) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ooni-aggregate` [OONI country connectivity aggregates](https://ooni.org/) | [terms/evidence](https://github.com/ooni/license/blob/master/data/LICENSE.md); terms_checked; 2026-10-09 | permission_required / permission_required | [ooni](#policy-ooni) | off_until_configured; ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-openalex` [OpenAlex scholarly metadata](https://openalex.org/) | [terms/evidence](https://help.openalex.org/access/overview/); terms_checked; 2026-10-09 | conditional / conditional | [openalex](#policy-openalex) | on_demand; ASE_OPENALEX_API_KEY | medium; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-openaq-area` [OpenAQ area air-quality observations](https://openaq.org/) | [terms/evidence](https://docs.openaq.org/about/terms); partial_review; 2026-10-09 | unknown / unknown | [openaq](#policy-openaq) | off_until_configured; ASE_OPENAQ_API_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-osm-features` [OpenStreetMap feature search](https://www.openstreetmap.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [osm-service](#policy-osm-service) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-rdap` [Verisign domain registry RDAP](https://www.iana.org/rdap) | [attempted page](https://www.iana.org/rdap); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [rdap](#policy-rdap) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-retained-area-feeds` Retained public feeds (per-item) | terms unverified; per_item_required; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-sec-company-directory` [SEC company identity candidates](https://www.sec.gov/) | [terms/evidence](https://www.sec.gov/about/privacy-information); partial_review; 2026-10-09 | unknown / unknown | [sec](#policy-sec) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-sec-submissions` [SEC EDGAR submissions](https://www.sec.gov/) | [terms/evidence](https://www.sec.gov/about/privacy-information); partial_review; 2026-10-09 | unknown / unknown | [sec](#policy-sec) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-uk-parliament` [UK Parliament written questions](https://www.parliament.uk/) | [terms/evidence](https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/); terms_checked; 2026-10-09 | conditional / conditional | [parliament](#policy-parliament) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-usgs-area` [USGS area earthquake search](https://earthquake.usgs.gov/) | [terms/evidence](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits); partial_review; 2026-10-09 | conditional / conditional | [usgs](#policy-usgs) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-web-search` [Fresh web search](https://platform.openai.com/docs/guides/tools-web-search) | [terms/evidence](https://openai.com/policies/services-agreement/); partial_review; 2026-10-09 | unknown / unknown | [openai-search](#policy-openai-search) | on_demand; model | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-world-bank` [World Bank annual indicators](https://data.worldbank.org/) | [terms/evidence](https://data.worldbank.org/summary-terms-of-use); partial_review; 2026-10-09 | conditional / conditional | [world-bank](#policy-world-bank) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-youtube` [YouTube video search](https://www.youtube.com/) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ar` [Google News research (ar)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_de` [Google News research (de)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_en` [Google News research (en)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_es` [Google News research (es)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_fr` [Google News research (fr)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_hi` [Google News research (hi)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ja` [Google News research (ja)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ko` [Google News research (ko)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_pt` [Google News research (pt)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ru` [Google News research (ru)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_uk` [Google News research (uk)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_zh-cn` [Google News research (zh-cn)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_zh-tw` [Google News research (zh-tw)](https://news.google.com/) | [terms/evidence](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_import` Private document import (per-item) | terms unverified; per_item_required; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_media` Private image and video import (per-item) | terms unverified; per_item_required; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; ASE_RESEARCH_TESSERACT_PATH, ASE_RESEARCH_FFMPEG_PATH and ASE_RESEARCH_FFPROBE_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_aljazeera_en` [Al Jazeera English](https://www.aljazeera.com/) | [terms/evidence](https://www.aljazeera.com/terms-and-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [aljazeera](#policy-aljazeera) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_anadolu_en` [Anadolu Agency English](https://www.aa.com.tr/en) | [terms/evidence](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_bbc_world` [BBC News World](https://www.bbc.co.uk/news/world) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_bellingcat` [Bellingcat](https://www.bellingcat.com/) | [attempted page](https://www.bellingcat.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [bellingcat](#policy-bellingcat) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cgtn_china` [CGTN China](https://www.cgtn.com/china) | [terms/evidence](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_crisis_group` [International Crisis Group](https://www.crisisgroup.org/) | [attempted page](https://www.crisisgroup.org/legal); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [crisisgroup](#policy-crisisgroup) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_acsc_advisories` [Australia ACSC advisories](https://www.cyber.gov.au/about-us/view-all-content/advisories) | [terms/evidence](https://www.cyber.gov.au/copyright); terms_checked; 2026-10-09 | conditional / conditional | [acsc](#policy-acsc) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_bleeping_computer` [BleepingComputer security news](https://www.bleepingcomputer.com/) | [terms/evidence](https://www.bleepingcomputer.com/terms-of-use/); terms_checked; 2026-10-09 | permission_required / permission_required | [bleepingcomputer](#policy-bleepingcomputer) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cccs_alerts` [Canadian Centre for Cyber Security alerts and advisories](https://www.cyber.gc.ca/en/alerts-advisories) | [attempted page](https://www.cyber.gc.ca/en/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cccs](#policy-cccs) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cert_eu` [CERT-EU threat intelligence](https://cert.europa.eu/publications/threat-intelligence) | [terms/evidence](https://cert.europa.eu/legal-notice); terms_checked; 2026-10-09 | conditional / conditional | [cert-eu](#policy-cert-eu) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cert_fr` [CERT-FR alerts and advisories](https://www.cert.ssi.gouv.fr/) | [terms/evidence](https://www.cert.ssi.gouv.fr/mentions-legales/); terms_checked; 2026-10-09 | conditional / conditional | [cert-fr](#policy-cert-fr) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cert_ua` [CERT-UA incident and threat reports](https://cert.gov.ua/) | [attempted page](https://cert.gov.ua/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [cert-ua](#policy-cert-ua) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cisa_advisories` [US CISA cybersecurity and ICS advisories](https://www.cisa.gov/news-events/cybersecurity-advisories) | [attempted page](https://www.cisa.gov/about/website-policies); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cisa](#policy-cisa) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cisco_talos` [Cisco Talos threat intelligence](https://blog.talosintelligence.com/) | [attempted page](https://blog.talosintelligence.com/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [talos](#policy-talos) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_google_threat_intelligence` [Google Threat Intelligence and Mandiant](https://cloud.google.com/blog/topics/threat-intelligence) | [attempted page](https://cloud.google.com/blog/topics/threat-intelligence); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [google-threat-blog](#policy-google-threat-blog) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_ic3_psa` [FBI IC3 public service announcements](https://www.ic3.gov/PSA) | [terms/evidence](https://www.ic3.gov/Home/Privacy); terms_checked; 2026-10-09 | conditional / conditional | [ic3](#policy-ic3) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_microsoft_threat_intelligence` [Microsoft Threat Intelligence](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/) | [terms/evidence](https://www.microsoft.com/en-us/legal/terms-of-use); partial_review; 2026-10-09 | permission_required / permission_required | [microsoft-web](#policy-microsoft-web) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_ncsc_news` [UK NCSC news and threat statements](https://www.ncsc.gov.uk/section/keep-up-to-date/news) | [terms/evidence](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_ncsc_reports` [UK NCSC threat reports](https://www.ncsc.gov.uk/section/keep-up-to-date/threat-reports) | [terms/evidence](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_sans_isc` [SANS Internet Storm Center diaries](https://isc.sans.edu/) | [attempted page](https://isc.sans.edu/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [sans-isc](#policy-sans-isc) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_the_record` [The Record from Recorded Future News](https://therecord.media/) | [attempted page](https://therecord.media/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [record](#policy-record) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_unit42` [Palo Alto Networks Unit 42 research](https://unit42.paloaltonetworks.com/) | [terms/evidence](https://www.paloaltonetworks.com/legal-notices/terms-of-use); partial_review; 2026-10-09 | permission_required / permission_required | [paloalto](#policy-paloalto) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_dawn` [Dawn](https://www.dawn.com/) | [terms/evidence](https://www.dawn.com/terms/); terms_checked; 2026-10-09 | permission_required / permission_required | [dawn](#policy-dawn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_dw_world` [DW World](https://www.dw.com/en/) | [terms/evidence](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_canada` [Bank of Canada press releases](https://www.bankofcanada.ca/press/press-releases/) | [terms/evidence](https://www.bankofcanada.ca/terms/); terms_checked; 2026-10-09 | conditional / conditional | [bank-canada](#policy-bank-canada) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_england` [Bank of England news](https://www.bankofengland.co.uk/news) | [terms/evidence](https://www.bankofengland.co.uk/legal); terms_checked; 2026-10-09 | permission_required / permission_required | [bank-england](#policy-bank-england) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_japan` [Bank of Japan releases](https://www.boj.or.jp/en/) | [terms/evidence](https://www.boj.or.jp/en/copyright.htm); terms_checked; 2026-10-09 | permission_required / permission_required | [bank-japan](#policy-bank-japan) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_russia` [Bank of Russia press releases](https://www.cbr.ru/eng/press/) | [terms/evidence](https://www.cbr.ru/eng/about/); terms_checked; 2026-10-09 | conditional / conditional | [bank-russia](#policy-bank-russia) | on_demand; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bbc_business` [BBC Business](https://www.bbc.com/business) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bis_speeches` [BIS central bankers' speeches](https://www.bis.org/cbspeeches/) | [terms/evidence](https://www.bis.org/about/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [bis](#policy-bis) | on_demand; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bls_consumer_prices` [BLS consumer price index](https://www.bls.gov/cpi/) | [terms/evidence](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bls_employment` [BLS employment situation](https://www.bls.gov/ces/) | [terms/evidence](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bls_producer_prices` [BLS producer price index](https://www.bls.gov/ppi/) | [terms/evidence](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_census_indicators` [US Census economic indicators](https://www.census.gov/economic-indicators/) | [attempted page](https://www.census.gov/about/policies/copyright.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [census](#policy-census) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_cgtn_business` [CGTN Business](https://www.cgtn.com/business) | [terms/evidence](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_dw_business` [DW Business](https://www.dw.com/en/business/s-1431) | [terms/evidence](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_ecb_press` [European Central Bank press releases](https://www.ecb.europa.eu/press/html/index.en.html) | [terms/evidence](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_economist_finance` [The Economist finance and economics](https://www.economist.com/finance-and-economics) | [terms/evidence](https://www.economist.com/syndication/permissions); partial_review; 2026-10-09 | permission_required / permission_required | [economist](#policy-economist) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_eia_energy` [EIA Today in Energy](https://www.eia.gov/todayinenergy/) | [terms/evidence](https://www.eia.gov/about/copyrights_reuse.php); terms_checked; 2026-10-09 | conditional / conditional | [eia](#policy-eia) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_federal_reserve` [Federal Reserve press releases](https://www.federalreserve.gov/newsevents/pressreleases.htm) | [terms/evidence](https://www.federalreserve.gov/disclaimer.htm); terms_checked; 2026-10-09 | conditional / conditional | [federal-reserve](#policy-federal-reserve) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_france24_business` [France 24 Business](https://www.france24.com/en/business/) | [attempted page](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_guardian_business` [The Guardian business](https://www.theguardian.com/business) | [terms/evidence](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_hm_treasury` [HM Treasury announcements](https://www.gov.uk/government/organisations/hm-treasury) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_intellinews` [bne IntelliNews](https://www.intellinews.com/) | [attempted page](https://www.intellinews.com/terms/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [intellinews](#policy-intellinews) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_ons_releases` [ONS statistical releases](https://www.ons.gov.uk/releasecalendar) | [terms/evidence](https://www.ons.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ons](#policy-ons) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_reserve_bank_india` [Reserve Bank of India press releases](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx) | [terms/evidence](https://www.rbi.org.in/Scripts/Disclaimer.aspx); partial_review; 2026-10-09 | permission_required / permission_required | [rbi](#policy-rbi) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_scmp_china` [SCMP China economy](https://www.scmp.com/economy/china-economy) | [terms/evidence](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_tehran_times` [Tehran Times economy](https://www.tehrantimes.com/service/economy) | [attempted page](https://www.tehrantimes.com/page/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [tehran-times](#policy-tehran-times) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_the_bell` [The Bell](https://en.thebell.io/) | [terms/evidence](https://en.thebell.io/terms-of-service/); partial_review; 2026-10-09 | unknown / unknown | [the-bell](#policy-the-bell) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_wto_news` [WTO latest news](https://www.wto.org/english/news_e/news_e.htm) | [attempted page](https://www.wto.org/english/res_e/copyright_e.htm); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [wto](#policy-wto) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_france24_en` [France 24 English](https://www.france24.com/en/) | [attempted page](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_fcdo_news` [GOV.UK FCDO news](https://www.gov.uk/government/organisations/foreign-commonwealth-development-office) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_home_office` [GOV.UK Home Office news](https://www.gov.uk/government/organisations/home-office) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_mod_news` [GOV.UK Ministry of Defence news](https://www.gov.uk/government/organisations/ministry-of-defence) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_number_10` [GOV.UK Prime Minister's Office news](https://www.gov.uk/government/organisations/prime-ministers-office-10-downing-street) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_travel_advice` [GOV.UK foreign travel advice](https://www.gov.uk/foreign-travel-advice) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_guardian_world` [The Guardian World](https://www.theguardian.com/world) | [terms/evidence](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_kyiv_independent` [The Kyiv Independent](https://kyivindependent.com/) | [attempted page](https://kyivindependent.com/terms-of-use/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [kyiv-independent](#policy-kyiv-independent) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_lemonde_en` [Le Monde in English](https://www.lemonde.fr/en/) | [terms/evidence](https://www.lemonde.fr/en/about-us/article/2026/03/27/le-monde-rss-feeds_6751860_115.html); terms_checked; 2026-10-09 | permission_required / permission_required | [lemonde](#policy-lemonde) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_meduza_en` [Meduza in English](https://meduza.io/en) | [attempted page](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_nikkei_asia` [Nikkei Asia](https://asia.nikkei.com/) | [terms/evidence](https://info.asia.nikkei.com/rss); terms_checked; 2026-10-09 | permission_required / permission_required | [nikkei](#policy-nikkei) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_pravda_ua_en` [Ukrainska Pravda in English](https://www.pravda.com.ua/eng/) | [terms/evidence](https://www.pravda.com.ua/eng/rules/); terms_checked; 2026-10-09 | permission_required / permission_required | [pravda](#policy-pravda) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_reliefweb_updates` [ReliefWeb updates](https://reliefweb.int/) | [attempted page](https://reliefweb.int/terms-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [reliefweb](#policy-reliefweb) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_russia_mfa_ru` [Russian MFA news (Russian)](https://mid.ru/ru/) | [attempted page](https://mid.ru/ru/about/copyright/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [russia-mfa](#policy-russia-mfa) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_scmp_news` [South China Morning Post](https://www.scmp.com/) | [terms/evidence](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_tass_en` [TASS English](https://tass.com/) | [terms/evidence](https://tass.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [tass](#policy-tass) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_times_of_israel` [The Times of Israel](https://www.timesofisrael.com/) | [terms/evidence](https://www.timesofisrael.com/terms/); terms_checked; 2026-10-09 | permission_required / permission_required | [times-israel](#policy-times-israel) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_un_news` [UN News](https://news.un.org/) | [attempted page](https://www.un.org/en/about-us/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [un-web](#policy-un-web) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_un_press` [UN press releases and meetings coverage](https://press.un.org/) | [attempted page](https://www.un.org/en/about-us/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [un-web](#policy-un-web) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_us_dod_news` [US Department of Defense news](https://www.defense.gov/News/) | [attempted page](https://www.defense.gov/Resources/DOD-Imagery/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [us-dod](#policy-us-dod) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_us_state_travel_advisories` [US State Department travel advisories](https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html) | [terms/evidence](https://travel.state.gov/content/travel/en/copyright-disclaimer.html); terms_checked; 2026-10-09 | conditional / conditional | [state-travel](#policy-state-travel) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_whitehouse_news` [White House news](https://www.whitehouse.gov/news/) | [terms/evidence](https://www.whitehouse.gov/copyright/); terms_checked; 2026-10-09 | conditional / conditional | [whitehouse](#policy-whitehouse) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_anadolu_ar` [Anadolu Agency Arabic](https://www.aa.com.tr/ar) | [terms/evidence](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_afrique` [BBC News Afrique](https://www.bbc.com/afrique) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_arabic` [BBC News Arabic](https://www.bbc.com/arabic) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_hausa` [BBC News Hausa](https://www.bbc.com/hausa) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_hindi` [BBC News Hindi](https://www.bbc.com/hindi) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_japanese` [BBC News Japanese](https://www.bbc.com/japanese) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_korean` [BBC News Korean](https://www.bbc.com/korean) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_swahili` [BBC News Swahili](https://www.bbc.com/swahili) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_urdu` [BBC News Urdu](https://www.bbc.com/urdu) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_belta_ru` [BelTA in Russian](https://belta.by/) | [attempted page](https://belta.by/about/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [belta](#policy-belta) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_cdt_zh` [China Digital Times in Chinese](https://chinadigitaltimes.net/chinese/) | [attempted page](https://chinadigitaltimes.net/copyright/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cdt](#policy-cdt) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_deutschlandfunk_de` [Deutschlandfunk Nachrichten](https://www.deutschlandfunk.de/) | [terms/evidence](https://www.deutschlandfunk.de/nutzungsbedingungen-102.html); terms_checked; 2026-10-09 | permission_required / permission_required | [deutschlandfunk](#policy-deutschlandfunk) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_express_urdu` [Express News Urdu](https://www.express.pk/) | [attempted page](https://www.express.pk/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [express-urdu](#policy-express-urdu) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_hrana_en` [HRANA in English](https://www.en-hrana.org/) | [attempted page](https://www.en-hrana.org/about-us/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [hrana-en](#policy-hrana-en) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_hrana_fa` [HRANA in Persian](https://www.hra-news.org/) | [attempted page](https://www.hra-news.org/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [hrana-fa](#policy-hrana-fa) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_insider_ru` [The Insider in Russian](https://theins.ru/) | [attempted page](https://theins.ru/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [insider](#policy-insider) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_interfax_ru` [Interfax in Russian](https://www.interfax.ru/) | [terms/evidence](https://www.interfax.ru/license); terms_checked; 2026-10-09 | permission_required / permission_required | [interfax](#policy-interfax) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_iranwire_en` [IranWire in English](https://iranwire.com/en/) | [terms/evidence](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_iranwire_fa` [IranWire in Persian](https://iranwire.com/fa/) | [terms/evidence](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_maariv_he` [Maariv Hebrew](https://www.maariv.co.il/) | [attempted page](https://www.maariv.co.il/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [maariv](#policy-maariv) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_mediazona_ru` [Mediazona in Russian](https://zona.media/) | [attempted page](https://zona.media/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [mediazona](#policy-mediazona) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_meduza_ru` [Meduza in Russian](https://meduza.io/) | [attempted page](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_ndtv_hindi` [NDTV India Hindi](https://ndtv.in/) | [terms/evidence](https://drop.ndtv.com/ndtv/common/NDTV-ServiceTerms.pdf); partial_review; 2026-10-09 | permission_required / permission_required | [ndtv](#policy-ndtv) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_radio_okapi_fr` [Radio Okapi French](https://www.radiookapi.net/) | [attempted page](https://www.radiookapi.net/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [radio-okapi](#policy-radio-okapi) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_trt_haber_tr` [TRT Haber Turkish](https://www.trthaber.com/) | [attempted page](https://www.trthaber.com/kurumsal/kullanim-kosullari.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [trt](#policy-trt) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_ukrinform_en` [Ukrinform in English](https://www.ukrinform.net/) | [attempted page](https://www.ukrinform.net/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ukrinform](#policy-ukrinform) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_social_bluesky` [Bluesky curated accounts research](https://bsky.social/) | [terms/evidence](https://bsky.social/about/support/tos); partial_review; 2026-10-09 | unknown / unknown | [bluesky](#policy-bluesky) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_social_telegram` [Curated Telegram channels](https://telegram.org/) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | on_demand; No source-specific prerequisite recorded | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Reference dataset

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `reference:conflicts` Conflict and tension areas (per-item) | terms unverified; per_item_required; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reference:entities` [Ship and aircraft reference](https://www.wikidata.org/) | [terms/evidence](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [mixed-osm-wikidata](#policy-mixed-osm-wikidata) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reference:public_figures` [Public figures](https://www.wikidata.org/) | [terms/evidence](https://www.wikidata.org/wiki/Wikidata:Licensing); partial_review; 2026-10-09 | unknown / unknown | [wikidata-mixed](#policy-wikidata-mixed) | available_asset; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Rss

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `aljazeera_en` [Al Jazeera English](https://www.aljazeera.com/) | [terms/evidence](https://www.aljazeera.com/terms-and-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [aljazeera](#policy-aljazeera) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `anadolu_ar` [Anadolu Agency Arabic](https://www.aa.com.tr/ar) | [terms/evidence](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `anadolu_en` [Anadolu Agency English](https://www.aa.com.tr/en) | [terms/evidence](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_afrique` [BBC News Afrique](https://www.bbc.com/afrique) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_arabic` [BBC News Arabic](https://www.bbc.com/arabic) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_hausa` [BBC News Hausa](https://www.bbc.com/hausa) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_hindi` [BBC News Hindi](https://www.bbc.com/hindi) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_japanese` [BBC News Japanese](https://www.bbc.com/japanese) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_korean` [BBC News Korean](https://www.bbc.com/korean) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_swahili` [BBC News Swahili](https://www.bbc.com/swahili) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_urdu` [BBC News Urdu](https://www.bbc.com/urdu) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_world` [BBC News World](https://www.bbc.co.uk/news/world) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bellingcat` [Bellingcat](https://www.bellingcat.com/) | [attempted page](https://www.bellingcat.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [bellingcat](#policy-bellingcat) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `belta_ru` [BelTA in Russian](https://belta.by/) | [attempted page](https://belta.by/about/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [belta](#policy-belta) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cdt_zh` [China Digital Times in Chinese](https://chinadigitaltimes.net/chinese/) | [attempted page](https://chinadigitaltimes.net/copyright/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cdt](#policy-cdt) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cgtn_china` [CGTN China](https://www.cgtn.com/china) | [terms/evidence](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `crisis_group` [International Crisis Group](https://www.crisisgroup.org/) | [attempted page](https://www.crisisgroup.org/legal); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [crisisgroup](#policy-crisisgroup) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_acsc_advisories` [Australia ACSC advisories](https://www.cyber.gov.au/about-us/view-all-content/advisories) | [terms/evidence](https://www.cyber.gov.au/copyright); terms_checked; 2026-10-09 | conditional / conditional | [acsc](#policy-acsc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_bleeping_computer` [BleepingComputer security news](https://www.bleepingcomputer.com/) | [terms/evidence](https://www.bleepingcomputer.com/terms-of-use/); terms_checked; 2026-10-09 | permission_required / permission_required | [bleepingcomputer](#policy-bleepingcomputer) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cccs_alerts` [Canadian Centre for Cyber Security alerts and advisories](https://www.cyber.gc.ca/en/alerts-advisories) | [attempted page](https://www.cyber.gc.ca/en/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cccs](#policy-cccs) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cert_eu` [CERT-EU threat intelligence](https://cert.europa.eu/publications/threat-intelligence) | [terms/evidence](https://cert.europa.eu/legal-notice); terms_checked; 2026-10-09 | conditional / conditional | [cert-eu](#policy-cert-eu) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cert_fr` [CERT-FR alerts and advisories](https://www.cert.ssi.gouv.fr/) | [terms/evidence](https://www.cert.ssi.gouv.fr/mentions-legales/); terms_checked; 2026-10-09 | conditional / conditional | [cert-fr](#policy-cert-fr) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cert_ua` [CERT-UA incident and threat reports](https://cert.gov.ua/) | [attempted page](https://cert.gov.ua/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [cert-ua](#policy-cert-ua) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cisa_advisories` [US CISA cybersecurity and ICS advisories](https://www.cisa.gov/news-events/cybersecurity-advisories) | [attempted page](https://www.cisa.gov/about/website-policies); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cisa](#policy-cisa) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cisco_talos` [Cisco Talos threat intelligence](https://blog.talosintelligence.com/) | [attempted page](https://blog.talosintelligence.com/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [talos](#policy-talos) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_google_threat_intelligence` [Google Threat Intelligence and Mandiant](https://cloud.google.com/blog/topics/threat-intelligence) | [attempted page](https://cloud.google.com/blog/topics/threat-intelligence); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [google-threat-blog](#policy-google-threat-blog) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_ic3_psa` [FBI IC3 public service announcements](https://www.ic3.gov/PSA) | [terms/evidence](https://www.ic3.gov/Home/Privacy); terms_checked; 2026-10-09 | conditional / conditional | [ic3](#policy-ic3) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_microsoft_threat_intelligence` [Microsoft Threat Intelligence](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/) | [terms/evidence](https://www.microsoft.com/en-us/legal/terms-of-use); partial_review; 2026-10-09 | permission_required / permission_required | [microsoft-web](#policy-microsoft-web) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_ncsc_news` [UK NCSC news and threat statements](https://www.ncsc.gov.uk/section/keep-up-to-date/news) | [terms/evidence](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_ncsc_reports` [UK NCSC threat reports](https://www.ncsc.gov.uk/section/keep-up-to-date/threat-reports) | [terms/evidence](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_sans_isc` [SANS Internet Storm Center diaries](https://isc.sans.edu/) | [attempted page](https://isc.sans.edu/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [sans-isc](#policy-sans-isc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_the_record` [The Record from Recorded Future News](https://therecord.media/) | [attempted page](https://therecord.media/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [record](#policy-record) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_unit42` [Palo Alto Networks Unit 42 research](https://unit42.paloaltonetworks.com/) | [terms/evidence](https://www.paloaltonetworks.com/legal-notices/terms-of-use); partial_review; 2026-10-09 | permission_required / permission_required | [paloalto](#policy-paloalto) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `dawn` [Dawn](https://www.dawn.com/) | [terms/evidence](https://www.dawn.com/terms/); terms_checked; 2026-10-09 | permission_required / permission_required | [dawn](#policy-dawn) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `deutschlandfunk_de` [Deutschlandfunk Nachrichten](https://www.deutschlandfunk.de/) | [terms/evidence](https://www.deutschlandfunk.de/nutzungsbedingungen-102.html); terms_checked; 2026-10-09 | permission_required / permission_required | [deutschlandfunk](#policy-deutschlandfunk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `dw_world` [DW World](https://www.dw.com/en/) | [terms/evidence](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_canada` [Bank of Canada press releases](https://www.bankofcanada.ca/press/press-releases/) | [terms/evidence](https://www.bankofcanada.ca/terms/); terms_checked; 2026-10-09 | conditional / conditional | [bank-canada](#policy-bank-canada) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_england` [Bank of England news](https://www.bankofengland.co.uk/news) | [terms/evidence](https://www.bankofengland.co.uk/legal); terms_checked; 2026-10-09 | permission_required / permission_required | [bank-england](#policy-bank-england) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_japan` [Bank of Japan releases](https://www.boj.or.jp/en/) | [terms/evidence](https://www.boj.or.jp/en/copyright.htm); terms_checked; 2026-10-09 | permission_required / permission_required | [bank-japan](#policy-bank-japan) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_russia` [Bank of Russia press releases](https://www.cbr.ru/eng/press/) | [terms/evidence](https://www.cbr.ru/eng/about/); terms_checked; 2026-10-09 | conditional / conditional | [bank-russia](#policy-bank-russia) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bbc_business` [BBC Business](https://www.bbc.com/business) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bis_speeches` [BIS central bankers' speeches](https://www.bis.org/cbspeeches/) | [terms/evidence](https://www.bis.org/about/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [bis](#policy-bis) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bls_consumer_prices` [BLS consumer price index](https://www.bls.gov/cpi/) | [terms/evidence](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bls_employment` [BLS employment situation](https://www.bls.gov/ces/) | [terms/evidence](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bls_producer_prices` [BLS producer price index](https://www.bls.gov/ppi/) | [terms/evidence](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_census_indicators` [US Census economic indicators](https://www.census.gov/economic-indicators/) | [attempted page](https://www.census.gov/about/policies/copyright.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [census](#policy-census) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_cgtn_business` [CGTN Business](https://www.cgtn.com/business) | [terms/evidence](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_dw_business` [DW Business](https://www.dw.com/en/business/s-1431) | [terms/evidence](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_ecb_press` [European Central Bank press releases](https://www.ecb.europa.eu/press/html/index.en.html) | [terms/evidence](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_economist_finance` [The Economist finance and economics](https://www.economist.com/finance-and-economics) | [terms/evidence](https://www.economist.com/syndication/permissions); partial_review; 2026-10-09 | permission_required / permission_required | [economist](#policy-economist) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_eia_energy` [EIA Today in Energy](https://www.eia.gov/todayinenergy/) | [terms/evidence](https://www.eia.gov/about/copyrights_reuse.php); terms_checked; 2026-10-09 | conditional / conditional | [eia](#policy-eia) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_federal_reserve` [Federal Reserve press releases](https://www.federalreserve.gov/newsevents/pressreleases.htm) | [terms/evidence](https://www.federalreserve.gov/disclaimer.htm); terms_checked; 2026-10-09 | conditional / conditional | [federal-reserve](#policy-federal-reserve) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_france24_business` [France 24 Business](https://www.france24.com/en/business/) | [attempted page](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_guardian_business` [The Guardian business](https://www.theguardian.com/business) | [terms/evidence](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_hm_treasury` [HM Treasury announcements](https://www.gov.uk/government/organisations/hm-treasury) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_intellinews` [bne IntelliNews](https://www.intellinews.com/) | [attempted page](https://www.intellinews.com/terms/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [intellinews](#policy-intellinews) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_ons_releases` [ONS statistical releases](https://www.ons.gov.uk/releasecalendar) | [terms/evidence](https://www.ons.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ons](#policy-ons) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_reserve_bank_india` [Reserve Bank of India press releases](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx) | [terms/evidence](https://www.rbi.org.in/Scripts/Disclaimer.aspx); partial_review; 2026-10-09 | permission_required / permission_required | [rbi](#policy-rbi) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_scmp_china` [SCMP China economy](https://www.scmp.com/economy/china-economy) | [terms/evidence](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_tehran_times` [Tehran Times economy](https://www.tehrantimes.com/service/economy) | [attempted page](https://www.tehrantimes.com/page/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [tehran-times](#policy-tehran-times) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_the_bell` [The Bell](https://en.thebell.io/) | [terms/evidence](https://en.thebell.io/terms-of-service/); partial_review; 2026-10-09 | unknown / unknown | [the-bell](#policy-the-bell) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_wto_news` [WTO latest news](https://www.wto.org/english/news_e/news_e.htm) | [attempted page](https://www.wto.org/english/res_e/copyright_e.htm); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [wto](#policy-wto) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `express_urdu` [Express News Urdu](https://www.express.pk/) | [attempted page](https://www.express.pk/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [express-urdu](#policy-express-urdu) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `france24_en` [France 24 English](https://www.france24.com/en/) | [attempted page](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_fcdo_news` [GOV.UK FCDO news](https://www.gov.uk/government/organisations/foreign-commonwealth-development-office) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_home_office` [GOV.UK Home Office news](https://www.gov.uk/government/organisations/home-office) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_mod_news` [GOV.UK Ministry of Defence news](https://www.gov.uk/government/organisations/ministry-of-defence) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_number_10` [GOV.UK Prime Minister's Office news](https://www.gov.uk/government/organisations/prime-ministers-office-10-downing-street) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_travel_advice` [GOV.UK foreign travel advice](https://www.gov.uk/foreign-travel-advice) | [terms/evidence](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `guardian_world` [The Guardian World](https://www.theguardian.com/world) | [terms/evidence](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `hrana_en` [HRANA in English](https://www.en-hrana.org/) | [attempted page](https://www.en-hrana.org/about-us/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [hrana-en](#policy-hrana-en) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `hrana_fa` [HRANA in Persian](https://www.hra-news.org/) | [attempted page](https://www.hra-news.org/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [hrana-fa](#policy-hrana-fa) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `insider_ru` [The Insider in Russian](https://theins.ru/) | [attempted page](https://theins.ru/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [insider](#policy-insider) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `interfax_ru` [Interfax in Russian](https://www.interfax.ru/) | [terms/evidence](https://www.interfax.ru/license); terms_checked; 2026-10-09 | permission_required / permission_required | [interfax](#policy-interfax) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `iranwire_en` [IranWire in English](https://iranwire.com/en/) | [terms/evidence](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `iranwire_fa` [IranWire in Persian](https://iranwire.com/fa/) | [terms/evidence](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `kyiv_independent` [The Kyiv Independent](https://kyivindependent.com/) | [attempted page](https://kyivindependent.com/terms-of-use/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [kyiv-independent](#policy-kyiv-independent) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `lemonde_en` [Le Monde in English](https://www.lemonde.fr/en/) | [terms/evidence](https://www.lemonde.fr/en/about-us/article/2026/03/27/le-monde-rss-feeds_6751860_115.html); terms_checked; 2026-10-09 | permission_required / permission_required | [lemonde](#policy-lemonde) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `maariv_he` [Maariv Hebrew](https://www.maariv.co.il/) | [attempted page](https://www.maariv.co.il/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [maariv](#policy-maariv) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mediazona_ru` [Mediazona in Russian](https://zona.media/) | [attempted page](https://zona.media/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [mediazona](#policy-mediazona) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `meduza_en` [Meduza in English](https://meduza.io/en) | [attempted page](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `meduza_ru` [Meduza in Russian](https://meduza.io/) | [attempted page](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ndtv_hindi` [NDTV India Hindi](https://ndtv.in/) | [terms/evidence](https://drop.ndtv.com/ndtv/common/NDTV-ServiceTerms.pdf); partial_review; 2026-10-09 | permission_required / permission_required | [ndtv](#policy-ndtv) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_abc_australia` [ABC News Australia](https://www.abc.net.au/news/) | [terms/evidence](https://help.abc.net.au/hc/en-us/articles/360001548096-ABC-Terms-of-Use); terms_checked; 2026-10-09 | permission_required / permission_required | [abc-australia](#policy-abc-australia) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_abc_us_international` [ABC News International](https://abcnews.go.com/International) | [attempted page](https://abcnews.go.com/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [abc-us](#policy-abc-us) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_africanews` [Africanews](https://www.africanews.com/) | [terms/evidence](https://www.euronews.com/terms-and-conditions/); terms_checked; 2026-10-09 | permission_required / permission_required | [euronews](#policy-euronews) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_agencia_brasil_en` [Agência Brasil English](https://agenciabrasil.ebc.com.br/en) | [attempted page](https://agenciabrasil.ebc.com.br/en); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [agencia-brasil](#policy-agencia-brasil) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_antara_en` [ANTARA News English](https://en.antaranews.com/) | [attempted page](https://en.antaranews.com/copyright); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [antara](#policy-antara) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_arab_news` [Arab News](https://www.arabnews.com/) | [terms/evidence](https://www.arabnews.com/node/51204); terms_checked; 2026-10-09 | permission_required / permission_required | [arab-news](#policy-arab-news) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bangkok_post` [Bangkok Post](https://www.bangkokpost.com/) | [attempted page](https://www.bangkokpost.com/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [bangkok-post](#policy-bangkok-post) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_batimes` [Buenos Aires Times](https://www.batimes.com.ar/) | [attempted page](https://www.batimes.com.ar/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [batimes](#policy-batimes) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_northern_ireland` [BBC News Northern Ireland](https://www.bbc.co.uk/news/northern_ireland) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_scotland` [BBC News Scotland](https://www.bbc.co.uk/news/scotland) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_uk` [BBC News UK](https://www.bbc.co.uk/news/uk) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_wales` [BBC News Wales](https://www.bbc.co.uk/news/wales) | [terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_belfast_live` [BelfastLive](https://www.belfastlive.co.uk/news/) | [attempted page](https://www.belfastlive.co.uk/terms-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [belfast-live](#policy-belfast-live) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_birmingham_live` [BirminghamLive](https://www.birminghammail.co.uk/news/) | [attempted page](https://www.birminghammail.co.uk/terms-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [birmingham-live](#policy-birmingham-live) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_cbc_canada` [CBC News top stories](https://www.cbc.ca/news) | [attempted page](https://www.cbc.ca/aboutus/termsofuse.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cbc](#policy-cbc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_cbs_world` [CBS News World](https://www.cbsnews.com/world/) | [attempted page](https://www.paramount.com/legal/us/en/cbsi/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [cbs](#policy-cbs) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_cna_asia` [CNA Asia](https://www.channelnewsasia.com/asia) | [terms/evidence](https://www.channelnewsasia.com/rss/rssterms); terms_checked; 2026-10-09 | permission_required / permission_required | [cna-rss](#policy-cna-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_el_pais` [El País Spanish](https://elpais.com/) | [attempted page](https://www.elpais.com/estaticos/aviso-legal/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [elpais](#policy-elpais) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_euronews` [Euronews](https://www.euronews.com/) | [terms/evidence](https://www.euronews.com/terms-and-conditions/); terms_checked; 2026-10-09 | permission_required / permission_required | [euronews](#policy-euronews) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_france24_ar` [France 24 Arabic](https://www.france24.com/ar/) | [attempted page](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_guardian_uk` [The Guardian UK news](https://www.theguardian.com/uk-news) | [terms/evidence](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_herald_scotland` [The Herald Scotland](https://www.heraldscotland.com/) | [attempted page](https://www.heraldscotland.com/terms/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [herald-scotland](#policy-herald-scotland) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_hindustan_times` [Hindustan Times India](https://www.hindustantimes.com/india-news) | [terms/evidence](https://www.hindustantimes.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [hindustan-times](#policy-hindustan-times) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_independent_uk` [The Independent UK](https://www.independent.co.uk/news/uk) | [terms/evidence](https://www.independent.co.uk/service/rss-feeds-775086.html); terms_checked; 2026-10-09 | permission_required / permission_required | [independent-rss](#policy-independent-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_indian_express` [The Indian Express](https://indianexpress.com/) | [terms/evidence](https://indianexpress.com/terms-and-conditions/); terms_checked; 2026-10-09 | permission_required / permission_required | [indian-express](#policy-indian-express) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_infobae` [Infobae](https://www.infobae.com/) | [terms/evidence](https://www.infobae.com/terminos-y-condiciones/); terms_checked; 2026-10-09 | permission_required / permission_required | [infobae](#policy-infobae) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_insight_crime` [InSight Crime](https://insightcrime.org/) | [attempted page](https://insightcrime.org/about-us/republishing-guidelines/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [insightcrime](#policy-insightcrime) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_japan_times` [The Japan Times](https://www.japantimes.co.jp/) | [attempted page](https://www.japantimes.co.jp/terms-of-service/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [japan-times](#policy-japan-times) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_manchester_evening` [Manchester Evening News](https://www.manchestereveningnews.co.uk/news/) | [attempted page](https://www.manchestereveningnews.co.uk/terms-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [reach-manchester](#policy-reach-manchester) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_mercopress` [MercoPress](https://en.mercopress.com/) | [attempted page](https://www.mercopress.com/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [mercopress](#policy-mercopress) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_mexico_news_daily` [Mexico News Daily](https://mexiconewsdaily.com/) | [attempted page](https://mexiconewsdaily.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [mexico-news](#policy-mexico-news) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_middle_east_eye` [Middle East Eye](https://www.middleeasteye.net/) | [attempted page](https://www.middleeasteye.net/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [middle-east-eye](#policy-middle-east-eye) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_myjoyonline` [MyJoyOnline Ghana](https://www.myjoyonline.com/) | [attempted page](https://www.myjoyonline.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [myjoyonline](#policy-myjoyonline) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_nation_kenya` [Nation Kenya](https://nation.africa/kenya) | [attempted page](https://nation.africa/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [nation](#policy-nation) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_newsroom_nz` [Newsroom New Zealand](https://newsroom.co.nz/) | [attempted page](https://newsroom.co.nz/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [newsroom](#policy-newsroom) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_northern_echo` [The Northern Echo](https://www.thenorthernecho.co.uk/news/) | [attempted page](https://www.thenorthernecho.co.uk/terms/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [northern-echo](#policy-northern-echo) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_npr_world` [NPR World](https://www.npr.org/sections/world/) | [attempted page](https://www.npr.org/about-npr/179876898/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [npr](#policy-npr) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_nytimes_world` [The New York Times World](https://www.nytimes.com/section/world) | [attempted page](https://www.nytimes.com/content/help/rights/terms/terms-of-service.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [nytimes](#policy-nytimes) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_oc_media` [OC Media](https://oc-media.org/) | [attempted page](https://oc-media.org/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [oc-media](#policy-oc-media) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_pbs_news` [PBS News headlines](https://www.pbs.org/newshour/) | [attempted page](https://www.pbs.org/about/about-pbs/terms-of-use/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [pbs](#policy-pbs) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_premium_times` [Premium Times Nigeria](https://www.premiumtimesng.com/) | [attempted page](https://www.premiumtimesng.com/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [premium-times](#policy-premium-times) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_publico_pt` [Público Portugal](https://www.publico.pt/) | [attempted page](https://www.publico.pt/termos-e-condicoes); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [publico](#policy-publico) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_radio_dabanga` [Radio Dabanga](https://www.dabangasudan.org/en) | [attempted page](https://www.dabangasudan.org/en/about-us); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [dabanga](#policy-dabanga) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_rappler` [Rappler](https://www.rappler.com/) | [attempted page](https://www.rappler.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [rappler](#policy-rappler) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_rfi_en` [RFI English](https://www.rfi.fr/en/) | [attempted page](https://www.rfi.fr/en/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [rfi](#policy-rfi) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_rfi_fr` [RFI French](https://www.rfi.fr/fr/) | [attempted page](https://www.rfi.fr/en/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [rfi](#policy-rfi) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_sabc_news` [SABC News](https://www.sabcnews.com/sabcnews/) | [attempted page](https://www.sabcnews.com/sabcnews/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [sabc](#policy-sabc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_sky_uk` [Sky News UK](https://news.sky.com/uk) | [attempted page](https://news.sky.com/info/policies-and-standards/terms-and-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [sky](#policy-sky) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_stv_scotland` [STV News Scotland](https://news.stv.tv/) | [attempted page](https://news.stv.tv/terms-of-use); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [stv](#policy-stv) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_the_diplomat` [The Diplomat](https://thediplomat.com/) | [attempted page](https://thediplomat.com/terms-of-use/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [diplomat](#policy-diplomat) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_the_national_uae` [The National UAE](https://www.thenationalnews.com/) | [terms/evidence](https://www.thenationalnews.com/terms-and-conditions/); terms_checked; 2026-10-09 | permission_required / permission_required | [national-uae](#policy-national-uae) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_times_central_asia` [The Times of Central Asia](https://timesca.com/) | [attempted page](https://timesca.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [timesca](#policy-timesca) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_wales_online` [WalesOnline](https://www.walesonline.co.uk/news/) | [attempted page](https://www.walesonline.co.uk/terms-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [wales-online](#policy-wales-online) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nikkei_asia` [Nikkei Asia](https://asia.nikkei.com/) | [terms/evidence](https://info.asia.nikkei.com/rss); terms_checked; 2026-10-09 | permission_required / permission_required | [nikkei](#policy-nikkei) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `pravda_ua_en` [Ukrainska Pravda in English](https://www.pravda.com.ua/eng/) | [terms/evidence](https://www.pravda.com.ua/eng/rules/); terms_checked; 2026-10-09 | permission_required / permission_required | [pravda](#policy-pravda) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `radio_okapi_fr` [Radio Okapi French](https://www.radiookapi.net/) | [attempted page](https://www.radiookapi.net/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [radio-okapi](#policy-radio-okapi) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reliefweb_updates` [ReliefWeb updates](https://reliefweb.int/) | [attempted page](https://reliefweb.int/terms-conditions); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [reliefweb](#policy-reliefweb) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `russia_mfa_ru` [Russian MFA news (Russian)](https://mid.ru/ru/) | [attempted page](https://mid.ru/ru/about/copyright/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [russia-mfa](#policy-russia-mfa) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `scmp_news` [South China Morning Post](https://www.scmp.com/) | [terms/evidence](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `tass_en` [TASS English](https://tass.com/) | [terms/evidence](https://tass.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [tass](#policy-tass) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `times_of_israel` [The Times of Israel](https://www.timesofisrael.com/) | [terms/evidence](https://www.timesofisrael.com/terms/); terms_checked; 2026-10-09 | permission_required / permission_required | [times-israel](#policy-times-israel) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `trt_haber_tr` [TRT Haber Turkish](https://www.trthaber.com/) | [attempted page](https://www.trthaber.com/kurumsal/kullanim-kosullari.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [trt](#policy-trt) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukrinform_en` [Ukrinform in English](https://www.ukrinform.net/) | [attempted page](https://www.ukrinform.net/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ukrinform](#policy-ukrinform) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `un_news` [UN News](https://news.un.org/) | [attempted page](https://www.un.org/en/about-us/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [un-web](#policy-un-web) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `un_press` [UN press releases and meetings coverage](https://press.un.org/) | [attempted page](https://www.un.org/en/about-us/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [un-web](#policy-un-web) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `us_dod_news` [US Department of Defense news](https://www.defense.gov/News/) | [attempted page](https://www.defense.gov/Resources/DOD-Imagery/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [us-dod](#policy-us-dod) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `us_state_travel_advisories` [US State Department travel advisories](https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html) | [terms/evidence](https://travel.state.gov/content/travel/en/copyright-disclaimer.html); terms_checked; 2026-10-09 | conditional / conditional | [state-travel](#policy-state-travel) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `whitehouse_news` [White House news](https://www.whitehouse.gov/news/) | [terms/evidence](https://www.whitehouse.gov/copyright/); terms_checked; 2026-10-09 | conditional / conditional | [whitehouse](#policy-whitehouse) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Telegram

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `telegram_agentstvonews` [Agentstvo (Telegram)](https://t.me/agentstvonews) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_astrapress` [ASTRA (Telegram)](https://t.me/astrapress) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_bazabazon` [Baza (Telegram)](https://t.me/bazabazon) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_bleepingcomputer` [BleepingComputer (Telegram)](https://t.me/BleepingComputer) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_bloomberg` [Bloomberg (Telegram)](https://t.me/bloomberg) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_boris_rozhin` [Colonelcassad (Telegram)](https://t.me/boris_rozhin) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_centralbank_russia` [Bank of Russia (Telegram)](https://t.me/centralbank_russia) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_deepstateua` [DeepState (Telegram)](https://t.me/DeepStateUA) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_dsns_telegram` [State Emergency Service of Ukraine (Telegram)](https://t.me/dsns_telegram) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_dva_majors` [Dva Majora (Telegram)](https://t.me/dva_majors) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_epoddubny` [Yevgeny Poddubny (Telegram)](https://t.me/epoddubny) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_generalstaffzsu` [General Staff of the Armed Forces of Ukraine (Telegram)](https://t.me/generalstaffZSU) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_idfofficial` [Israel Defense Forces (Telegram)](https://t.me/idfofficial) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_intelslava` [Intel Slava Z (Telegram)](https://t.me/intelslava) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_irna_1313` [IRNA (Telegram)](https://t.me/irna_1313) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_israelwarroom` [Israel War Room (Telegram)](https://t.me/IsraelWarRoom) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_izvestia` [Izvestia (Telegram)](https://t.me/izvestia) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_kommersant` [Kommersant (Telegram)](https://t.me/kommersant) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_kpszsu` [Air Force Command of the Armed Forces of Ukraine (Telegram)](https://t.me/kpszsu) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_kyivindependent_official` [The Kyiv Independent (Telegram)](https://t.me/kyivindependent_official) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mali_actu` [Mali Actu (Telegram)](https://t.me/Mali_Actu) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mchs_official` [EMERCOM of Russia (Telegram)](https://t.me/mchs_official) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mediazzzona` [Mediazona (Telegram)](https://t.me/mediazzzona) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_meduzalive` [Meduza (Telegram)](https://t.me/meduzalive) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mfarussia` [Russian MFA (English) (Telegram)](https://t.me/MFARussia) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mid_russia` [Russian Ministry of Foreign Affairs (Telegram)](https://t.me/MID_Russia) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_milinfolive` [Voenny Osvedomitel (Telegram)](https://t.me/milinfolive) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mod_russia` [Russian Ministry of Defence (Telegram)](https://t.me/mod_russia) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mod_russia_en` [Russian Ministry of Defence (English) (Telegram)](https://t.me/mod_russia_en) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mvs_ukraine` [Ministry of Internal Affairs of Ukraine (Telegram)](https://t.me/mvs_ukraine) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_nbu_ua` [National Bank of Ukraine (Telegram)](https://t.me/nbu_ua) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_nexta_live` [NEXTA (Telegram)](https://t.me/nexta_live) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_nvua_official` [NV (Telegram)](https://t.me/nvua_official) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_operativnozsu` [Operatyvno ZSU (Telegram)](https://t.me/operativnoZSU) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_osintdefender` [OSINTdefender (Telegram)](https://t.me/OSINTdefender) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ostorozhno_novosti` [Ostorozhno Novosti (Telegram)](https://t.me/ostorozhno_novosti) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_pravda_gerashchenko` [Anton Gerashchenko (Telegram)](https://t.me/Pravda_Gerashchenko) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_presstv` [Press TV (Telegram)](https://t.me/PressTV) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_qudsnen` [Quds News Network (Telegram)](https://t.me/QudsNen) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_radiosvoboda` [Radio Svoboda (Telegram)](https://t.me/radiosvoboda) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rbc_news` [RBC (Telegram)](https://t.me/rbc_news) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_readovkanews` [Readovka (Telegram)](https://t.me/readovkanews) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_redpacketsecurity` [RedPacket Security (Telegram)](https://t.me/RedPacketSecurity) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rian_ru` [RIA Novosti (Telegram)](https://t.me/rian_ru) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rvvoenkor` [Rusvesna war correspondents (Telegram)](https://t.me/RVvoenkor) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rybar` [Rybar (Telegram)](https://t.me/rybar) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_sashakots` [Kotsnews (Telegram)](https://t.me/sashakots) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_scmpnews` [South China Morning Post (Telegram)](https://t.me/scmpnews) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_shot_shot` [SHOT (Telegram)](https://t.me/shot_shot) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_solovievlive` [Vladimir Solovyov (Telegram)](https://t.me/SolovievLive) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_suspilnenews` [Suspilne News (Telegram)](https://t.me/suspilnenews) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_tass_agency` [TASS (Telegram)](https://t.me/tass_agency) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_thehackernews` [The Hacker News (Telegram)](https://t.me/thehackernews) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_tsaplienko` [Andriy Tsaplienko (Telegram)](https://t.me/Tsaplienko) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrainenow` [Ukraine NOW (Telegram)](https://t.me/UkraineNow) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrenergo` [Ukrenergo (Telegram)](https://t.me/ukrenergo) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrinform_news` [Ukrinform (Telegram)](https://t.me/ukrinform_news) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrpravda_news` [Ukrainska Pravda (Telegram)](https://t.me/ukrpravda_news) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_united24media` [UNITED24 Media (Telegram)](https://t.me/United24media) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_v_zelenskiy_official` [Volodymyr Zelenskyy (Telegram)](https://t.me/V_Zelenskiy_official) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_voenkorkotenok` [Yuri Kotenok (Telegram)](https://t.me/voenkorKotenok) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_vxunderground` [vx-underground (Telegram)](https://t.me/vxunderground) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_wargonzo` [WarGonzo (Telegram)](https://t.me/wargonzo) | [terms/evidence](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Ukraine dataset

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `ukraine:deepstate` [DeepStateMap frontline](https://deepstatemap.live/) | [terms/evidence](https://deepstatemap.live/license.html); terms_checked; 2026-10-09 | permission_required / permission_required | [deepstate](#policy-deepstate) | off_until_configured; ASE_UKRAINE_DEEPSTATE_ACCESS | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:hrmmu_casualties` [Civilian casualty reports](https://ukraine.ohchr.org/en/reports/protection-of-civilians) | [attempted page](https://www.un.org/en/about-us/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [un-web](#policy-un-web) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:oblast_outlines` [Oblast outlines](https://www.geoboundaries.org/) | [terms/evidence](https://www.geoboundaries.org/index.html); terms_checked; 2026-10-09 | conditional / conditional | [geoboundaries](#policy-geoboundaries) | available_asset; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:ocha_frontline` [OCHA humanitarian frontline](https://gis.unocha.org/) | [attempted page](https://gis.unocha.org/server/rest/services/Hosted/UKR_Front_Line/FeatureServer/info/iteminfo); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ocha-frontline](#policy-ocha-frontline) | off_until_configured; ASE_UKRAINE_OCHA_HUMANITARIAN | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:oryx_losses` [Visually confirmed equipment losses](https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html) | [attempted page](https://www.oryxspioenkop.com/); lookup_inconclusive; attempt 2026-10-09 | unknown / unknown | [oryx](#policy-oryx) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:reference_catalogue` [Equipment, forces and timeline notes](https://www.wikidata.org/) | [terms/evidence](https://www.wikidata.org/wiki/Wikidata:Licensing); partial_review; 2026-10-09 | unknown / unknown | [wikidata-mixed](#policy-wikidata-mixed) | available_asset; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:viina_control` [VIINA territorial control](https://github.com/zhukovyuri/VIINA) | [terms/evidence](https://github.com/zhukovyuri/VIINA); terms_checked; 2026-10-09 | conditional / conditional | [viina](#policy-viina) | available_asset; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:warspotting` [WarSpotting geolocated losses](https://ukr.warspotting.net/) | [terms/evidence](https://ukr.warspotting.net/about/); terms_checked; 2026-10-09 | permission_required / permission_required | [warspotting](#policy-warspotting) | off_until_configured; ASE_UKRAINE_WARSPOTTING | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Youtube

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `yt_al_jazeera` [Al Jazeera English (YouTube)](https://www.youtube.com/@AlJazeeraEnglish) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_ap` [Associated Press (YouTube)](https://www.youtube.com/@AssociatedPress) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_bbc_news` [BBC News (YouTube)](https://www.youtube.com/@BBCNews) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_black_hat` [Black Hat (YouTube)](https://www.youtube.com/@BlackHatOfficialYT) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_cgtn` [CGTN (YouTube)](https://www.youtube.com/@CGTN) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_chatham_house` [Chatham House (YouTube)](https://www.youtube.com/@ChathamHouse) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_cnbc` [CNBC (YouTube)](https://www.youtube.com/@CNBC) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_defcon` [DEF CON (YouTube)](https://www.youtube.com/@DEFCONConference) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_dw_news` [DW News (YouTube)](https://www.youtube.com/@dwnews) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_economist` [The Economist (YouTube)](https://www.youtube.com/@TheEconomist) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_euronews` [euronews (YouTube)](https://www.youtube.com/@euronews) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_european_commission` [European Commission (YouTube)](https://www.youtube.com/@EuropeanCommission) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_financial_times` [Financial Times (YouTube)](https://www.youtube.com/@FinancialTimes) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_france24` [FRANCE 24 English (YouTube)](https://www.youtube.com/@FRANCE24English) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_guardian` [The Guardian (YouTube)](https://www.youtube.com/@guardiannews) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_kyiv_independent` [The Kyiv Independent (YouTube)](https://www.youtube.com/@kyivindependent) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_meduza` [Meduza (YouTube)](https://www.youtube.com/@meduzalive) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_middle_east_eye` [Middle East Eye (YouTube)](https://www.youtube.com/@MiddleEastEye) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_nato` [NATO (YouTube)](https://www.youtube.com/@NATO) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_number_10` [Number10gov (YouTube)](https://www.youtube.com/@10DowningStreet) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_pbs_newshour` [PBS NewsHour (YouTube)](https://www.youtube.com/@PBSNewsHour) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_perun` [Perun (YouTube)](https://www.youtube.com/@PerunAU) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_reuters` [Reuters (YouTube)](https://www.youtube.com/@Reuters) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_scmp` [South China Morning Post (YouTube)](https://www.youtube.com/@SouthChinaMorningPost) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_sky_news` [Sky News (YouTube)](https://www.youtube.com/@SkyNews) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_taiwan_plus` [TaiwanPlus News (YouTube)](https://www.youtube.com/@TaiwanPlusNews) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_united_nations` [United Nations (YouTube)](https://www.youtube.com/@unitednations) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_war_on_the_rocks` [War on the Rocks (YouTube)](https://www.youtube.com/@WarontheRocks) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_white_house` [The White House (YouTube)](https://www.youtube.com/@WhiteHouse) | [terms/evidence](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Supplementary sources

These are reviewed historical/candidate providers, not extra active catalogue entries.

| Provider | Status | Policy |
| --- | --- | --- |
| adsb-fi | not_in_current_backend_catalogue | [adsb-fi](#policy-adsb-fi) |
| reddit | not_in_current_backend_catalogue | [reddit](#policy-reddit) |
| open-meteo | not_in_current_backend_catalogue | [open-meteo](#policy-open-meteo) |
| global-fishing-watch | not_in_current_backend_catalogue | [gfw](#policy-gfw) |
| opensanctions | not_in_current_backend_catalogue | [opensanctions](#policy-opensanctions) |

## Policy details

Policy text is shared to keep repeated source rows consistent. Inspect each exact product and deployment before relying on it.

### Policy abc-australia

**ABC Australia**: Personal non-commercial; written permission otherwise.

[Primary terms/evidence](https://help.abc.net.au/hc/en-us/articles/360001548096-ABC-Terms-of-Use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain copyright/trade marks and avoid implied endorsement.

Redistribution: No project-specific onward-sharing or export grant established.

July 2026 terms reserve ABC and licensor rights. Reproduction, republication, adaptation and translation beyond specific service exceptions require prior written permission. Library Sales is the content permission route.

Risk: high. Action: request_permission, legal_review.

### Policy abc-us

**ABC News US**: Terms not verified.

[Attempted page](https://abcnews.go.com/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

RSS/terms search did not establish the current publisher licence; candidate terms route failed. Do not apply Australian ABC terms.

Risk: high. Action: request_permission, legal_review.

### Policy acled

**ACLED event data**: Eligibility and licence-specific EULA.

[Primary terms/evidence](https://acleddata.com/eula). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Prominent ACLED credit, access date, data scope and changes, including visualisations.

Redistribution: Raw sharing restricted. Non-commercial external outputs must be transformative and prevent dataset reconstruction; a dashboard alone is insufficient.

Corporate/public-sector and third-party-service permissions require the appropriate agreement. Account/API entitlement is not redistribution permission.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://acleddata.com/contentusage); [reference 2](https://acleddata.com/attributionpolicy). These links are not separate verification dates.

### Policy acsc

**Australian Cyber Security Centre**: CC BY 4.0, except specified material.

[Primary terms/evidence](https://www.cyber.gov.au/copyright). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit Australian Signals Directorate and Commonwealth of Australia with the publication year and licence.

Redistribution: Covered material may be reused under CC BY 4.0; obtain separate third-party permissions.

January 2026 reviewed policy excludes coat of arms, logos, third-party content and specifically excluded material.

Risk: high. Action: attribute, legal_review.

### Policy adsb-fi

**adsb.fi open data**: Personal, non-commercial terms.

[Primary terms/evidence](https://github.com/adsbfi/opendata/blob/main/README.md). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Cite adsb.fi and link its home page.

Redistribution: No licensing, sale, rental or lease of the data/service under the public terms.

Commercial enquiries are invited. Current aviation code uses adsb.lol instead; do not confuse the providers or assume personal use covers team hosting.

Risk: high. Action: request_permission, legal_review.

### Policy adsb-lol

**ADSB.lol API data**: ODbL 1.0.

[Primary terms/evidence](https://www.adsb.lol/docs/open-data/api/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit ADSB.lol and ODbL; preserve database notices.

Redistribution: ODbL attribution/share-alike and derivative-database obligations apply.

The API page specifies ODbL. Its separate contributor CC0 grant is not a replacement API-output licence. Review derived databases and publication; no availability guarantee.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://opendatacommons.org/licenses/odbl/1-0/); [reference 2](https://www.adsb.lol/privacy-license/). These links are not separate verification dates.

### Policy agencia-brasil

**Agencia Brasil**: Applicable reuse grant not located.

[Attempted page](https://agenciabrasil.ebc.com.br/en). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official homepage has a reserved-rights footer; targeted search did not establish applicable English-feed reuse terms.

Risk: high. Action: request_permission, legal_review.

### Policy aiddata

**AidData projects**: Applicable reuse grant not located.

[Attempted page](https://www.aiddata.org/datasets). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Dataset catalogue inspected after candidate terms route failed. Exact project dataset/version licence and upstream documents remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy aisstream

**AISstream**: Hosted architecture documented; commercial data grant unresolved.

[Primary terms/evidence](https://www.aisstream.io/documentation). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: Confirm commercial and retained/exported data rights; direct browser connections are prohibited.

Official documentation supports a backend proxy supplying needed client information and operational persistence. It limits connections and subscription changes. These service directions do not establish a general commercial redistribution licence or attribution rule.

Risk: high. Action: request_permission, legal_review.

### Policy aljazeera

**Al Jazeera**: Restricted.

[Primary terms/evidence](https://www.aljazeera.com/terms-and-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source credit.

Redistribution: Commercial reuse and automated collection need permission.

Review section 6.

Risk: high. Action: request_permission, legal_review.

### Policy anadolu

**Anadolu Agency**: Subscription agreement required.

[Primary terms/evidence](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official Turkish notice requires website publisher subscription and restricts use and transfer outside the contract; no project subscription or onward-use scope established.

Risk: high. Action: request_permission, legal_review.

### Policy antara

**ANTARA English**: Terms not verified.

[Attempted page](https://en.antaranews.com/copyright). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Search located copyright notices and syndication references, but candidate copyright page was inaccessible and no endpoint-specific reuse grant established.

Risk: high. Action: request_permission, legal_review.

### Policy arab-news

**Arab News**: Prior written public/commercial reuse permission.

[Primary terms/evidence](https://www.arabnews.com/node/51204). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms restrict public or commercial copying, editing, redistribution and derivative works without written publisher approval; photographs require specific consent. Terms URL redirected to the official backup host.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://backup.arabnews.com/node/51204). These links are not separate verification dates.

### Policy bangkok-post

**Bangkok Post**: Terms not verified.

[Attempted page](https://www.bangkokpost.com/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Targeted official-domain search did not establish reuse terms; candidate terms page was inaccessible.

Risk: high. Action: request_permission, legal_review.

### Policy bank-canada

**Bank of Canada publications**: Conditional website reuse.

[Primary terms/evidence](https://www.bankofcanada.ca/terms/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit Bank, indicate changes, ensure accuracy and avoid endorsement.

Redistribution: Copy/distribute covered content with attribution and advance free-source disclosure for paid use.

Paid service/documents must disclose before sale/distribution that source content is freely available from the Bank. Third-party material, banknote images and logos are excluded.

Risk: medium. Action: keep, attribute, legal_review.

### Policy bank-england

**Bank of England publications**: Personal/internal non-commercial resources; database terms separate.

[Primary terms/evidence](https://www.bankofengland.co.uk/legal). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain Bank and author/source notices; confirm licensed-use credit.

Redistribution: Commercial publication/reuse needs further authorisation; database exceptions are product-specific.

The RSS publications path is not the statistical Database. Its OGL database grant must not be applied to speeches/releases or third-party LSEG data.

Risk: high. Action: request_permission, legal_review.

### Policy bank-japan

**Bank of Japan**: Commercial and image reuse requires permission.

[Primary terms/evidence](https://www.boj.or.jp/en/copyright.htm). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Explicitly credit Bank of Japan; preserve notices.

Redistribution: No commercial/report-hosting grant established without permission.

Text copying with credit is subject to exceptions. Commercial purposes, specified material and image data require advance permission; changes also need approval.

Risk: high. Action: request_permission, legal_review.

### Policy bank-russia

**Bank of Russia**: Reproduction with source link; site-link notification condition.

[Primary terms/evidence](https://www.cbr.ru/eng/about/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Link the precise original webpage as source.

Redistribution: Published material may be reproduced subject to linked attribution and applicable notification conditions.

Official policy permits reproduction on internet servers/media with source reference. Structured site/catalogue hyperlinks require notification to Press Service; review deployment and any separately marked rights.

Risk: medium. Action: attribute, legal_review.

### Policy barentswatch

**BarentsWatch open AIS**: NLOD unless API-specific conditions say otherwise.

[Primary terms/evidence](https://www.barentswatch.no/artikler/api-vilkar/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Display Data delivered by BarentsWatch, link where possible, and credit the data owner.

Redistribution: Open AIS subject to NLOD and exact API conditions; no separate media grant inferred.

November 2023 terms explicitly permit commercial reuse/redistribution with credit. Registration required, no misleading affiliation, and high loads require contact. Special-access data is excluded; retain delivered data contents.

Risk: high. Action: attribute, legal_review.

Related evidence: [reference 1](https://developer.barentswatch.no/docs/AIS/live-ais-api/). These links are not separate verification dates.

### Policy batimes

**Buenos Aires Times**: Terms not verified.

[Attempted page](https://www.batimes.com.ar/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Targeted official-domain search and candidate terms route did not establish applicable reuse rights.

Risk: high. Action: request_permission, legal_review.

### Policy bbc-rss

**BBC RSS**: Current terms lookup blocked; older BBC terms available.

[Primary terms/evidence](https://www.bbc.co.uk/usingthebbc/terms/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Older terms require prominent BBC News name and linked source; preserve embedded branding.

Redistribution: No current commercial or multi-user grant verified; do not treat historical personal-use terms as clearance.

Current page blocked by robots. Official September 2022 PDF section 15 requires permission for business RSS and a metadata licence. Confirm current scope before use.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://downloads.bbc.co.uk/usingthebbc/bbc_terms_of_use_19September2022english.pdf). These links are not separate verification dates.

### Policy belfast-live

**Belfast Live**: Terms not verified.

[Attempted page](https://www.belfastlive.co.uk/terms-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official terms route returned 402; do not automatically substitute another Reach publication policy.

Risk: high. Action: request_permission, legal_review.

### Policy bellingcat

**Bellingcat**: Unverified.

[Attempted page](https://www.bellingcat.com/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms lookup failed. Establish current publication-specific licensing before approving collection, hosted excerpts or exports.

Risk: high. Action: request_permission, legal_review.

### Policy belta

**Belta**: Terms not verified.

[Attempted page](https://belta.by/about/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate about/copyright routes were inaccessible; reuse grant not verified.

Risk: high. Action: request_permission, legal_review.

### Policy birmingham-live

**Birmingham Live**: Terms not verified.

[Attempted page](https://www.birminghammail.co.uk/terms-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official terms route returned 402; exact publication rights remain unverified.

Risk: high. Action: request_permission, legal_review.

### Policy bis

**BIS speeches/publications**: Limited-extract permission; statistics separate.

[Primary terms/evidence](https://www.bis.org/about/terms-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit BIS; translated extracts need non-official translation notice and original link.

Redistribution: Only the bounded extract grant is established for commercial products, not full feed text or unrestricted reports.

Limited non-statistical excerpts in products must stay within 400 words or two tables/graphs and at most 10% of the publication. Other reuse requires permission; third-party speeches need exact provenance review.

Risk: medium. Action: attribute, legal_review.

### Policy bleepingcomputer

**BleepingComputer**: Personal non-commercial access; publication permission.

[Primary terms/evidence](https://www.bleepingcomputer.com/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain copyright, trademark and proprietary notices.

Redistribution: No hosted evidence/export grant verified.

Written permission is required for publication/sale/redistribution. Stored copies outside personal non-commercial use and business use of contributions are restricted.

Risk: high. Action: request_permission, legal_review.

### Policy bls

**US Bureau of Labor Statistics**: Public-domain BLS material; photo/illustration exceptions.

[Primary terms/evidence](https://www.bls.gov/bls/linksite.htm). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite BLS; do not use its emblem without authority.

Redistribution: Covered public-domain statistics may be redistributed; exclude separately copyrighted material.

BLS permits reuse of its public-domain publications; emblem and previously copyrighted images are excluded.

Risk: low. Action: keep, attribute.

### Policy bluesky

**Bluesky user content**: Platform terms; user-owned content.

[Primary terms/evidence](https://bsky.social/about/support/tos). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve author, post URL and platform identity.

Redistribution: Bluesky platform licences do not establish blanket third-party report/export rights.

Review developer terms, deletion propagation and individual author rights; AT Protocol accessibility is not a public-domain dedication.

Risk: high. Action: request_permission, legal_review.

### Policy camera-alaska

**Alaska 511**: Provider-specific camera terms.

[Primary terms/evidence](https://511.alaska.gov/about/disclaimer). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer provides warranties, not an affirmative reuse licence. Keyed developer application access and image URLs do not clear index or pixels.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://511.alaska.gov/developers/doc). These links are not separate verification dates.

### Policy camera-alberta

**Alberta 511**: Non-commercial/educational reproduction; commercial permission.

[Primary terms/evidence](https://511.alberta.ca/about/about). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No commercial grant verified; clarify each camera owner, image rights and credit.

Commercial reproduction/distribution/promotion requires written government permission. Registered API access is not a separate image or redistribution licence.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://511.alberta.ca/developers/doc). These links are not separate verification dates.

### Policy camera-amss

**AMSS Serbia cameras**: Owner/media rights not verified.

[Attempted page](https://www.amss.org.rs/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official provider homepage inspected without an applicable commercial camera reuse grant.

Risk: high. Action: request_permission, legal_review.

### Policy camera-argyll

**Argyll and Bute council**: Owner/media rights not verified.

[Attempted page](https://www.argyll-bute.gov.uk/privacy-and-cookies). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate policy route inaccessible; exact image reuse terms remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-arizona

**Arizona 511**: Provider-specific camera terms.

[Primary terms/evidence](https://azdot.gov/disclaimer). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

ADOT retains distribution rights and warns reproduction may require permission. AZ511 traffic disclaimer adds no grant; obtain scope for hosted indexes/images.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://az511.gov/about/disclaimer). These links are not separate verification dates.

### Policy camera-asfinag

**ASFINAG webcams**: Prior-approved partner integration.

[Primary terms/evidence](https://media.asfinag.at/media/lsgfvnz1/webcam-informationen-durch-webcampartner.pdf). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Identify ASFINAG clearly; credit each broadcast use.

Redistribution: Partner linking grant excludes smartphone applications, favourites services and simultaneous multiple-camera displays without additional agreement.

Current official webcam page still links March 2012 partner and August 2007 general terms. Ordinary use is private. Approved partners may link supplied indexes; broader redistribution and multi-camera views need a separate agreement. Public index access does not clear proxying, copying snapshots or video.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.asfinag.at/verkehr-sicherheit/webcams/); [reference 2](https://media.asfinag.at/media/b3fngdvg/webcam-informationen-nutzungsbedingunge_-august-2007.pdf). These links are not separate verification dates.

### Policy camera-autostrade

**Autostrade Italy**: Provider-specific data/media conditions.

[Attempted page](https://www.autostrade.it/it/home). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Official site readable, legal-page lookup failed. No applicable index, still-image or video reuse grant found.

Risk: high. Action: request_permission, legal_review.

### Policy camera-butler

**Butler Sheriff cameras**: Owner/media rights not verified.

[Attempted page](https://www.butlersheriff.org/terms-of-use/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route inaccessible; public agency ownership is not treated as a footage reuse grant.

Risk: high. Action: request_permission, legal_review.

### Policy camera-caltrans

**Caltrans CWWP2**: Public-domain information with photograph/third-party exceptions.

[Primary terms/evidence](https://dot.ca.gov/conditions-of-use). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: Commercial metadata use supported; actual camera-image/stream rights require confirmation.

CWWP2 targets commercial/media applications and CCTV information; camera-specific documentation retrieval failed. Metadata distribution does not clear every image or stream.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://dot.ca.gov/programs/traffic-operations/traveler-information/cwwp). These links are not separate verification dates.

### Policy camera-camsecure

**Camsecure**: Owner/media rights not verified.

[Attempted page](https://www.camsecure.co/terms-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route inaccessible; streaming supplier is not necessarily camera owner.

Risk: high. Action: request_permission, legal_review.

### Policy camera-carsprogram

**CARS platform delivery**: Owner/media rights not verified.

[Attempted page](https://www.carsprogram.org/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate provider site inaccessible; a shared traffic-platform hostname does not establish agency-specific image rights. public.carsprogram.org is shared by Indiana, Minnesota and Massachusetts adapters; a host-wide licence is not inferred from any one agency programme.

Risk: high. Action: request_permission, legal_review.

### Policy camera-chavo

**Chavo weather camera**: Owner/media rights not verified.

[Attempted page](https://meteo.chavo.biz/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official weather page returned no readable terms. Image/stream reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-chuv

**CHUV camera**: Owner/media rights not verified.

[Attempted page](https://www.chuv.ch/fr/chuv-home/footer/conditions-generales). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route inaccessible; exact image reuse terms remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-connecticut

**Connecticut CTroads**: Provider-specific camera terms.

[Attempted page](https://www.ctroads.com/about/disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer inaccessible. Developer help describes keys, requests and cameras but no verified image/index redistribution licence. Current catalogue ctroads.org and documentation ctroads.com require endpoint correspondence review.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.ctroads.com/developers/help). These links are not separate verification dates.

### Policy camera-derbyshire

**Derbyshire traffic cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.derbyshire.gov.uk/council/performance/open-data/license/licence.aspx). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

General council data policy declares CC0 unless otherwise stated and asks credit, timely updates and short caches. Coverage of photographs on the separate camera application remains unresolved. Camera information describes ten-minute stills.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.derbyshire.gov.uk/transport-roads/roads-traffic/traffic-cameras/traffic-cameras.aspx). These links are not separate verification dates.

### Policy camera-dgt

**DGT camera metadata**: Creative Commons Attribution label; scope/version unresolved.

[Primary terms/evidence](https://nap.dgt.es/es/dataset/camaras-dgt-datex2-v3-7). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official hourly static-road-data catalogue labels camera metadata Creative Commons Attribution without a version. General legal notice indexed restrictions conflict with broad reuse assumptions; direct legal retrieval failed. No snapshot, embed or live-footage grant established.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.dgt.es/contenido/aviso-legal/index.html). These links are not separate verification dates.

### Policy camera-drivebc

**DriveBC HighwayCams**: OGL-BC metadata; current image scope unresolved.

[Primary terms/evidence](https://www2.gov.bc.ca/gov/content/data/policy-standards/data-policies/open-data/open-government-licence-bc). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use OGL-BC attribution for covered records; preserve individual image owners.

Redistribution: Verify present snapshot/partner scope before treating all image URLs as commercially reusable.

Official catalogue/indexed licence support metadata reuse. Historical government API repository says images and data OGL-BC; its draft status does not clear every current partner camera. Current licence fetch returned 502; catalogue rendered a shell.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://catalogue.data.gov.bc.ca/dataset/bc-highwaycams); [reference 2](https://github.com/bcgov/drivebc-webcam-api). These links are not separate verification dates.

### Policy camera-durham

**Durham traffic cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.data.gov.uk/dataset/2c4818e4-3da2-4bdb-a8d9-894d700f889a/https-datamillnorth-org-dataset-2kq9x-traffic-web-cameras). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

October 2024 location-data record specifies OGL; September 2026 successor record has no licence set. Reconcile metadata licences; contractor-hosted image rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.data.gov.uk/dataset/b03d9e6f-d74a-42e0-ba57-179ea0950f3c/traffic-web-cameras). These links are not separate verification dates.

### Policy camera-earthcam

**EarthCam**: Personal viewing/copying; commercial licence.

[Primary terms/evidence](https://www.earthcam.com/company/tos.php). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Authorised social sharing retains watermark and Courtesy of EarthCam credit; other uses need agreed credits.

Redistribution: Commercial reuse, embeds, live rebroadcasts and further redistribution require licensing.

Terms permit one personal non-commercial home copy. Linking policy prohibits live-image embedding and page framing. FAQ distinguishes prescribed social sharing from licensed website/app embeds and rebroadcasting. No directory-data redistribution grant established.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.earthcam.com/site/linktous.php); [reference 2](https://www.earthcam.com/faq.php); [reference 3](https://www.earthcam.com/company/contact.php?query=license). These links are not separate verification dates.

### Policy camera-estonia

**Estonia Tarktee**: Provider-specific data/media conditions.

[Attempted page](https://tarktee.ee/#/en/datex). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Official DATEX/current-service pages returned application shells. No applicable camera metadata/image licence established; third-party licence claims were excluded.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://tarktee.transpordiamet.ee/). These links are not separate verification dates.

### Policy camera-fintraffic

**Fintraffic camera snapshots**: CC BY 4.0 for covered Fintraffic open data.

[Primary terms/evidence](https://www.digitraffic.fi/en/terms-of-service/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit Fintraffic/digitraffic.fi, licence and changes; retain owner notices.

Redistribution: Covered snapshots and metadata may be redistributed under CC BY 4.0.

Fintraffic FAQ expressly permits own-service camera-image embedding via Digitraffic. Applies to supplied snapshots and metadata, not unrelated third-party or live footage.

Risk: medium. Action: attribute, legal_review.

Related evidence: [reference 1](https://www.fintraffic.fi/en/digitalservices/traffic-situation/frequently-asked-questions-about-traffic-situation-service). These links are not separate verification dates.

### Policy camera-florida

**Florida 511**: Provider-specific camera terms.

[Attempted page](https://teo.fdot.gov/architecture/architectures/d5/html/agreements/agreements.html). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official agreement catalogue lists recipient-specific CCTV memoranda/video agreements. Public FL511 viewing is not a blanket grant; obtain applicable FDOT agreement. Candidate disclaimer inaccessible.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://fl511.com/about/disclaimer). These links are not separate verification dates.

### Policy camera-georgia

**Georgia 511**: Provider-specific camera terms.

[Attempted page](https://511ga.org/about/disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer inaccessible. Official indexed developer documentation describes registered access and cameras without a verified reuse grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://511ga.org/developers/doc). These links are not separate verification dates.

### Policy camera-home-solutions

**Home Solutions Bulgaria**: Owner/media rights not verified.

[Attempted page](https://home-solutions.bg/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Provider site returned 403; image/stream reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-hongkong

**Hong Kong traffic snapshots**: DATA.GOV.HK terms v1.2.

[Primary terms/evidence](https://data.gov.hk/en/terms-and-conditions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Identify Transport Department, DATA.GOV.HK and relevant owner.

Redistribution: Designated open snapshots may be reused under dataset terms; no blanket live-video/third-party grant.

Terms include photographs and commercial distribution. Official indexed snapshot dataset reviewed; direct dataset fetch timed out. Confirm the catalogue tis_1 endpoint against the reviewed tis_2 dataset and image owners.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://data.gov.hk/en-data/dataset/hk-td-tis_2-traffic-snapshot-images). These links are not separate verification dates.

### Policy camera-hungary

**Hungary Utinform**: Provider-specific data/media conditions.

[Attempted page](https://www.utinform.hu/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Service required JavaScript. Official operator announcements identify Slovenian and Austrian camera integration, so underlying owner rights vary. No commercial reuse grant verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://internet.kozut.hu/2022/11/04/mar-a-szloven-forgalomfigyelo-kamerak-kepei-is-elerhetok-az-utinform-weboldalan/); [reference 2](https://internet.kozut.hu/2023/04/13/mar-az-osztrak-forgalomfigyelo-kamerak-kepei-is-elerhetok-az-utinform-weboldalan/). These links are not separate verification dates.

### Policy camera-iceland

**Vegagerdin data and photographs**: CC BY 4.0 for covered data and photographs.

[Primary terms/evidence](https://www.vegagerdin.is/vegagerdin/gagnasafn/vefthjonustur/skilmalar-vefthjonustur). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit Vegagerdin, dataset, acquisition period/date and licence; identify alterations.

Redistribution: CC BY 4.0 conditions apply to covered metadata and photographs; check exclusions and third-party rights.

Current Icelandic service terms expressly include cameras and photographs unless otherwise stated. English page retains older September 2014 wording. Commercial hosting and redistribution of covered metadata/snapshots are conditional; separate live-video/player grants were not established.

Risk: high. Action: attribute, legal_review.

Related evidence: [reference 1](https://www.vegagerdin.is/vegagerdin/gagnasafn/vefthjonustur/terms-and-conditions). These links are not separate verification dates.

### Policy camera-idaho

**Idaho 511**: Provider-specific camera terms.

[Primary terms/evidence](https://511.idaho.gov/about/privacy). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer identifies ITD property and prohibits sale, value-added processing for resale or other for-profit distribution. Non-commercial hosted/camera-specific rights remain insufficiently specified.

Risk: high. Action: request_permission, legal_review.

### Policy camera-illinois

**Travel Midwest / Illinois**: Provider-specific camera terms.

[Primary terms/evidence](https://travelmidwest.com/About/InfoReusePolicy). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Use prescribed IDOT credit/logo and pass policy onward.

Redistribution: Obtain registration/approval, preserve content and comply with agency-specific conditions.

Registered redistribution programme covers information and JPEG camera snapshots, with at least five-minute XML/image request intervals. Commercial applications are contemplated, subject to approval and originating-agency conditions. It is not a full-motion grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://travelmidwest.com/About/RegistrationForm). These links are not separate verification dates.

### Policy camera-indiana

**Indiana TrafficWise**: Provider-specific camera terms.

[Attempted page](https://511in.org/about/disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Site returned an application shell and disclaimer was inaccessible. Vendor XML request programme is an access route, not agency reuse permission.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.castlerockits.com/xml-data-feeds). These links are not separate verification dates.

### Policy camera-inmoves

**Inmoves delivery service**: Owner/media rights not verified.

[Attempted page](https://www.inmoves.nl/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official provider homepage shows copyright/contact but no applicable downstream camera-owner grant.

Risk: high. Action: request_permission, legal_review.

### Policy camera-iowa

**Iowa DOT cameras**: Provider-specific camera terms.

[Primary terms/evidence](https://iowadot.gov/policies-statements/terms-use). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

General photo/video and commercial republication require written consent. GIS CC0/CC BY exceptions cannot automatically be applied to camera pixels. Exact camera catalogue licence did not extract.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://data.iowadot.gov/datasets/IowaDOT::traffic-cameras-3/about); [reference 2](https://iowadot.gov/travel-tools/iowa-511/511-data-feeds). These links are not separate verification dates.

### Policy camera-ipcamlive

**IPCamLive platform**: Service terms; individual stream rights unresolved.

[Primary terms/evidence](https://www.ipcamlive.com/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms bind visitors and subscribers and govern streaming service use. They do not establish a blanket third-party right to redistribute every hosted camera, snapshot or recording. Obtain actual owner authorisation and delivery scope.

Risk: high. Action: request_permission, legal_review.

### Policy camera-ireland

**TII traffic cameras**: CC BY 4.0 for released PSI; camera scope unresolved.

[Primary terms/evidence](https://www.tii.ie/en/compliance/reuse-of-public-sector-information/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: For covered PSI credit TII and include its prescribed Irish Public Sector Information CC BY 4.0 notice.

Redistribution: No project-specific onward-sharing or export grant established.

General PSI policy permits commercial reuse of covered released information, excluding personal and unauthorised third-party content. Traffic-map help returned an application shell; no camera-specific index, snapshot, embed or stream release established.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://traffic.tii.ie/help/). These links are not separate verification dates.

### Policy camera-isleofman

**Isle of Man government cameras**: Owner/media rights not verified.

[Attempted page](https://www.gov.im/about-the-government/legal-notice/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate legal notice inaccessible; exact image reuse terms remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-kansas

**Kansas KanDrive**: Provider-specific camera terms.

[Attempted page](https://www.ksdot.gov/travel/travel-conditions/kandrive). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official description was indexed but direct retrieval returned 403; application homepage was a shell. Vendor XML request programme gives no agency image licence.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.kandrive.gov/); [reference 2](https://www.castlerockits.com/xml-data-feeds). These links are not separate verification dates.

### Policy camera-kcscout

**Kansas City Scout**: Owner/media rights not verified.

[Attempted page](https://www.kcscout.net/Disclaimer.aspx). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate disclaimer inaccessible; exact camera index/pixel reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-lithuania

**Lithuania Eismoinfo**: Provider-specific data/media conditions.

[Attempted page](https://eismoinfo.lt/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Service returned no readable terms. Licences for other traffic datasets cannot be transferred to camera metadata or pixels.

Risk: high. Action: request_permission, legal_review.

### Policy camera-louisiana

**Louisiana 511**: Provider-specific camera terms.

[Primary terms/evidence](https://511la.org/about/disclaimer). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer addresses accounts, warranties and liability. Developer application access does not establish a commercial camera index/image grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://511la.org/developers/doc). These links are not separate verification dates.

### Policy camera-luxembourg

**Luxembourg CITA**: Provider-specific data/media conditions.

[Primary terms/evidence](https://data.public.lu/en/datasets/cita-cameras-autoroute/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: Commercial CC0 location-data reuse supported; image/video rights unresolved.

Exact cameras.kml location resource is CC0 in the official dataset, updated August 2022. This clears covered metadata, not separately hosted stills or video; CITA homepage adds no media grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.cita.lu/). These links are not separate verification dates.

### Policy camera-lyon

**GrandLyon Criter cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.data.gouv.fr/datasets/cameras-web-criter-de-la-metropole-de-lyon). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Credit source and last update for covered information; no implied endorsement.

Redistribution: Commercial licensed metadata reuse supported; resolve separately hosted image scope.

Official catalogue updated 9 October 2026 applies Licence Ouverte 2.0. It describes locations and access to minute-by-minute stills; whether separately hosted image bytes are covered remains ambiguous.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.data.gouv.fr/pages/legal/licences/etalab-2.0). These links are not separate verification dates.

### Policy camera-madrid

**Madrid Informo cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://datos.madrid.es/dataset/202088-0-trafico-camaras/information). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit Madrid, source, supplied update date and licence; identify modifications.

Redistribution: Conditional reuse of published dataset records/snapshots; verify endpoint matches the licensed product.

CC BY 4.0 dataset expressly covers KML locations and five-minute snapshots. General terms permit commercial reproduction and public communication, with source/update metadata preserved and no misleading changes. No continuous-video grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://datos.madrid.es/pages/condiciones-generales-ayuntamiento-de-madrid). These links are not separate verification dates.

### Policy camera-manitoba

**Manitoba 511**: Provider-specific camera terms.

[Attempted page](https://www.manitoba511.ca/about/disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer/terms retrieval failed. Camera/view schemas document access but do not establish image or index reuse rights.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.manitoba511.ca/help/endpoint/cameras); [reference 2](https://www.manitoba511.ca/help/subendpoint/cameras). These links are not separate verification dates.

### Policy camera-massachusetts

**Massachusetts MassDOT cameras**: Provider-specific camera terms.

[Primary terms/evidence](https://www.mass.gov/doc/developers-license-agreement-11132009/download). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Acknowledge MassDOT, avoid misrepresentation and logo use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official indexed developer agreement permits limited revocable reproduction/redistribution and profitable projects. Camera documentation specifies a TrafficLand JPEG feed at one frame per 120 seconds; obtain its terms. Direct PDFs failed; no full-motion grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.mass.gov/doc/massdot-developers-relationship-principles-11132009/download); [reference 2](https://www.mass.gov/info-details/highway-data-for-developers). These links are not separate verification dates.

### Policy camera-mgw

**MGW delivery hosts**: Owner/media rights not verified.

[Attempted page](https://www.mgw-is.uk/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate provider site inaccessible; exact owner and hosted image/stream rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-michigan

**Michigan MiDrive**: Provider-specific camera terms.

[Attempted page](https://www.michigan.gov/mdot/Travel/safety/Efforts/ITS/SEMTOC). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official research references Policy 10212 and signed camera/video-sharing documents but is not the operative licence. Operational contact found; current reuse policy remains unverified.

Risk: high. Action: request_permission, legal_review.

### Policy camera-minnesota

**Minnesota 511**: Provider-specific camera terms.

[Attempted page](https://511mn.org/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Homepage returned an application shell; official search did not establish camera terms. Vendor access programme does not grant agency image rights.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.castlerockits.com/xml-data-feeds). These links are not separate verification dates.

### Policy camera-montreal

**Montreal live traffic cameras**: Provider-specific camera terms.

[Attempted page](https://donnees.montreal.ca/dataset/cameras-observation-routiere). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Live-index catalogue route inaccessible. A separate annotated archive dataset has CC BY 4.0, which cannot be extended to live image bytes or current index without linkage.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://open.canada.ca/data/en/dataset/3c30b818-3cd9-4877-8273-600a2ee80b05). These links are not separate verification dates.

### Policy camera-neotel

**Neotel delivery host**: Owner/media rights not verified.

[Attempted page](https://www.neotel.mk/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate provider site inaccessible; delivery service does not establish camera-owner permission.

Risk: high. Action: request_permission, legal_review.

### Policy camera-nevada

**Nevada 511**: Provider-specific camera terms.

[Attempted page](https://www.nvroads.com/about/disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer inaccessible. Developer camera schema and public-viewing/non-recording FAQ establish no commercial index or image redistribution grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.nvroads.com/developers/doc); [reference 2](https://www.nvroads.com/about/faq). These links are not separate verification dates.

### Policy camera-newbrunswick

**New Brunswick 511**: Provider-specific camera terms.

[Attempted page](https://511.gnb.ca/about/disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Disclaimer/terms retrieval failed. Developer docs and FAQ mention freely viewable government/private-operator images; free viewing is not redistribution permission.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://511.gnb.ca/developers/doc); [reference 2](https://511.gnb.ca/about/faq). These links are not separate verification dates.

### Policy camera-newengland

**New England 511**: Provider-specific camera terms.

[Primary terms/evidence](https://newengland511.org/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Separate Maine, New Hampshire and Vermont terms were inspected. They address service acceptance, responsibilities, warranties and fees, without an affirmative camera copyright or commercial redistribution grant. Seek each agency separately.

Risk: high. Action: request_permission, legal_review.

### Policy camera-newfoundland

**Newfoundland and Labrador 511**: Provider-specific camera terms.

[Primary terms/evidence](https://511nl.ca/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Terms address use, warranties, termination and third-party links without an affirmative commercial or hosted camera grant.

Risk: high. Action: request_permission, legal_review.

### Policy camera-newyork

**New York 511**: Provider-specific camera terms.

[Primary terms/evidence](https://www.511ny.org/developers/resources). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source integrity, follow branding restrictions; source credit encouraged.

Redistribution: Approved programme does not imply unrestricted feed extraction or video resale.

Programme covers camera images/video and an authorised map embed. Official indexed access agreement supports approved value-added redistribution with business/market and intermediate-recipient disclosure; canonical agreement unreadable. Obtain product-specific approval.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://prod-ny.ibi511.com/developers/daa). These links are not separate verification dates.

### Policy camera-northcarolina

**North Carolina DriveNC**: Provider-specific camera terms.

[Primary terms/evidence](https://www.ncdot.gov/about-us/how-we-operate/policy-process/Pages/terms-use.aspx). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

NCDOT permits unaltered non-commercial copying/distribution unless otherwise stated. Third-party licensed photos/video may be excluded. No special commercial DriveNC camera grant verified.

Risk: high. Action: request_permission, legal_review.

### Policy camera-northeast

**North East UTMC camera service**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.netraveldata.co.uk/?page_id=13). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain UTMC/source and OGL 3.0 credit and excluded-rights notices.

Redistribution: Commercial reuse of covered metadata/stills under OGL; no continuous-video grant.

OGL 3.0 service documentation explicitly includes names, locations and still JPEGs and identifies netrafficcams as a consumer. Scope to matching documented service cameras, not arbitrary feeds.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.netraveldata.co.uk/?page_id=42). These links are not separate verification dates.

### Policy camera-northyorkshire

**North Yorkshire weather cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.northyorks.gov.uk/your-council/websites-and-media/your-council/websites-and-media/terms-and-conditions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Council terms did not establish a camera grant. The restrictive Ordnance Survey map clause applies to map data and cannot automatically classify camera photographs.

Risk: high. Action: request_permission, legal_review.

### Policy camera-norway

**Statens vegvesen DATEX cameras**: NLOD for supplied DATEX data and images.

[Primary terms/evidence](https://www.vegvesen.no/en/fag/technology/open-data/a-selection-of-open-data/what-is-datex/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Credit Statens vegvesen, source and NLOD where practicable; identify alterations.

Redistribution: A registered alternative programme is documented below; no onward-sharing or export grant verified for the implemented endpoint.

Provider expressly offers licensed camera images to media/service providers, with registration. This covers supplied DATEX metadata and images; it does not establish rights for unrelated HLS, website embeds or non-DATEX endpoints. The implemented Atlas road-weather-and-view measurement-sites API exposes stillImageUrl and HLS videoUrl. Equivalence to the licensed DATEX delivery has not been established; implemented-path commercial and hosted rights remain unknown.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://dataut.vegvesen.no/en/dataset/webkamera); [reference 2](https://data.norge.no/nlod/en/2.0). These links are not separate verification dates.

### Policy camera-novascotia

**Nova Scotia 511**: Provider-specific camera terms.

[Primary terms/evidence](https://511.novascotia.ca/about/about). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Posted traffic/weather information may be reproduced personally and publicly for non-commercial purposes, subject to exceptions. Commercial permission and third-party imagery/full-motion rights are not granted.

Risk: high. Action: request_permission, legal_review.

### Policy camera-nsw

**Transport for NSW camera metadata**: CC BY metadata; image rights unresolved.

[Primary terms/evidence](https://data.nsw.gov.au/data/en/dataset/2-live-traffic-cameras). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: For licensed metadata credit Transport for NSW and CC BY 4.0; image credits unresolved.

Redistribution: No project-specific onward-sharing or export grant established.

Dataset describes image URLs, coordinates and descriptions, not an express licence to every linked image. Official indexed data licence defaults to CC BY 4.0; portal contract requires registration and no credential sharing. Direct Hub pages returned 403 and PDF retrieval failed. Separate image/stream rights remain unverified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://opendata.transport.nsw.gov.au/datalicence); [reference 2](https://opendata.transport.nsw.gov.au/sites/default/files/2024-09/TfNSW-Open-Data-Portal-Terms.pdf); [reference 3](https://opendata.transport.nsw.gov.au/sites/default/files/2023-08/Live_Traffic_Data_Developer_Guide.pdf). These links are not separate verification dates.

### Policy camera-nzta

**NZTA Traffic and Travel information**: Registration and restricted travel-information reuse.

[Primary terms/evidence](https://www.nzta.govt.nz/about-us/our-data-and-official-information/use-our-data/terms-of-use). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain supplied image form, notices and source credit.

Redistribution: Registration and extra licence may be required; no unrestricted paid redistribution grant.

Official indexed terms include snapshots/webcams; direct fetch 403. Redistributors must register independently; preserve images/notices and freshness. Charging for value-added features differs from charging for information. Current endpoint mapping unresolved after historic InfoConnect closure.

Risk: high. Action: request_permission, legal_review.

### Policy camera-ontario

**Ontario 511 developer data**: OGL Ontario data unless otherwise stated; individual access approval.

[Primary terms/evidence](https://511on.ca/developers/resources). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use OGL Ontario source attribution and communicate the supplied disclaimer.

Redistribution: Metadata commercial reuse is conditional; approval and camera-image rights remain separate.

Developer agreement requires proposed use and downstream recipients disclosed for review. Underlying image/partner rights are unverified. Direct OGL page returned 403; official indexed licence retrieved.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.ontario.ca/page/open-government-licence-ontario); [reference 2](https://511on.ca/help/endpoint/cameras). These links are not separate verification dates.

### Policy camera-opencctv

**OpenCCTV directory**: Reuse grant not located.

[Attempted page](https://opencctv.org/about). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official About, sourcing and privacy pages describe an index/embedding service operated by Impactful Technology LLC. They do not establish an index reuse licence or underlying camera permission. Targeted search and failed terms routes did not resolve commercial hosting, snapshots or streams.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://opencctv.org/how-we-source); [reference 2](https://opencctv.org/privacy); [reference 3](https://opencctv.org/terms); [reference 4](https://opencctv.org/terms-of-service). These links are not separate verification dates.

### Policy camera-oregon

**Oregon TripCheck**: Provider-specific camera terms.

[Attempted page](https://www.tripcheck.com/Pages/API). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official inventory documentation includes partner-camera still-image URLs. Developer subscription requires terms not retrieved here; endpoint access does not clear pixels.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://apiportal.odot.state.or.us/product/tripcheck-data-api); [reference 2](https://www.oregon.gov/ODOT/Maintenance/Pages/Traveler-Information.aspx). These links are not separate verification dates.

### Policy camera-ottawa

**Ottawa traffic cameras**: Provider-specific camera terms.

[Primary terms/evidence](https://traffic.ottawa.ca/en/traffic-map-data-lists-and-resources/faq). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use the Ottawa OGL acknowledgement and applicable owner credits.

Redistribution: A registered alternative programme is documented below; no onward-sharing or export grant verified for the implemented endpoint.

FAQ expressly supports developer applications delivering images from their own servers. Registered still-image API has a minimum 60-second interval and invokes Ottawa OGL v2. MTO-owned cameras and other unauthorised third-party rights remain excluded; no continuous-video grant. The implemented /beta/camera_list and /map/camera?id= paths differ from the registered /opendata/camera certificate API. No equivalence of their delivery rights was verified, so the implemented-path commercial and hosted rights remain unknown.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://traffic.ottawa.ca/en/opendata); [reference 2](https://ottawa.ca/en/city-hall/open-transparent-and-accountable-government/open-data/open-data-licence-version-20). These links are not separate verification dates.

### Policy camera-owner-rights

**Per-camera owner and delivery rights**: Index metadata and camera media have separate rights.

Status: `per_item_required`. Checked: not verified. Attempted: not attempted.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Keep each camera owner and provider credit; do not substitute directory credit.

Redistribution: Public stream/embed URLs and an allowlisted host do not authorise copying, proxying, capture, resale or report export.

Review each host, camera owner and delivery method. OSIRIS MIT catalogue code/data notices do not license third-party streams. A directory or government index does not establish rights in every image.

Risk: high. Action: request_permission, legal_review.

### Policy camera-pennsylvania

**Pennsylvania 511**: Provider-specific camera terms.

[Primary terms/evidence](https://www.pa.gov/content/dam/copapwp-pagov/en/penndot/documents/programs-and-doing-business/onlineservices/511pa_developers_corner-tcs.pdf). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit PennDOT and avoid implied endorsement.

Redistribution: Obtain approval for exact purpose and delivery; current-traffic restriction is material to analytical evidence and exports.

February 2014 programme permits approved value-added camera redistribution including advertising, requires multi-user developer-server replication, and restricts images to current traffic. Other OSINT purposes require written approval. Confirm current applicability; general site terms are more restrictive.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.511pa.com/about/disclaimer). These links are not separate verification dates.

### Policy camera-puertorico

**Puerto Rico ITS**: Provider-specific camera terms.

[Attempted page](https://www.dtop.pr.gov/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official searches did not locate camera reuse terms. Candidate ITS About.aspx and TermsOfUse.aspx routes failed and were not established as operative terms.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://its.act.pr.gov/About.aspx); [reference 2](https://its.act.pr.gov/TermsOfUse.aspx). These links are not separate verification dates.

### Policy camera-quebec

**Quebec traffic camera metadata**: Provider-specific camera terms.

[Primary terms/evidence](https://www.donneesquebec.ca/recherche/dataset/camera-de-circulation). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: For covered metadata retain source and CC BY 4.0 attribution.

Redistribution: Commercial metadata reuse is conditional; image/footage redistribution remains unverified.

Official indexed metadata dataset licenses locations and video URLs under CC BY 4.0. This does not clear image bytes or partner footage. FAQ describes refreshed five-second loops and stills, not necessarily continuous live video.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.quebec511.info/en/quebec511/faq.asp). These links are not separate verification dates.

### Policy camera-queensland

**Queensland Traffic cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.data.qld.gov.au/dataset/131940-traffic-and-travel-information-geojson-api). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Credit Queensland/Transport and Main Roads, source and CC BY 4.0 for covered data.

Redistribution: Commercial metadata reuse supported; separate image hosting/republication needs established licence.

Official GeoJSON webcam metadata is CC BY 4.0; developer page encourages applications. Separate website copyright restricts content not expressly CC-licensed to personal/non-commercial use. Exact image coverage unresolved.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://qldtraffic.qld.gov.au/more/Developers-and-Data/index.html); [reference 2](https://qldtraffic.qld.gov.au/more/Copyright/index.html). These links are not separate verification dates.

### Policy camera-river-japan

**MLIT river cameras**: Owner/media rights not verified.

[Attempted page](https://www.river.go.jp/portal/#80). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official portal inspected without establishing an applicable camera-image licence. Do not infer snapshot redistribution from public display.

Risk: high. Action: request_permission, legal_review.

### Policy camera-rws

**Rijkswaterstaat cameras**: CC0 website text excludes imagery.

[Primary terms/evidence](https://www.rijkswaterstaat.nl/copyright). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: For authorised images use Rijkswaterstaat and creator credit; text requests Bron: Rijkswaterstaat.

Redistribution: No project-specific onward-sharing or export grant established.

Official indexed copyright policy inspected; direct retrieval timed out twice. Images and video are excluded from CC0. Camera-specific index, snapshot, embed and stream rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.rwsverkeersinfo.nl/sitemap/). These links are not separate verification dates.

### Policy camera-saskatchewan

**Saskatchewan Highway Hotline**: Provider-specific camera terms.

[Primary terms/evidence](https://www.saskatchewan.ca/copyright). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Linked general policy requires advance written commercial permission and Crown credit for qualifying accurate non-commercial copies. Linked terms exclude other gov.sk.ca sites; exact Hotline coverage is ambiguous.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.saskatchewan.ca/terms-of-use); [reference 2](https://hotline.gov.sk.ca/region/All%20Districts). These links are not separate verification dates.

### Policy camera-scotland

**Traffic Scotland images and indexes**: Subscriber or express-authorisation terms.

[Primary terms/evidence](https://www.traffic.gov.scot/copyright). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit Traffic Scotland and retain supplied working URLs.

Redistribution: Confirm subscriber-specific commercial, proxy, export and redistribution rights before use.

Direct links to camera images and private-network use require express authorisation. Developer hub offers approved subscribers images and camera lists over FTP. Subscriber portal requires authentication; actual agreement is unverified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.traffic.gov.scot/traffic-scotland-developer-hub); [reference 2](https://developer.trafficscotland.org/). These links are not separate verification dates.

### Policy camera-singapore

**Singapore Traffic Images**: Singapore Open Data Licence.

[Primary terms/evidence](https://data.gov.sg/open-data-licence). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Conspicuous publisher/source and licence acknowledgement.

Redistribution: Covered dataset reuse and app-user sublicensing permitted; further downstream sublicensing restricted.

Official Traffic Images dataset permits commercial use. Licence excludes third-party rights/personal data; do not extend to different LTA DataMall contracts or other footage.

Risk: medium. Action: attribute, legal_review.

Related evidence: [reference 1](https://data.gov.sg/collections/354/datasets/d_6cdb6b405b25aaaacbaf7689bcc6fae0/view). These links are not separate verification dates.

### Policy camera-skyline

**SkylineWebcams**: Prior written reproduction permission.

[Primary terms/evidence](https://www.skylinewebcams.com/terms-of-use.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Do not remove marks; obtain the required credit with permission.

Redistribution: Sharing through supplied links only unless separately authorised; no attribution-only reuse exception found.

April 2020 terms cover frames, images, footage and text. Supplied sharing links do not authorise feed extraction, proxying, recording or a new player. Downloading, screenshots, copying, publication and commercial exploitation require written VisioRay permission.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.skylinewebcams.com/support/faq.html). These links are not separate verification dates.

### Policy camera-slupsk

**Slupsk city cameras**: Owner/media rights not verified.

[Attempted page](https://www.slupsk.pl/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official city homepage links cameras and privacy, but no applicable camera reuse licence was established.

Risk: high. Action: request_permission, legal_review.

### Policy camera-smartburgas

**Smart Burgas cameras**: Owner/media rights not verified.

[Attempted page](https://www.smartburgas.eu/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Provider site inaccessible; image/stream reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-taiwan

**Taiwan Highway Bureau CCTV**: Provider-specific data/media conditions.

[Primary terms/evidence](https://data.gov.tw/dataset/29817). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use Highway Bureau attribution prescribed by service rules and data licence.

Redistribution: Covered metadata supports broad reuse; exact stream-media rights remain unresolved.

Official dataset uses Government Data Licence 1.0; service rules require Highway Bureau credit and at least 60 seconds between retrievals. Schema includes stream URLs/intended display, but does not conclusively clear separately delivered streams for commercial proxying/archives.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://data.gov.tw/license); [reference 2](https://thbapp.thb.gov.tw/opendata/); [reference 3](https://thbapp.thb.gov.tw/opendata/cctvdata.aspx). These links are not separate verification dates.

### Policy camera-tallinn

**Tallinn crossings**: Provider-specific data/media conditions.

[Attempted page](https://ristmikud.tallinn.ee/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Service/help pages establish no reuse licence. Operator recording retention and law-enforcement extracts do not grant public commercial redistribution.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://ristmikud.tallinn.ee/index.php/login/abi). These links are not separate verification dates.

### Policy camera-tamar

**Tamar Crossings cameras**: Owner/media rights not verified.

[Attempted page](https://www.tamarcrossings.org.uk/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route inaccessible; exact image reuse terms remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-tfl

**TfL JamCam snapshots**: TfL modified OGL transport data terms.

[Primary terms/evidence](https://tfl.gov.uk/corporate/terms-and-conditions/transport-data-service). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain TfL image branding and required transport-data attribution.

Redistribution: Commercial supplied snapshots/metadata reuse conditional on terms, registration and image freshness.

Registration applies. Camera guidance explicitly allows website/intranet images; retain supplied form/branding, no cropping, and update within 15 minutes. This does not cover other CCTV footage. The shared Amazon S3 hostname is linked here only for the /jamcams.tfl.gov.uk/ path constrained by this adapter, not for unrelated buckets or media.

Risk: medium. Action: attribute, legal_review.

Related evidence: [reference 1](https://tfl.gov.uk/info-for/open-data-users/our-open-data). These links are not separate verification dates.

### Policy camera-tkchopin

**TK Chopin cameras**: Owner/media rights not verified.

[Attempted page](https://www.tkchopin.pl/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Provider site inaccessible; image/stream reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-toronto

**Toronto traffic camera metadata**: Provider-specific camera terms.

[Primary terms/evidence](https://open.toronto.ca/dataset/traffic-cameras/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use prescribed Toronto OGL acknowledgement for covered information.

Redistribution: Dataset metadata and separately linked image rights must be resolved independently.

Dataset page identifies Toronto OGL, but substantive dynamic description did not extract. OGL permits commercial distribution of covered information with acknowledgement and third-party exclusions; linked image bytes/footage are not proven covered.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://open.toronto.ca/open-data-licence/). These links are not separate verification dates.

### Policy camera-uab

**UAB camera CDN**: Owner/media rights not verified.

[Attempted page](https://www.uab.org/copyright). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate copyright route inaccessible; CDN hostname does not establish every camera owner or terms.

Risk: high. Action: request_permission, legal_review.

### Policy camera-uss

**USS Group delivery host**: Owner/media rights not verified.

[Attempted page](https://www.ussgroup.co.uk/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route inaccessible; delivery supplier and camera-owner rights remain separate.

Risk: high. Action: request_permission, legal_review.

### Policy camera-utah

**Utah UDOT Traffic**: Provider-specific camera terms.

[Primary terms/evidence](https://udottraffic.utah.gov/about/disclaimer). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Public-service warranties and road cautions provide no affirmative camera reuse licence. Camera API describes metadata and image URLs, not pixel rights.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://udottraffic.utah.gov/help/endpoint/cameras). These links are not separate verification dates.

### Policy camera-uzivo

**Uzivo Beograd cameras**: Owner/media rights not verified.

[Attempted page](https://uzivobeograd.rs/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate provider site inaccessible; image/stream reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-western-isles

**Comhairle nan Eilean Siar cameras**: Owner/media rights not verified.

[Attempted page](https://www.cne-siar.gov.uk/terms-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route inaccessible; exact image reuse terms remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy camera-westmorland

**Westmorland and Furness weather cameras**: Provider-specific data/media conditions.

[Primary terms/evidence](https://www.westmorlandandfurness.gov.uk/disclaimer). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm required provider/owner credit.

Redistribution: No blanket commercial image, continuous-video, recording or export grant established.

Current disclaimer supplies no reuse grant. Legacy Eden copyright policy requires permission for photographs/commercial use unless open data, but cannot be assumed to govern the current application.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.eden.gov.uk/about-this-site/website-legal-statements/copyright/). These links are not separate verification dates.

### Policy camera-wsdot

**WSDOT camera records and imagery**: Unverified reuse rights.

[Attempted page](https://wsdot.wa.gov/about/policies/travel-information-disclaimer). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Current travel disclaimer returned 403; indexed text established disclaimers only. API camera schema includes non-WSDOT owners. Registration and image URLs do not establish onward rights.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.wsdot.wa.gov/traffic/api/); [reference 2](https://wsdot.wa.gov/traffic/api/Documentation/class_camera.html). These links are not separate verification dates.

### Policy camera-youtube

**YouTube camera embeds**: Authorised player use; separate owner/content restrictions.

[Primary terms/evidence](https://www.youtube.com/static?template=terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve player features, source/channel identification and owner notices.

Redistribution: Use authorised player functionality within terms; independently clear recording, screenshots, proxying and exported footage.

YouTube permits showing videos through its provided embeddable player. Extraction, downloading, redistribution and automated access outside authorised service functionality require applicable permission. Embeddability is not a universal recording/export licence or proof of uploader ownership.

Risk: high. Action: request_permission, legal_review.

### Policy camera-yukon

**Yukon 511**: Provider-specific camera terms.

[Primary terms/evidence](https://511yukon.ca/about/disclaimer). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Confirm source-specific credit before use.

Redistribution: No blanket commercial, hosted, recording or export grant established.

Official indexed disclaimer addresses warranties, privacy and third parties, without an affirmative commercial/hosted camera reuse grant.

Risk: high. Action: request_permission, legal_review.

### Policy cbc

**CBC**: Terms not verified.

[Attempted page](https://www.cbc.ca/aboutus/termsofuse.html). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official terms retrieval was blocked by robots; no current publisher reuse grant verified.

Risk: high. Action: request_permission, legal_review.

### Policy cbs

**CBS News**: Terms not verified.

[Attempted page](https://www.paramount.com/legal/us/en/cbsi/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate current corporate terms could not be retrieved. Historical local-feed terms do not resolve this world-news endpoint.

Risk: high. Action: request_permission, legal_review.

### Policy cccs

**Canadian Centre for Cyber Security**: Terms not verified.

[Attempted page](https://www.cyber.gc.ca/en/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate public-site terms routes failed. Separate authenticated portal terms and a report copyright warning do not resolve the public-advisory feed.

Risk: high. Action: request_permission, legal_review.

### Policy cdt

**China Digital Times**: Terms not verified.

[Attempted page](https://chinadigitaltimes.net/copyright/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Targeted search found third-party documents rather than a publisher-wide licence; candidate copyright route was inaccessible.

Risk: high. Action: request_permission, legal_review.

### Policy celestrak

**CelesTrak service usage**: Usage policy reviewed; commercial redistribution licence not established.

[Primary terms/evidence](https://celestrak.org/usage-policy.php). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain CelesTrak and upstream provenance pending rights clarification.

Redistribution: Free service access does not by itself establish downstream licensing rights.

Policy updated 22 May 2026: download once per update (GP every two hours); stop on non-200 responses. Check scheduler/backoff compliance separately.

Risk: medium. Action: attribute, legal_review.

### Policy census

**US Census**: Unverified.

[Attempted page](https://www.census.gov/about/policies/copyright.html). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary policy lookup failed and official-domain search did not establish the current product-specific permission. No federal-public-domain assumption applied.

Risk: high. Action: request_permission, legal_review.

### Policy cert-eu

**CERT-EU**: CC BY 4.0 for covered EU documents.

[Primary terms/evidence](https://cert.europa.eu/legal-notice). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit CERT-EU/EU and CC BY 4.0; indicate changes.

Redistribution: Covered documents may be redistributed under CC BY 4.0; excluded material separately cleared.

Legal notice permits reuse with credit and changes identified; excludes marks and unauthorised third-party rights. Check individual report notices and personal-image permissions.

Risk: high. Action: attribute, legal_review.

### Policy cert-fr

**CERT-FR**: Licence Ouverte 2.0 except explicit exceptions.

[Primary terms/evidence](https://www.cert.ssi.gouv.fr/mentions-legales/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain ANSSI/CERT-FR source, date and licence; mark changes.

Redistribution: Reuse under Licence Ouverte 2.0 subject to exceptions and attribution.

Legal notice applies the open licence unless otherwise stated. ANSSI logos/marks require separate approval; republication does not imply ANSSI endorsement.

Risk: high. Action: attribute, legal_review.

### Policy cert-ua

**CERT-UA**: Applicable reuse grant not located.

[Attempted page](https://cert.gov.ua/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official homepage returned no readable content; applicable terms not established.

Risk: high. Action: request_permission, legal_review.

### Policy cgtn

**CGTN**: Personal, non-commercial site access.

[Primary terms/evidence](https://www.cgtn.com/terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve CGTN and contributor copyright notices; branding is separately restricted.

Redistribution: No commercial resale, third-party copying or automated extraction grant under ordinary access.

Terms updated 1 May 2026 restrict extraction, derivatives and third-party copying. Commercial reuse needs express written consent.

Risk: high. Action: request_permission, legal_review.

### Policy cisa

**CISA**: Unverified.

[Attempted page](https://www.cisa.gov/about/website-policies). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary policy lookup failed and official-domain search did not establish the current product-specific permission. No federal-public-domain assumption applied.

Risk: high. Action: request_permission, legal_review.

### Policy cloudflare-radar

**Cloudflare Radar API data**: CC BY-NC 4.0 (API/download data).

[Primary terms/evidence](https://radar.cloudflare.com/about). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit Cloudflare Radar, source link and CC BY-NC 4.0; identify changes.

Redistribution: Non-commercial sharing subject to the licence. Commercial display/export needs a separate grant.

API data is distinct from CC BY 4.0 embeddable/downloadable graphs. Non-commercial hosted suitability is fact-specific; no project exception verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://creativecommons.org/licenses/by-nc/4.0/). These links are not separate verification dates.

### Policy cna-rss

**CNA RSS**: Personal, non-commercial RSS terms.

[Primary terms/evidence](https://www.channelnewsasia.com/rss/rssterms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Direct link to the full article; no intermediate page; preserve supplied content.

Redistribution: Third-party distribution, forwarding, licensing and transfer restricted, including non-commercial use.

Attribution alone does not authorise multi-user redistribution. Seek a separate content-hosting agreement.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.channelnewsasia.com/contact-us/help-and-feedback). These links are not separate verification dates.

### Policy companies-house

**Companies House API**: Applicable reuse grant not located.

[Attempted page](https://developer.company-information.service.gov.uk/overview). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Developer documentation and linked register guidance inspected; candidate API terms routes failed. GOV.UK guidance-page OGL does not itself establish all company-file/officer/PSC data rights. Confirm register reuse and privacy obligations.

Risk: high. Action: request_permission, legal_review.

### Policy contracts-finder

**Contracts Finder**: Terms not verified.

[Attempted page](https://www.contractsfinder.service.gov.uk/TermsAndConditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms, help and homepage retrieval failed. A hosted tender attachment is not evidence of the API dataset licence.

Risk: high. Action: request_permission, legal_review.

### Policy copernicus

**Copernicus Data Space footprints**: Sentinel data open; other portal material restricted.

[Primary terms/evidence](https://dataspace.copernicus.eu/terms-and-conditions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: For covered data include Copernicus Sentinel data and year; modified outputs require the modified-data notice.

Redistribution: Exact footprint product and retained/exported metadata scope require confirmation.

Sentinel legal notice permits lawful reproduction, distribution and adaptation with source notices. Other portal content is non-commercial and not generally redistributable. Confirm that exact catalogue footprints are covered Sentinel data/service information rather than assuming all portal metadata inherits the grant.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice). These links are not separate verification dates.

### Policy crisisgroup

**International Crisis Group**: Unverified.

[Attempted page](https://www.crisisgroup.org/legal). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary legal page returned 403; search found a feed description but no current republication grant.

Risk: high. Action: request_permission, legal_review.

### Policy crossref

**Crossref metadata**: Metadata reuse without restriction, as described by Crossref.

[Primary terms/evidence](https://www.crossref.org/services/metadata-retrieval/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Preserve Crossref provenance, authors and DOI links.

Redistribution: Metadata access is not a grant to republish linked full articles or third-party images.

Review any source-specific copyrighted abstract/full-text field before exporting more than the implemented metadata.

Risk: medium. Action: keep, attribute, legal_review.

### Policy dabanga

**Radio Dabanga**: Applicable reuse grant not located.

[Attempted page](https://www.dabangasudan.org/en/about-us). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

About page and copyright search do not establish a reuse licence. Hosted third-party reports and images retain their own rights.

Risk: high. Action: request_permission, legal_review.

### Policy dawn

**Dawn**: Restricted.

[Primary terms/evidence](https://www.dawn.com/terms/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve notices.

Redistribution: Commercial reuse requires prior written permission.

Review intellectual-property terms.

Risk: high. Action: request_permission, legal_review.

### Policy deepstate

**DeepState API**: Provider API licence; commercial use by prior agreement.

[Primary terms/evidence](https://deepstatemap.live/license.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve DeepState identification and approved links/branding.

Redistribution: API distribution, publication, proxying or transfer is restricted without authorisation.

Visual/text material reuse rules are separate from API rights. Hosted cache/display and exports require express scope confirmation; no grant verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://api.deepstatemap.live/request). These links are not separate verification dates.

### Policy defcon-social

**DEF CON Social**: Terms not verified.

[Attempted page](https://defcon.social/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Instance terms route was inaccessible. Software licensing does not license users posts; owner rights and federation terms remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy deutschlandfunk

**Deutschlandfunk**: Private non-commercial use; written consent for reuse.

[Primary terms/evidence](https://www.deutschlandfunk.de/nutzungsbedingungen-102.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms restrict reproduction, storage, translation and redistribution, including excerpts, without prior written consent. Advertising, sponsorship and subscription benefit are expressly commercial; sharing links does not license copied content.

Risk: high. Action: request_permission, legal_review.

### Policy digitraffic

**Fintraffic Digitraffic**: CC BY 4.0 data and service terms.

[Primary terms/evidence](https://www.digitraffic.fi/en/terms-of-service/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Source: Fintraffic / digitraffic.fi, licence CC BY 4.0; identify changes.

Redistribution: Covered data may be reused with licence conditions; verify any third-party exception.

Review camera-image scope separately where contributor rights differ; preserve rate limits and service identification.

Risk: medium. Action: keep, attribute, legal_review.

### Policy diplomat

**The Diplomat**: Terms not verified.

[Attempted page](https://thediplomat.com/terms-of-use/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy dw-rss

**Deutsche Welle RSS**: Distribution registration and product-specific terms.

[Primary terms/evidence](https://b2b.dw.com/page/dw-terms-conditions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

DW promotes German News Service integration, but that is a specific registered offering. Do not assume the existing world/business feeds have its rights. Exact feed and report/export agreement unverified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://amp.dw.com/en/benefit-from-smart-content-made-in-germany/a-19470839). These links are not separate verification dates.

### Policy ecb

**ECB reference rates and releases**: ECB reproduction conditions.

[Primary terms/evidence](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite ECB, reproduce accurately and identify modifications.

Redistribution: Sold documents require notice before payment and at access that ECB information is freely available; authored papers have separate restrictions.

Reference rates are informational, not transaction prices. Apply the free-source notice to relevant commercial reports/subscriptions.

Risk: medium. Action: keep, attribute, legal_review.

### Policy economist

**The Economist**: Permission/licensing service.

[Primary terms/evidence](https://www.economist.com/syndication/permissions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official permissions page offers a licence for the specified reuse. General terms direct access blocked; no project licence or automated-feed/AI scope verified.

Risk: high. Action: request_permission, legal_review.

### Policy eia

**US Energy Information Administration**: Public-domain EIA products; third-party exceptions.

[Primary terms/evidence](https://www.eia.gov/about/copyrights_reuse.php). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit EIA and publication date; distinguish EIA quotations from other text.

Redistribution: Public-domain products reusable; protect separately licensed images/content.

Data/files/reports/charts may be used/distributed. Protected third-party works require permission; translations identify translator and original source.

Risk: low. Action: keep, attribute.

### Policy elpais

**El Pais**: Terms not verified.

[Attempted page](https://www.elpais.com/estaticos/aviso-legal/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate legal-notice route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy emsc

**EMSC SeismicPortal datasets**: CC BY 4.0 for downloaded datasets/products.

[Primary terms/evidence](https://www.seismicportal.eu/terms.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit EMSC-CSEM SeismicPortal, source URL and access date; link licence and identify changes.

Redistribution: Covered earthquake datasets can be reused commercially with CC BY conditions.

The website/services/databases themselves remain copyrighted separately. Follow exact web-service documentation and dataset notice.

Risk: medium. Action: keep, attribute.

### Policy eox-2024

**EOxCloudless 2024**: CC BY-NC-SA 4.0 or suitable EOX commercial licence.

[Primary terms/evidence](https://cloudless.eox.at/license-non-commercial). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2024).

Redistribution: Preserve visible attribution; independent downstream reuse/sublicensing needs scope review.

2018–2025 imagery is non-commercial under published free terms. The 2016 CC BY offer does not cover the implemented 2024 layer. Map export declarations are not licence verification.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://cloudless.eox.at/documentation/license). These links are not separate verification dates.

### Policy eu-sanctions

**EU financial sanctions data**: Portal metadata CC0; dataset rights separate.

[Primary terms/evidence](https://data.europa.eu/en/legal-notice). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain EU and originating dataset provenance; apply dataset-specific credit.

Redistribution: Do not extend portal metadata CC0 to all linked datasets.

Portal legal notice applies CC0 to portal metadata and CC BY 4.0 to EU-owned editorial content. Linked resources require their own licence; exact financial-sanctions download scope remains unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy eupolicy-social

**EU Policy Social**: Terms not verified.

[Attempted page](https://eupolicy.social/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Instance terms route was inaccessible. User-post commercial/hosted reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy euronews

**Euronews and Africanews**: Personal non-commercial copy; permission for reuse.

[Primary terms/evidence](https://www.euronews.com/terms-and-conditions/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Keep author, copyright and trade-mark notices intact.

Redistribution: No blanket hosted or export grant; narrow statutory exceptions need legal assessment.

Terms expressly cover both domains. Personal downloading does not authorise commercial exploitation, republication, translation or redistribution; permission from publisher and relevant rightsholders is required.

Risk: high. Action: request_permission, legal_review.

### Policy express-urdu

**Express Urdu**: Terms not verified.

[Attempted page](https://www.express.pk/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Search result /terms was a news-tag page, not legal terms. Candidate terms-and-conditions route failed.

Risk: high. Action: request_permission, legal_review.

### Policy federal-reserve

**Federal Reserve Board**: Public domain unless otherwise indicated.

[Primary terms/evidence](https://www.federalreserve.gov/disclaimer.htm). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite Board source; no unauthorised seals/logos or implied affiliation.

Redistribution: Board public-domain information may be copied/distributed; exclude separately owned content.

Non-Board material and branding require separate permission. Linked external sites retain their own conditions.

Risk: low. Action: keep, attribute.

### Policy first-epss

**FIRST EPSS score enrichment**: Published free-use guidance; full redistribution scope unresolved.

[Primary terms/evidence](https://www.first.org/epss/faq). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: FIRST requests attribution for publications/products. Credit FIRST EPSS, link to the project, and retain score and model dates where supplied.

Redistribution: Confirm the scope for retained scores, commercial multi-user display and exported evidence.

The FAQ permits free score access without registration and requests attribution. API guidance supports small lookups, while bulk synchronisation should use daily files. These pages do not supply an explicit blanket commercial redistribution licence. The default CISA connector attaches EPSS probability, percentile and date to retained events; its API batch pattern also needs service-use review.

Risk: high. Action: attribute, legal_review.

Related evidence: [reference 1](https://www.first.org/epss/data.html). These links are not separate verification dates.

### Policy france24

**France 24**: Unverified.

[Attempted page](https://www.france24.com/en/legal-notice). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary lookup inaccessible; site search also blocked. Obtain current terms and precise feed/hosted rights from the publisher.

Risk: high. Action: request_permission, legal_review.

### Policy gdacs

**GDACS disaster information**: Service disclaimer plus linked EU reuse policy.

[Primary terms/evidence](https://data.gdacs.org/About/termofuse.aspx). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms describe modelled/uncertain disaster information, not validated official warnings. Linked EC policy licenses EU-owned content CC BY 4.0 but excludes third-party rights; exact combined data grant needs confirmation.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://commission.europa.eu/legal-notice_en). These links are not separate verification dates.

### Policy gdelt

**GDELT datasets**: GDELT published data-use terms.

[Primary terms/evidence](https://www.gdeltproject.org/about.html#termsofuse). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite GDELT and link its website.

Redistribution: Dataset redistribution, mirrors and commercial use permitted under the published terms.

This covers GDELT data, not copyright in linked news articles, photographs or publisher excerpts.

Risk: medium. Action: attribute, legal_review.

### Policy geoboundaries

**geoBoundaries**: CC BY 4.0.

[Primary terms/evidence](https://www.geoboundaries.org/index.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit geoBoundaries and its requested Runfola et al. (2020) citation.

Redistribution: Commercial reuse and redistribution with attribution, licence notice and indication of changes.

Confirm the packaged boundary release and preserve its source-specific metadata.

Risk: medium. Action: attribute, legal_review.

### Policy gfw

**Global Fishing Watch**: CC BY-NC 4.0 default plus service/dataset terms.

[Primary terms/evidence](https://globalfishingwatch.org/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Source/access date, licence and provider notices; include the specified apparent-fishing disclaimer where applicable.

Redistribution: Non-commercial reuse is conditional and dataset-specific; terms additionally address same-term reuse.

API/bulk registration is not commercial permission. Third-party data and hosted audience need review; software Apache licensing is not a data grant.

Risk: high. Action: request_permission, legal_review.

### Policy gleif

**GLEIF LEI data**: CC0 data with access-service terms.

[Primary terms/evidence](https://www.gleif.org/en/meta/lei-data-terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: GLEIF provenance recommended; no CC0 attribution condition.

Redistribution: CC0 reuse of covered LEI data; service terms and unrelated materials remain separate.

No licence claim is made for linked company filings or third-party source documents.

Risk: low. Action: keep, attribute.

### Policy google-dns

**Google Public DNS**: Google API service terms; returned-record rights separate.

[Primary terms/evidence](https://developers.google.com/speed/public-dns/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain required API/source notices and data provenance; do not imply Google endorsement.

Redistribution: API terms reserve content-owner and applicable-law exceptions; confirm exact DNS retention/export treatment.

Public DNS incorporates Google APIs terms. API access does not establish third-party content rights. Permanent copies, cache duration, redistribution and attribution conditions require evaluation for retained DNS evidence.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://developers.google.com/terms). These links are not separate verification dates.

### Policy google-news

**Google News aggregation**: Google service terms; publisher content separately owned.

[Primary terms/evidence](https://policies.google.com/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

The Other content section requires publisher permission or a lawful basis. General Google access does not license third-party News material. RSS-specific permission remains unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy google-threat-blog

**Google Threat Intelligence blog**: Applicable reuse grant not located.

[Attempted page](https://cloud.google.com/blog/topics/threat-intelligence). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Blog and cloud-service terms were inspected without establishing a specific blog republication licence. Do not substitute GCP service terms or developer-documentation licences.

Risk: high. Action: request_permission, legal_review.

### Policy govuk

**GOV.UK published content**: OGL v3 for covered content, with exceptions.

[Primary terms/evidence](https://www.gov.uk/help/terms-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Attribute the originating department and OGL; identify third-party material.

Redistribution: Reuse covered Crown content under OGL; exclude content carrying separate rights.

GOV.UK permits feed reuse. Service-specific terms, personal data, logos and third-party rights still need review.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). These links are not separate verification dates.

### Policy guardian

**Guardian**: Restricted.

[Primary terms/evidence](https://www.theguardian.com/help/terms-of-service). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve notices.

Redistribution: Commercial aggregation and AI reuse require approval.

Review section 3.

Risk: high. Action: request_permission, legal_review.

### Policy gvp

**Smithsonian Global Volcanism Program**: Federal compilation statements and commercial-permission restriction.

[Primary terms/evidence](https://volcano.si.edu/gvp_termsofuse.cfm). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit GVP/Smithsonian and dataset citation; preserve notices.

Redistribution: Do not label all GVP data CC0; photographs and maps can contain third-party rights.

GVP identifies its principal reports/database compilation as federal-employee products but also requires written permission for commercial products/services incorporating content. Smithsonian general terms permit specifically CC0-designated content, not all GVP material. Resolve this scope conflict before commercial use.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.si.edu/termsofuse). These links are not separate verification dates.

### Policy hapi

**HDX HAPI**: Unverified.

[Attempted page](https://hapi.humdata.org/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Documentation candidates inaccessible and official API home returned 403. Review each original humanitarian dataset licence and HAPI terms; app identifier is not permission.

Risk: high. Action: request_permission, legal_review.

### Policy herald-scotland

**Herald Scotland**: Unverified.

[Attempted page](https://www.heraldscotland.com/terms/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms and domain search blocked; exact publisher rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy hindustan-times

**Hindustan Times**: Restricted.

[Primary terms/evidence](https://www.hindustantimes.com/terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain notices.

Redistribution: Personal non-commercial use only; commercial reuse requires permission.

Review sections C and D.

Risk: high. Action: request_permission, legal_review.

### Policy hrana-en

**HRANA English**: Applicable reuse grant not located.

[Attempted page](https://www.en-hrana.org/about-us/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

About page and targeted copyright search did not locate applicable content-reuse terms; annual-report copyright notices do not establish an RSS licence.

Risk: high. Action: request_permission, legal_review.

### Policy hrana-fa

**HRANA Persian**: Applicable reuse grant not located.

[Attempted page](https://www.hra-news.org/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Targeted official-domain search returned copyrighted reports, not a feed-wide reuse licence.

Risk: high. Action: request_permission, legal_review.

### Policy ic3

**FBI IC3 public advisories**: Copying/distribution permitted with statutory mark restrictions.

[Primary terms/evidence](https://www.ic3.gov/Home/Privacy). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Identify IC3/FBI as information source without implying endorsement or misusing protected insignia.

Redistribution: Covered site information may be copied/distributed under the cited policy.

Site policy permits information distribution/copying subject to restrictions on FBI seal/name/initials and implied endorsement. Does not clear external or specifically copyrighted material.

Risk: high. Action: attribute, legal_review.

### Policy ifrc-go

**IFRC GO**: Unverified.

[Attempted page](https://go.ifrc.org/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms route rendered only the application shell. No copyright/data licence could be extracted; review exact GO records and originator rights.

Risk: high. Action: request_permission, legal_review.

### Policy independent-rss

**The Independent RSS**: Personal, non-commercial RSS terms.

[Primary terms/evidence](https://www.independent.co.uk/service/rss-feeds-775086.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Keep publisher notices and links; agreed licensing credit remains unverified.

Redistribution: Republication needs licensing; general terms restrict network storage accessible to others.

Request hosted display, selected-excerpt retention and report-export permission before relying on these uses.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.independent.co.uk/service/user-policies-a6184151.html). These links are not separate verification dates.

### Policy indian-express

**The Indian Express**: Personal non-commercial; licensed reuse.

[Primary terms/evidence](https://indianexpress.com/terms-and-conditions/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms restrict systematic databases, hosted retrieval, curation and third-party storage. Section 9 expressly addresses AI summarisation and commercial use requiring a binding licence. A public feed or subscription does not establish those rights.

Risk: high. Action: request_permission, legal_review.

### Policy infobae

**Infobae**: Written rightsholder permission.

[Primary terms/evidence](https://www.infobae.com/terminos-y-condiciones/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain copyright and rightsholder notices; agree required credit with permission.

Redistribution: No project-specific onward-sharing or export grant established.

Section 3 reserves reproduction, reuse, public communication and distribution absent express written authorisation. Access does not transfer rights. Obtain a grant covering excerpts, translation, hosting and exports.

Risk: high. Action: request_permission, legal_review.

### Policy insider

**The Insider**: Applicable reuse grant not located.

[Attempted page](https://theins.ru/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official homepage was inspected; no applicable reuse licence was found in the returned content.

Risk: high. Action: request_permission, legal_review.

### Policy insightcrime

**InSight Crime**: Applicable reuse grant not located.

[Attempted page](https://insightcrime.org/about-us/republishing-guidelines/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate republishing route failed; targeted official-domain search did not locate applicable commercial or hosted terms.

Risk: high. Action: request_permission, legal_review.

### Policy intellinews

**bne IntelliNews**: Terms retrieval blocked.

[Attempted page](https://www.intellinews.com/terms/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms page returned 403. Indexed subscription-renewal text does not establish content rights. Commercial/hosted publication and exports remain unverified.

Risk: high. Action: request_permission, legal_review.

### Policy interfax

**Interfax**: Written agreement or narrowly stated statutory uses.

[Primary terms/evidence](https://www.interfax.ru/license). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Permitted electronic uses require a homepage hyperlink in the first paragraph, at least normal text size; graphics have separate credit and no-modification conditions.

Redistribution: No project-specific onward-sharing or export grant established.

Rules distinguish personal copying and purpose-justified quotation from licensed reuse; they expressly reserve press/broadcast/RSS retransmission and require a written agreement for contractual use. No general commercial aggregation grant exists in these rules. Third-party material has its own restrictions.

Risk: high. Action: request_permission, legal_review.

### Policy ioda

**IODA public data**: Terms not extractable from current page.

[Attempted page](https://ioda.inetintel.cc.gatech.edu/resources). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Credit IODA/Georgia Tech and originating measurements pending exact terms.

Redistribution: No verified commercial or hosted redistribution grant.

Resources, About and API documentation returned application shells without legal text. Official Markup Studio/data-download announcement supports analyses and visualisations but establishes no commercial redistribution licence. Live feeds and acknowledgement-gated research paths differ.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://ioda.inetintel.cc.gatech.edu/about/); [reference 2](https://api.ioda.inetintel.cc.gatech.edu/v2/); [reference 3](https://ioda.inetintel.cc.gatech.edu/reports/ioda-markup/). These links are not separate verification dates.

### Policy iranwire

**IranWire**: Personal use; commercial licence required.

[Primary terms/evidence](https://iranwire.com/en/pages/terms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit IranWire and identified contributors; retain linked source.

Redistribution: Commercial reuse requires licence; personal extracts are not an onward-hosting grant.

Terms reserve commercial use and prohibit text/data mining and scraping. Quotation provision does not establish rights for the implemented hosted collector or AI reports.

Risk: high. Action: request_permission, legal_review.

### Policy isw

**Institute for the Study of War**: Prior written permission for dataset/map integration.

[Primary terms/evidence](https://understandingwar.org/fair-use-and-attribution-policy/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Prominent ISW credit accompanies material; preserve logos and disclaimers.

Redistribution: Obtain an explicit grant for shapefiles, datasets, developer notes and analytical integration.

January 2026 policy inspected in official indexed text; direct retrieval returned 403. It requires consent for modification, commercial exploitation and integration into analytical systems, datasets and mapping platforms. Bulk/API redistribution is prohibited without permission; limited published-form sharing/excerpts do not clear this integration.

Risk: high. Action: request_permission, legal_review.

### Policy japan-times

**The Japan Times**: Terms not verified.

[Attempted page](https://www.japantimes.co.jp/terms-of-service/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; commercial/hosted reuse remains unverified.

Risk: high. Action: request_permission, legal_review.

### Policy journa-host

**Journa.host**: Terms not verified.

[Attempted page](https://journa.host/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Instance terms route was inaccessible. User-post commercial/hosted reuse rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy jtwc

**Joint Typhoon Warning Center**: Terms retrieval blocked.

[Attempted page](https://www.metoc.navy.mil/jtwc/jtwc.html). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official public site could not be retrieved. Historical research/partner access is not a commercial public-feed licence; third-party graphics and inputs remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy kyiv-independent

**Kyiv Independent**: Unverified.

[Attempted page](https://kyivindependent.com/terms-of-use/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms candidate could not be retrieved; do not confuse this publisher with The Independent.

Risk: high. Action: request_permission, legal_review.

### Policy launch-library

**The Space Devs Launch Library**: Broad data use with value-added/service conditions.

[Primary terms/evidence](https://github.com/TheSpaceDevs/Tutorials/blob/main/faqs/faq_TSD.md#terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Attribution to The Space Devs is encouraged, not mandatory; retain third-party notices.

Redistribution: Covered data supports value-added hosted use; review onward raw sharing and separate media rights.

Official FAQ permits data use in any form and sharing resulting creations, encouraging added value, local caching and backend client delivery. LL2 free limit is 15 calls/hour/IP. No blanket grant established for linked third-party imagery/webcasts.

Risk: high. Action: attribute, legal_review.

Related evidence: [reference 1](https://github.com/TheSpaceDevs/Tutorials/blob/main/faqs/faq_LL2.md). These links are not separate verification dates.

### Policy lemonde

**Le Monde RSS**: Personal, non-professional and non-collective RSS use.

[Primary terms/evidence](https://www.lemonde.fr/en/about-us/article/2026/03/27/le-monde-rss-feeds_6751860_115.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve Le Monde and author attribution and original link.

Redistribution: Team or commercial republication is outside the personal RSS allowance.

Other RSS exploitation requires authorisation and payment. Verify language-edition/feed scope and saved evidence with syndication.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.lemonde.fr/le-monde-et-vous/article/2025/07/14/les-flux-rss-du-monde-fr_5498778_3237.html). These links are not separate verification dates.

### Policy maariv

**Maariv**: Terms not verified.

[Attempted page](https://www.maariv.co.il/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route could not be opened; reuse grant not verified.

Risk: high. Action: request_permission, legal_review.

### Policy mastodon-social

**Mastodon.social**: Applicable reuse grant not located.

[Attempted page](https://mastodon.social/terms-of-service). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms redirect returned an application shell without substantive terms. User posts remain independently owned; no blanket commercial reuse grant established.

Risk: high. Action: request_permission, legal_review.

### Policy mediazona

**Mediazona**: Applicable reuse grant not located.

[Attempted page](https://zona.media/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official homepage was inspected; no applicable reuse licence was found in the returned content.

Risk: high. Action: request_permission, legal_review.

### Policy meduza

**Meduza**: Unverified.

[Attempted page](https://meduza.io/en/pages/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms candidate inaccessible and primary-domain search did not establish current reuse terms. Ask publisher for the current policy and scope.

Risk: high. Action: request_permission, legal_review.

### Policy mercopress

**MercoPress**: Terms not verified.

[Attempted page](https://www.mercopress.com/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy mexico-news

**Mexico News Daily**: Terms not verified.

[Attempted page](https://mexiconewsdaily.com/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy microsoft-web

**Microsoft website documents**: Informational non-commercial/personal document use.

[Primary terms/evidence](https://www.microsoft.com/en-us/legal/terms-of-use). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain copyright and permission notices required for authorised document copies.

Redistribution: Hosted/modified/commercial excerpts and reports require a suitable separate grant.

Document permission excludes network posting/broadcast and modifications unless another licence applies. Check individual security-blog exceptions rather than extending software licences to articles.

Risk: high. Action: request_permission, legal_review.

### Policy middle-east-eye

**Middle East Eye**: Terms not verified.

[Attempted page](https://www.middleeasteye.net/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route timed out; no rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy mitre

**MITRE ATT&CK**: MITRE ATT&CK licence.

[Primary terms/evidence](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain MITRE copyright designation and full licence in copies.

Redistribution: Research/development/commercial copying permitted with the specified notices.

Trademark/branding and third-party linked reports remain separate.

Risk: low. Action: keep, attribute.

### Policy mixed-evidence

**Mixed or user-supplied evidence**: Per-item rights; no blanket licence.

Status: `per_item_required`. Checked: not verified. Attempted: not attempted.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve originating author/provider, licence and any required notices.

Redistribution: Each selected item retains its own restrictions; combining it into a report grants no new rights.

Applies to uploads, retained feeds, mixed curated assets and web-search evidence. Review source-specific licences, privacy, image rights and onward use.

Risk: high. Action: request_permission, legal_review.

### Policy mixed-osm-wikidata

**Combined OSM/Wikidata/reference assets**: ODbL and CC0 components; curated content unresolved.

[Primary terms/evidence](https://www.openstreetmap.org/copyright). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain OSM contributor/ODbL and source-record provenance; Wikidata structured data is CC0.

Redistribution: Review adapted-database duties, curated-text ownership and linked-media rights separately.

Existing code and resource notes identify OSM breadth, Wikidata coordinates/identities and curated text. Component licences do not establish a single unrestricted grant over every curated record or linked source. Ground-station and entity files contain repository-authored notes; no project-wide content licence was found.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.wikidata.org/wiki/Wikidata:Licensing). These links are not separate verification dates.

### Policy myjoyonline

**MyJoyOnline**: Terms not verified.

[Attempted page](https://www.myjoyonline.com/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy nasa-data

**NASA Earth science products**: NASA-led mission data CC0 unless marked otherwise; contributor exceptions.

[Primary terms/evidence](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use product-specific NASA/LANCE/FIRMS/GIBS credit and dataset citation.

Redistribution: Check each product or contributing source restriction; no blanket NASA-site clearance.

General policy located, but per-product and EONET contributing-source terms need completion. The older Worldview copyright URL was inaccessible in this lookup.

Risk: high. Action: attribute, legal_review.

### Policy nation

**Nation Africa**: Terms not verified.

[Attempted page](https://nation.africa/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy national-uae

**The National**: Personal non-commercial; prior written permission.

[Primary terms/evidence](https://www.thenationalnews.com/terms-and-conditions/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Copyright section restricts storage, redistribution and other website/network use without prior written consent. Publisher and licensed third-party materials have separate ownership.

Risk: high. Action: request_permission, legal_review.

### Policy natural-earth

**Natural Earth**: Public domain.

[Primary terms/evidence](https://www.naturalearthdata.com/about/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit optional; suggested: Made with Natural Earth.

Redistribution: Electronic and printed redistribution and modification permitted.

The provider explicitly permits commercial use. This does not settle third-party overlays or jurisdiction-specific boundary presentation.

Risk: low. Action: keep.

### Policy ncsc

**UK NCSC**: OGL v3 for covered Crown content.

[Primary terms/evidence](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Acknowledge NCSC source and link OGL where possible.

Redistribution: Covered Crown content reusable under OGL; obtain third-party and logo permission separately.

Official indexed terms allow OGL reuse; third-party images/material and logos are excluded. Confirm the exact report notices.

Risk: medium. Action: keep, attribute, legal_review.

### Policy ndtv

**NDTV**: Restricted platform content and automated retrieval.

[Primary terms/evidence](https://drop.ndtv.com/ndtv/common/NDTV-ServiceTerms.pdf). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Current official service terms prohibit copying, storage, publication and systematic retrieval unless expressly permitted. Older general content terms allow personal non-commercial use only. Confirm the exact Hindi RSS and AI summarisation grant before commercial hosting.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://drop.ndtv.com/ndtv/page/terms.html). These links are not separate verification dates.

### Policy newsroom

**Newsroom NZ**: Terms not verified.

[Attempted page](https://newsroom.co.nz/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms retrieval/search was blocked by robots. A donation-site privacy result is not a news-content licence.

Risk: high. Action: request_permission, legal_review.

### Policy nga-navwarnings

**NGA Navigational Warnings**: Applicable legal disclaimer unavailable.

[Attempted page](https://msi.nga.mil/home). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official maritime product description establishes purpose, not reuse rights. MSI legal-disclaimer content could not be retrieved. Do not substitute Digital Nautical Chart terms for NavWarnings.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.nga.mil/resources/Maritime_Safety_Products_and_Services.html). These links are not separate verification dates.

### Policy nikkei

**Nikkei Asia RSS**: Personal, non-commercial headline reading.

[Primary terms/evidence](https://info.asia.nikkei.com/rss). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No onward republication/copying/redistribution grant in the public RSS terms.

Feed terms expressly prohibit republication, copying and redistribution. A subscription does not establish the required separate scope.

Risk: high. Action: request_permission, legal_review.

### Policy nist-nvd

**NIST NVD severity enrichment**: General NIST data terms; NVD-specific API terms unresolved.

[Primary terms/evidence](https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Acknowledge NIST for its data and preserve the selected CVSS metric source/date; confirm the current NVD API notice before display.

Redistribution: Confirm the scope for retained scores, commercial multi-user display and exported evidence.

NIST general terms permit worldwide reuse of its own non-SRD employee-created data with acknowledgement and change notices. They distinguish copyrighted SRD and third-party/extramural works. The NVD developer page returned no readable terms, so this does not clear every NVD-supplied metric. The default CISA enrichment retains the primary/fallback CVSS metric, source and date, potentially from an external CNA. Confirm that contributor scope and current NVD API conditions.

Risk: high. Action: attribute, legal_review.

Related evidence: [reference 1](https://nvd.nist.gov/developers/start-here). These links are not separate verification dates.

### Policy northern-echo

**Northern Echo**: Terms not verified.

[Attempted page](https://www.thenorthernecho.co.uk/terms/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; do not substitute another Newsquest publication policy.

Risk: high. Action: request_permission, legal_review.

### Policy npr

**NPR**: Unverified.

[Attempted page](https://www.npr.org/about-npr/179876898/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms blocked; indexed programme notices reserve rights and refer to permission policy. No current grant verified.

Risk: high. Action: request_permission, legal_review.

### Policy nws

**NOAA National Weather Service data**: Public domain for NWS-produced information unless otherwise noted.

[Primary terms/evidence](https://www.weather.gov/disclaimer). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain notices; credit NWS; do not imply endorsement or present modified data as official.

Redistribution: Lawful reuse permitted for covered NWS data; third-party material requires separate review.

Applies to NWS/NHC/SWPC/tsunami information, not every item hosted anywhere on noaa.gov.

Risk: medium. Action: attribute, legal_review.

### Policy nytimes

**New York Times**: Unverified.

[Attempted page](https://www.nytimes.com/content/help/rights/terms/terms-of-service.html). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms retrieval and primary-domain search blocked. Obtain current terms and RSS syndication permission.

Risk: high. Action: request_permission, legal_review.

### Policy oc-media

**OC Media**: Applicable reuse grant not located.

[Attempted page](https://oc-media.org/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route failed; targeted republishing search did not establish a grant. Partner republication examples are not permission for this project.

Risk: high. Action: request_permission, legal_review.

### Policy ocha-frontline

**OCHA hosted Ukraine front line**: Exact layer licence unavailable.

[Attempted page](https://gis.unocha.org/server/rest/services/Hosted/UKR_Front_Line/FeatureServer/info/iteminfo). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Exact layer metadata could not be retrieved. OCHA guidance requires dataset-specific licences or humanitarian-only designations and says old COD/FOD terms are no longer valid. Hosting and UN boundary disclaimers do not establish commercial rights.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://knowledge.base.unocha.org/wiki/spaces/imtoolbox/pages/157974581/COD+Tutorial+How+to+publish+COD-AB+or+COD-PS+on+HDX). These links are not separate verification dates.

### Policy ofac

**OFAC SDN list**: Applicable reuse grant not located.

[Attempted page](https://ofac.treasury.gov/faqs/topic/1641). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official FAQ and Treasury privacy-page lookup did not establish an endpoint-specific reuse grant. Government affiliation alone is not recorded as permission.

Risk: high. Action: request_permission, legal_review.

### Policy ons

**Office for National Statistics**: OGL for covered content.

[Primary terms/evidence](https://www.ons.gov.uk/help/terms-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain Crown/source and OGL notices; identify changes.

Redistribution: Covered OGL data/content reusable; separately licensed material excluded.

Feed reuse in websites/apps is expressly contemplated. Third-party photos/illustrations/video excluded. Follow fair-use policy; permission needed to charge merely for clicking ONS links.

Risk: medium. Action: keep, attribute, legal_review.

### Policy ooni

**OONI data**: CC BY-NC-SA 4.0.

[Primary terms/evidence](https://github.com/ooni/license/blob/master/data/LICENSE.md). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit OONI, link source and licence, identify changes.

Redistribution: Non-commercial sharing/adaptations subject to attribution and share-alike; no commercial grant verified.

The acknowledgement setting records an operator assertion, not permission. Review whether the actual hosted use is non-commercial and the effect on derived outputs.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://creativecommons.org/licenses/by-nc-sa/4.0/). These links are not separate verification dates.

### Policy open-meteo

**Open-Meteo data and service**: CC BY 4.0 data; free API non-commercial; commercial service subscription.

[Primary terms/evidence](https://open-meteo.com/en/terms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `conditional`.

Attribution: Credit Open-Meteo beside displayed data, link source/licence and identify changes.

Redistribution: Data redistribution is allowed under CC BY 4.0; API subscription/access conditions still apply.

Commercial calls to the free API are not authorised by the open data licence. Paid entitlement is unverified; no current catalogue connector.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://open-meteo.com/en/licence). These links are not separate verification dates.

### Policy openai-search

**OpenAI web-search evidence**: API agreement with third-party rights retained.

[Primary terms/evidence](https://openai.com/policies/services-agreement/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Web-result information shown to users must retain clearly visible clickable inline citations.

Redistribution: Commercial API integration does not itself clear underlying web material; evaluate each item.

Agreement assigns OpenAI rights in output between the parties while prohibiting infringement of third-party rights. It does not give a blanket licence to copy discovered pages or photographs. Inspect the actual account agreement and original publishers for retained excerpts and exports.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://openai.com/policies/service-terms/); [reference 2](https://developers.openai.com/api/docs/guides/tools-web-search). These links are not separate verification dates.

### Policy openalex

**OpenAlex metadata**: CC0 metadata; service tiers separate.

[Primary terms/evidence](https://help.openalex.org/access/overview/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: OpenAlex provenance recommended; retain original publication/DOI references.

Redistribution: Metadata reuse permitted; this does not relicense linked full text or images.

Data openness does not establish a particular API tier or allowance.

Risk: medium. Action: keep, attribute.

### Policy openaq

**OpenAQ API and underlying observations**: Provider-specific data rights and platform restrictions.

[Primary terms/evidence](https://docs.openaq.org/about/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Credit OpenAQ and original providers as their terms require; retain source links.

Redistribution: Do not treat open-source API software as a grant over all observations or unrestricted hosted-service use.

Platform terms require registered authorised access, prohibit API-key transfer and services substantially duplicating/competing with OpenAQ. Underlying providers have distinct terms and OpenAQ gives no blanket assurance of their rights. Exact observations require provider-level licence checks.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://openaq.org/terms/). These links are not separate verification dates.

### Policy openfreemap

**OpenFreeMap maps**: Commercial use stated; OSM/ODbL and OpenMapTiles rights remain.

[Primary terms/evidence](https://openfreemap.org/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: OpenFreeMap (optional), © OpenMapTiles, Data from OpenStreetMap; retain links and printed/export credit.

Redistribution: Observe underlying data/style licences and ODbL. Service terms do not grant unrestricted bulk extraction.

Commercial web/app maps expressly contemplated. Public service has no SLA; reconcile automated bulk collection with service terms. Existing image export must retain credits.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://openfreemap.org/tos/); [reference 2](https://www.openstreetmap.org/copyright). These links are not separate verification dates.

### Policy opensanctions

**OpenSanctions**: Public CC BY-NC 4.0; separate API/bulk commercial contracts.

[Primary terms/evidence](https://www.opensanctions.org/docs/commercial/exemption/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: CC credit/link/change notice for public data; confirm paid-contract requirements.

Redistribution: Bulk internal, bulk reseller and API grants differ. Substantial standalone dataset redistribution is restricted.

Current paid API terms contemplate customer-facing products; do not apply the bulk internal-only rule to that contract. No purchased entitlement or catalogue connector verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.opensanctions.org/docs/terms/data/202509/); [reference 2](https://www.opensanctions.org/docs/terms/api/202609/); [reference 3](https://www.opensanctions.org/docs/commercial/exemption/). These links are not separate verification dates.

### Policy oryx

**Oryx equipment losses**: Applicable reuse grant not located.

[Attempted page](https://www.oryxspioenkop.com/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official site has an Oryx copyright notice; no commercial, hosted-republication or dataset redistribution grant was located. Public article and linked evidence do not clear third-party media.

Risk: high. Action: request_permission, legal_review.

### Policy osiris-curated

**OSIRIS-derived mixed camera catalogue**: MIT for copied software/catalogue; camera rights separate.

[Primary terms/evidence](https://github.com/simplifaisoul/osiris/blob/fac8d1b/LICENSE). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain simplifaisoul 2026 MIT notice for copied catalogue/software and each operator provenance.

Redistribution: Do not extend catalogue MIT to linked images or streams; record owner-specific delivery rights.

Pinned upstream licence inspected and local camera NOTICE/CAMERA_WORLD scope checked. MIT supports reuse of covered copied material with notice, but does not grant underlying owners image, stream, poster, recording or export rights. Curated regions mix YouTube, Skyline links and other operators.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.youtube.com/static?template=terms); [reference 2](https://www.skylinewebcams.com/terms-of-use.html). These links are not separate verification dates.

### Policy osm

**OpenStreetMap data**: ODbL 1.0.

[Primary terms/evidence](https://www.openstreetmap.org/copyright). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: © OpenStreetMap contributors; link copyright/ODbL and preserve required notices.

Redistribution: Data/derivative-database share-alike conditions differ from produced-work image attribution.

Data rights do not grant unlimited use of OSM or third-party tile/geocoding/routing servers. Review service policy separately.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://opendatacommons.org/licenses/odbl/1-0/). These links are not separate verification dates.

### Policy osm-service

**OSM-derived public service**: ODbL data; service entitlement not reviewed.

[Primary terms/evidence](https://www.openstreetmap.org/copyright). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve OpenStreetMap and service attribution.

Redistribution: Data licence does not settle hosted service quotas, result caching or redistribution.

Photon/Valhalla/Overpass are separate operators. Review exact public-instance terms or self-host before approving commercial service use.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://github.com/komoot/photon); [reference 2](https://valhalla.openstreetmap.de/). These links are not separate verification dates.

### Policy paloalto

**Palo Alto Networks / Unit 42**: Personal non-commercial internal content use; separate agreements.

[Primary terms/evidence](https://www.paloaltonetworks.com/legal-notices/terms-of-use). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

General site terms restrict ordinary access to single-copy personal/non-commercial internal use. Check any specific Unit 42 blog permission or existing business contract; none verified.

Risk: high. Action: request_permission, legal_review.

### Policy parliament

**UK Parliament**: Open Parliament Licence v3.0.

[Primary terms/evidence](https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Contains Parliamentary information licensed under the Open Parliament Licence v3.0. Link licence where possible.

Redistribution: Covered information can be reused under OPL v3.0; no official status or endorsement.

Commercial products, copying, publishing, distribution and adaptation of covered Parliamentary information are allowed. Personal data, unreleased information, marks and unauthorised third-party rights are excluded.

Risk: high. Action: attribute, legal_review.

### Policy pbs

**PBS NewsHour**: Terms not verified.

[Attempted page](https://www.pbs.org/about/about-pbs/terms-of-use/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms route returned 403; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy pravda

**Ukrainska Pravda**: Conditional online quotation/reuse; commercial access restriction.

[Primary terms/evidence](https://www.pravda.com.ua/eng/rules/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Visible source and hyperlink by second paragraph or on first screen.

Redistribution: Do not assume the online-publication allowance authorises charging for excerpts or exported third-party content.

Free online-publication reuse has source/link conditions, but commercial access exploitation is prohibited. Interfax-Ukraine material and Getty media explicitly excluded. Clarify paid OSINT/report scope.

Risk: high. Action: request_permission, legal_review.

### Policy premium-times

**Premium Times**: Terms not verified.

[Attempted page](https://www.premiumtimesng.com/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy publico

**Publico**: Terms not verified.

[Attempted page](https://www.publico.pt/termos-e-condicoes). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy radio-okapi

**Radio Okapi**: Applicable reuse grant not located.

[Attempted page](https://www.radiookapi.net/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official homepage inspected; candidate conditions route failed and no applicable reuse licence established.

Risk: high. Action: request_permission, legal_review.

### Policy ransomware-live

**Ransomware.live**: Official announcement restricts raw redistribution.

[Primary terms/evidence](https://www.linkedin.com/posts/ransomwarelive_ransomware-cti-threatintelligence-activity-7495041175930888193-G25S). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Official provider page demands attribution; confirm exact required wording.

Redistribution: Raw-data republication/API redistribution requires explicit permission; full terms remain unavailable.

Provider announcement requires clients to use the integrating product backend and written permission for publishing raw data or another API/feed. Linked full terms could not be resolved. Commercial derivative scope, exact fair-use limits and third-party media remain unresolved.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.linkedin.com/company/ransomwarelive). These links are not separate verification dates.

### Policy rappler

**Rappler**: Terms not verified.

[Attempted page](https://www.rappler.com/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy rbi

**Reserve Bank of India**: Restricted caching, linking and framing.

[Primary terms/evidence](https://www.rbi.org.in/Scripts/Disclaimer.aspx). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Disclaimer prohibits caching/framing except authorised uses; home-page linking requires notification and internal links require permission. No broader commercial reproduction licence verified.

Risk: high. Action: request_permission, legal_review.

### Policy rdap

**RDAP discovery and registry responses**: Terms not verified.

[Attempted page](https://www.iana.org/rdap). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

IANA discovery and candidate terms routes failed. Each responding registry may apply its own terms and privacy limits; bootstrap discovery is not a blanket registry-data licence.

Risk: high. Action: request_permission, legal_review.

### Policy reach-manchester

**Manchester Evening News**: Unverified.

[Attempted page](https://www.manchestereveningnews.co.uk/terms-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms redirected to an inaccessible Tollbit page; primary-domain search did not establish reuse rights.

Risk: high. Action: request_permission, legal_review.

### Policy record

**The Record**: Applicable reuse grant not located.

[Attempted page](https://therecord.media/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Homepage links privacy and contact, but no content licence was established; attempted terms-of-use route failed.

Risk: high. Action: request_permission, legal_review.

### Policy reddit

**Reddit Data API**: Data API Terms and Responsible Builder Policy.

[Primary terms/evidence](https://redditinc.com/policies/data-api-terms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Developer-policy attribution and owner restrictions; exact display specification needs review.

Redistribution: Only approved app use; limited display rights are not general resale or independent redistribution.

Current policy requires API approval and written commercial approval. Retention, deletion and sensitive inference need review. No current catalogue connector.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy). These links are not separate verification dates.

### Policy reliefweb

**ReliefWeb**: Unverified.

[Attempted page](https://reliefweb.int/terms-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Current terms page returned a JavaScript human-verification challenge. API appname approval does not settle originating report publishers or onward reuse.

Risk: high. Action: request_permission, legal_review.

### Policy rfi

**RFI**: Terms not verified.

[Attempted page](https://www.rfi.fr/en/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official-domain search/retrieval was robots-blocked. Historic RSS instructions do not establish current commercial redistribution rights.

Risk: high. Action: request_permission, legal_review.

### Policy russia-mfa

**Russian Ministry of Foreign Affairs**: Terms not verified.

[Attempted page](https://mid.ru/ru/about/copyright/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate copyright route was inaccessible; commercial and hosted reuse not verified.

Risk: high. Action: request_permission, legal_review.

### Policy russianwarship

**General Staff figures via russianwarship.rip**: Mirror/API reuse grant not established.

[Attempted page](https://russianwarship.rip/en). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official site credits General Staff and offers a widget, but neither establishes broad commercial/API redistribution. API documentation returned no readable terms. Intermediary service rights and accompanying graphics need separate review.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://russianwarship.rip/en/widget); [reference 2](https://russianwarship.rip/api-documentation/v2). These links are not separate verification dates.

### Policy sabc

**SABC News**: Terms not verified.

[Attempted page](https://www.sabcnews.com/sabcnews/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy sans-isc

**SANS Internet Storm Center**: Applicable reuse grant not located.

[Attempted page](https://isc.sans.edu/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official homepage showed copyright and privacy links; candidate terms route failed. API availability does not establish a diary-content reuse licence.

Risk: high. Action: request_permission, legal_review.

### Policy scmp

**South China Morning Post**: Personal, non-commercial access; written permission for reuse.

[Primary terms/evidence](https://www.scmp.com/terms-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: Written permission required for copying/distribution and restricted automated/AI uses; third-party rights remain.

15 September 2026 terms section 3 covers extracts and metadata, automated collection, analytics and AI/RAG. Primary indexed terms retrieved after direct fetch failed; no exception verified.

Risk: high. Action: request_permission, legal_review.

### Policy sec

**SEC/EDGAR**: Public-information dissemination; third-party rights review.

[Primary terms/evidence](https://www.sec.gov/about/privacy-information). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Cite SEC; no seal/logo use or implied affiliation.

Redistribution: SEC dissemination permission does not itself settle copyright in company-authored attachments.

SEC permits copying/distribution of website information without its permission. This does not establish that every third-party filing attachment is copyright-free. Review fair-access policy and exact document rights.

Risk: high. Action: request_permission, legal_review.

### Policy sky

**Sky News**: Terms not verified.

[Attempted page](https://news.sky.com/info/policies-and-standards/terms-and-conditions). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy sslmate

**SSLMate Certificate Transparency search**: Terms not verified.

[Attempted page](https://sslmate.com/ct_search_api/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate API terms and general terms routes failed; no product-specific commercial/export rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy state-travel

**US Consular Affairs advisories**: Public domain unless copyrighted.

[Primary terms/evidence](https://travel.state.gov/content/travel/en/copyright-disclaimer.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit Bureau of Consular Affairs, US State Department; retain third-party credits.

Redistribution: Unmarked covered information may be copied/distributed; inspect item/photo notices.

Policy permits copying/distribution of unmarked site information. Many photographs are copyrighted and require owner permission; Country Commercial Guides have separate international copyright. Linked sites are not cleared.

Risk: high. Action: attribute, legal_review.

### Policy stv

**STV News**: Applicable reuse grant not located.

[Attempted page](https://news.stv.tv/terms-of-use). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official terms route displayed its heading and navigation without readable substantive terms. No permission inferred from the empty page.

Risk: high. Action: request_permission, legal_review.

### Policy talos

**Cisco Talos blog**: Applicable reuse grant not located.

[Attempted page](https://blog.talosintelligence.com/). Status: `lookup_inconclusive`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Blog footer did not establish a reuse policy. Cisco.com general terms were inspected but their scope cannot automatically be extended to this separate blog domain.

Risk: high. Action: request_permission, legal_review.

### Policy tass

**TASS text and RSS**: Restricted non-commercial excerpts; paid use by agreement.

[Primary terms/evidence](https://tass.com/terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: TASS credit and active original-page link at the start, subject to detailed format rules.

Redistribution: No unrestricted commercial collection/republication or media-rights grant.

RSS is explicitly covered. Free text use is limited to permitted non-commercial cases and at most 30% of quoted material, unchanged. Paid access/advertising-supported use needs an agreement.

Risk: high. Action: request_permission, legal_review.

### Policy tehran-times

**Tehran Times**: Terms not verified.

[Attempted page](https://www.tehrantimes.com/page/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; reuse grant not verified.

Risk: high. Action: request_permission, legal_review.

### Policy telegram

**Telegram content**: Restricted platform content licence; owner rights remain.

[Primary terms/evidence](https://telegram.org/tos/content-licensing). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain channel/author and post link; credit is not permission.

Redistribution: Non-standard access and transfer restricted. Content-owner conditions apply separately.

The current terms broadly prohibit scraping/aggregation and use for AI development, enhancement or deployment without specific consent. Legal review needed for existing collectors, model input and frozen report evidence.

Risk: high. Action: legal_review, request_permission, replace.

### Policy the-bell

**The Bell**: Subscription restrictions; public RSS unresolved.

[Primary terms/evidence](https://en.thebell.io/terms-of-service/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

October 2024 subscription terms prohibit sharing subscription content commercially or non-commercially. They do not establish a public RSS republication licence. Obtain endpoint-specific rights instead of treating a subscription as permission.

Risk: high. Action: request_permission, legal_review.

### Policy tilezen-terrain

**Tilezen/Mapzen terrain**: Multiple terrain provider licences.

[Primary terms/evidence](https://github.com/tilezen/joerd/blob/master/docs/attribution.md). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain the complete applicable terrain provider attribution set and hosted-service credit.

Redistribution: Review the exact tile endpoint, constituent datasets and derivative/export obligations.

Official project attribution file requires multiple source credits and directs users to investigate each data provider. Hosted-service credit differs from underlying data. No single global product/export grant inferred.

Risk: high. Action: request_permission, legal_review.

### Policy times-israel

**Times of Israel**: Personal, non-commercial use.

[Primary terms/evidence](https://www.timesofisrael.com/terms/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source and additional copyright notices.

Redistribution: Hosted/team reuse and report exports need express permission beyond personal access.

Other storage, catalogue, copying, republication and derivatives require express written permission. AP material has separate restrictions.

Risk: high. Action: request_permission, legal_review.

### Policy timesca

**The Times of Central Asia**: Terms not verified.

[Attempted page](https://timesca.com/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; no current reuse rights verified.

Risk: high. Action: request_permission, legal_review.

### Policy trt

**TRT Haber**: Terms not verified.

[Attempted page](https://www.trthaber.com/kurumsal/kullanim-kosullari.html). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; reuse grant not verified.

Risk: high. Action: request_permission, legal_review.

### Policy ucdp

**UCDP candidate events**: CC BY 4.0 unless otherwise noted.

[Primary terms/evidence](https://www.uu.se/en/department/peace-and-conflict-research/research/ucdp/frequently-asked-questions.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Use the dataset preferred citation, licence and change notice.

Redistribution: Covered data may be shared/adapted; preserve source/licence metadata and exceptions.

FAQ updated May 2026 expressly identifies CC BY 4.0 and dataset-specific citations. Commercial hosted reuse is conditional on exceptions and attribution. API operational terms and underlying news/media rights are separate.

Risk: high. Action: attribute, legal_review.

### Policy ukrinform

**Ukrinform**: Terms not verified.

[Attempted page](https://www.ukrinform.net/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Candidate terms route was inaccessible; reuse grant not verified.

Risk: high. Action: request_permission, legal_review.

### Policy un-web

**United Nations web material**: Unverified.

[Attempted page](https://www.un.org/en/about-us/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms/copyright pages returned 403. News, press, sanctions and OHCHR products can differ; do not infer public-domain or blanket rights from UN origin.

Risk: high. Action: request_permission, legal_review.

### Policy unknown-publisher

**Publisher rights not reviewed**: Not established.

Status: `not_reviewed`. Checked: not verified. Attempted: not attempted.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain publisher, author, date and original link; this is not a licence.

Redistribution: No republication, export or retained-excerpt grant established.

RSS availability and a source link do not establish commercial, hosted, AI or republication rights. Review this publisher and underlying contributors individually.

Risk: high. Action: request_permission, legal_review.

### Policy unknown-source

**Provider rights not reviewed**: Not established.

Status: `not_reviewed`. Checked: not verified. Attempted: not attempted.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source identity and record-level credits pending review.

Redistribution: No onward-reuse grant established.

Existing code licence notes are leads, not independently verified rights. Review the exact data product, service contract and intended use.

Risk: high. Action: request_permission, legal_review.

### Policy us-dod

**US Department of Defense news**: Terms not verified.

[Attempted page](https://www.defense.gov/Resources/DOD-Imagery/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official candidate image-policy retrieval failed; no whole-feed reuse grant inferred from government affiliation.

Risk: high. Action: request_permission, legal_review.

### Policy usgs

**USGS-produced data**: US public-domain USGS-produced data; third-party exceptions.

[Primary terms/evidence](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit USGS and retain third-party notices where present.

Redistribution: USGS-produced information reusable; non-USGS images and other supplied materials can retain copyright.

This assessment covers earthquake observations, not a blanket licence for every linked page or image.

Risk: medium. Action: keep, attribute, legal_review.

### Policy viina

**VIINA territorial-control data**: ODbL 1.0; database contents licence.

[Primary terms/evidence](https://github.com/zhukovyuri/VIINA). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain VIINA notices and follow the README citation requirements.

Redistribution: ODbL attribution/share-alike and access to adapted databases may apply to public outputs.

Review the exact adapted snapshot and report exports. Linked publishers retain separate article rights.

Risk: medium. Action: attribute, legal_review.

### Policy wales-online

**Wales Online**: Terms not verified.

[Attempted page](https://www.walesonline.co.uk/terms-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official terms route returned 402; exact publication rights remain unverified.

Risk: high. Action: request_permission, legal_review.

### Policy warspotting

**WarSpotting**: Nonprofit research/news reuse; contact for commercial use.

[Primary terms/evidence](https://ukr.warspotting.net/about/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Appropriate WarSpotting credit, such as a link; retain underlying media credits.

Redistribution: Commercial hosting/export scope must be agreed; independently clear evidence images.

FAQ permits credited nonprofit research, academia and news reporting and requests API use instead of scraping. Commercial users must contact first. Dataset permission does not establish ownership of photo evidence.

Risk: high. Action: request_permission, legal_review.

### Policy whitehouse

**White House**: Government-produced material; assigned copyrights may remain.

[Primary terms/evidence](https://www.whitehouse.gov/copyright/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain source, author and any assigned copyright notices; avoid implied endorsement.

Redistribution: Only covered government-produced material without other rights restrictions.

Official policy says government-produced site materials are not copyright protected, but the government can hold assigned rights. Check the actual item and third-party/mark rights rather than treating the whole host as public domain.

Risk: high. Action: attribute, legal_review.

### Policy who

**WHO publications**: CC BY-NC-SA 3.0 IGO where designated; commercial permission.

[Primary terms/evidence](https://www.who.int/about/policies/publishing/copyright). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: WHO title, publication place/year, source and licence; adaptations/translations need specified disclaimers.

Redistribution: Only designated non-commercial reuse under published conditions; no commercial grant verified.

Commercial use requires permission. Confirm Disease Outbreak News product-specific notice; other WHO publication/classification licences differ, and third-party material remains separate.

Risk: high. Action: request_permission, legal_review.

### Policy wikidata-mixed

**Wikidata plus separately licensed media**: Structured data CC0; other text/media separate.

[Primary terms/evidence](https://www.wikidata.org/wiki/Wikidata:Licensing). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Wikidata credit useful; preserve individual Commons author/licence/change notices.

Redistribution: CC0 facts do not license linked portraits, photographs, prose or curated source material.

Review every included image and seed source before approving the whole mixed catalogue. Do not label the complete asset CC0.

Risk: high. Action: attribute, legal_review.

### Policy wikidata-structured

**Wikidata structured-data enrichment**: CC0 for structured data.

[Primary terms/evidence](https://www.wikidata.org/wiki/Wikidata:Licensing). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain Wikidata entity identifiers and provenance; credit is useful, not a CC0 attribution obligation.

Redistribution: Structured facts may be reused commercially. This does not cover linked media or separately licensed prose.

Scope only to structured entity data, not every resource reached through its links.

Risk: medium. Action: attribute, legal_review.

### Policy world-bank

**World Bank indicators**: CC BY 4.0 with dataset exceptions and additional terms.

[Primary terms/evidence](https://data.worldbank.org/summary-terms-of-use). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit World Bank, dataset and original data provider; pass acknowledgement requirements downstream.

Redistribution: Conditional for covered indicators; third-party/restricted data can require additional permission.

Summary expressly permits commercial products, adaptation and sharing unless indicator metadata states otherwise. Additional dispute terms apply. Linked full dataset terms redirected to general terms, so retain this limit and check the exact dataset before deployment.

Risk: high. Action: attribute, legal_review.

Related evidence: [reference 1](https://www.worldbank.org/ext/en/legal/terms-conditions). These links are not separate verification dates.

### Policy wri-power

**WRI Global Power Plant Database**: CC BY 4.0 (database); MIT (code).

[Primary terms/evidence](https://github.com/wri/global-power-plant-database). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit WRI Global Power Plant Database and link licence/source.

Redistribution: Database reuse with CC BY conditions; retain provenance and identify alterations.

Latest published database version is 1.3.0; maintenance stopped. Software MIT is separate from data rights.

Risk: medium. Action: attribute, legal_review.

### Policy wto

**World Trade Organization**: Unverified.

[Attempted page](https://www.wto.org/english/res_e/copyright_e.htm). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary copyright candidate inaccessible; official contact page returned 402. No current publication/RSS commercial terms verified.

Risk: high. Action: request_permission, legal_review.

### Policy youtube

**YouTube Data API metadata**: YouTube API terms and developer policies.

[Primary terms/evidence](https://developers.google.com/youtube/terms/developer-policies). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: YouTube-required branding/links and uploader attribution; review exact presentation.

Redistribution: Non-authorised API data requires delete/refresh within 30 days; redistribution and independent media reuse are not blanket permissions.

Review saved evidence, exports, retention/deletion and application privacy/terms before approving use. A key alone does not establish compliance.

Risk: high. Action: attribute, legal_review.

## Camera host review queue

All 120 configured media/frame hosts retain the [camera-owner-rights](#policy-camera-owner-rights) policy. This is an allowlist inventory, not evidence that every camera on a host is authorised. No live stream was fetched. Provider-policy evidence is a separate reference and does not clear every camera owner or delivery method. Confirm embedding, proxying, recording, export and commercial terms separately.

| Host | Configured use | Owner rights | Provider-policy evidence |
| --- | --- | --- | --- |
| `511.alaska.gov` | media | unknown | [camera-alaska](#policy-camera-alaska) |
| `511.alberta.ca` | media | unknown | [camera-alberta](#policy-camera-alberta) |
| `511.gnb.ca` | media | unknown | [camera-newbrunswick](#policy-camera-newbrunswick) |
| `511.idaho.gov` | media | unknown | [camera-idaho](#policy-camera-idaho) |
| `511.novascotia.ca` | media | unknown | [camera-novascotia](#policy-camera-novascotia) |
| `511ga.org` | media | unknown | [camera-georgia](#policy-camera-georgia) |
| `511in.org` | media | unknown | [camera-indiana](#policy-camera-indiana) |
| `511la.org` | media | unknown | [camera-louisiana](#policy-camera-louisiana) |
| `511nl.ca` | media | unknown | [camera-newfoundland](#policy-camera-newfoundland) |
| `511ny.org` | media | unknown | [camera-newyork](#policy-camera-newyork) |
| `511on.ca` | media | unknown | [camera-ontario](#policy-camera-ontario) |
| `511yukon.ca` | media | unknown | [camera-yukon](#policy-camera-yukon) |
| `apps.derbyshire.gov.uk` | media | unknown | [camera-derbyshire](#policy-camera-derbyshire) |
| `atmsqf.iowadot.gov` | media | unknown | [camera-iowa](#policy-camera-iowa) |
| `az511.gov` | media | unknown | [camera-arizona](#policy-camera-arizona) |
| `cam.river.go.jp` | media | unknown | [camera-river-japan](#policy-camera-river-japan) |
| `cameras.qldtraffic.qld.gov.au` | media | unknown | [camera-queensland](#policy-camera-queensland) |
| `camsecure.co` | media | unknown | [camera-camsecure](#policy-camera-camsecure) |
| `cctv-ss01.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cctv-ss02.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cctv-ss03.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cctv-ss04.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cctv-ss05.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cctv-ss06.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cctv-ss07.thb.gov.tw` | media | unknown | [camera-taiwan](#policy-camera-taiwan) |
| `cdn.uab.org` | media | unknown | [camera-uab](#policy-camera-uab) |
| `cdnuiwebcams.utinform.hu` | media | unknown | [camera-hungary](#policy-camera-hungary) |
| `ctroads.org` | media | unknown | [camera-connecticut](#policy-camera-connecticut) |
| `cwwp2.dot.ca.gov` | media | unknown | [camera-caltrans](#policy-camera-caltrans) |
| `d1wse1.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d1wse2.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d1wse3.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d1wse4.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d1wse5.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d2wse1.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d2wse2.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `d3wse1.its.nv.gov` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `dcc.ussgroup.co.uk` | media | unknown | [camera-uss](#policy-camera-uss) |
| `download.data.grandlyon.com` | media | unknown | [camera-lyon](#policy-camera-lyon) |
| `drivebc.ca` | media | unknown | [camera-drivebc](#policy-camera-drivebc) |
| `drivenc.gov` | media | unknown | [camera-northcarolina](#policy-camera-northcarolina) |
| `eismoinfo.lt` | media | unknown | [camera-lithuania](#policy-camera-lithuania) |
| `etraffic.dgt.es` | media | unknown | [camera-dgt](#policy-camera-dgt) |
| `files.argyll-bute.gov.uk` | media | unknown | [camera-argyll](#policy-camera-argyll) |
| `fl511.com` | media | unknown | [camera-florida](#policy-camera-florida) |
| `gsccam.butlersheriff.org` | media | unknown | [camera-butler](#policy-camera-butler) |
| `home-solutions.bg` | media | unknown | [camera-home-solutions](#policy-camera-home-solutions) |
| `hotline.gov.sk.ca` | media | unknown | [camera-saskatchewan](#policy-camera-saskatchewan) |
| `images.data.gov.sg` | media | unknown | [camera-singapore](#policy-camera-singapore) |
| `images.drivebc.ca` | media | unknown | [camera-drivebc](#policy-camera-drivebc) |
| `images.gov.im` | media | unknown | [camera-isleofman](#policy-camera-isleofman) |
| `images.wsdot.wa.gov` | media | unknown | [camera-wsdot](#policy-camera-wsdot) |
| `infocar.dgt.es` | media | unknown | [camera-dgt](#policy-camera-dgt) |
| `informo.madrid.es` | media | unknown | [camera-madrid](#policy-camera-madrid) |
| `ipcamlive.com` | frames | unknown | [camera-ipcamlive](#policy-camera-ipcamlive) |
| `irecam.carsprogram.org` | media | unknown | [camera-ireland](#policy-camera-ireland) |
| `its.act.pr.gov` | media | unknown | [camera-puertorico](#policy-camera-puertorico) |
| `itsstreamingbr.dotd.la.gov` | media | unknown | [camera-louisiana](#policy-camera-louisiana) |
| `itsstreamingbr2.dotd.la.gov` | media | unknown | [camera-louisiana](#policy-camera-louisiana) |
| `itsstreamingno.dotd.la.gov` | media | unknown | [camera-louisiana](#policy-camera-louisiana) |
| `kamera.atlas.vegvesen.no` | media | unknown | [camera-norway](#policy-camera-norway) |
| `kamera.vegvesen.no` | media | unknown | [camera-norway](#policy-camera-norway) |
| `kamere.amss.org.rs` | media | unknown | [camera-amss](#policy-camera-amss) |
| `kscam.carsprogram.org` | media | unknown | [camera-kansas](#policy-camera-kansas) |
| `ls.tkchopin.pl` | media | unknown | [camera-tkchopin](#policy-camera-tkchopin) |
| `meteo.chavo.biz` | media | unknown | [camera-chavo](#policy-camera-chavo) |
| `micamerasimages.net` | media | unknown | [camera-michigan](#policy-camera-michigan) |
| `netrafficcams.co.uk` | media | unknown | [camera-northeast](#policy-camera-northeast) |
| `newengland511.org` | media | unknown | [camera-newengland](#policy-camera-newengland) |
| `opendata.toronto.ca` | media | unknown | [camera-toronto](#policy-camera-toronto) |
| `pics.smartburgas.eu` | media | unknown | [camera-smartburgas](#policy-camera-smartburgas) |
| `prod-ut.ibi511.com` | media | unknown | [camera-utah](#policy-camera-utah) |
| `public.carsprogram.org` | media | unknown | [camera-carsprogram](#policy-camera-carsprogram) |
| `ristmikud.tallinn.ee` | media | unknown | [camera-tallinn](#policy-camera-tallinn) |
| `s3-eu-west-1.amazonaws.com` | media | unknown | [camera-tfl](#policy-camera-tfl) |
| `s51.nysdot.skyvdn.com` | media | unknown | [camera-newyork](#policy-camera-newyork) |
| `s52.nysdot.skyvdn.com` | media | unknown | [camera-newyork](#policy-camera-newyork) |
| `s53.nysdot.skyvdn.com` | media | unknown | [camera-newyork](#policy-camera-newyork) |
| `s7.nysdot.skyvdn.com` | media | unknown | [camera-newyork](#policy-camera-newyork) |
| `s9.nysdot.skyvdn.com` | media | unknown | [camera-newyork](#policy-camera-newyork) |
| `skysfs4.trafficwise.org` | media | unknown | [camera-indiana](#policy-camera-indiana) |
| `stream.inmoves.nl` | media | unknown | [camera-inmoves](#policy-camera-inmoves) |
| `stream.uzivobeograd.rs` | media | unknown | [camera-uzivo](#policy-camera-uzivo) |
| `stream1.mgw-is.uk` | media | unknown | [camera-mgw](#policy-camera-mgw) |
| `stream2.mgw-is.uk` | media | unknown | [camera-mgw](#policy-camera-mgw) |
| `streaming1.neotel.net.mk` | media | unknown | [camera-neotel](#policy-camera-neotel) |
| `tarktee.transpordiamet.ee` | media | unknown | [camera-estonia](#policy-camera-estonia) |
| `tdcctv.data.one.gov.hk` | media | unknown | [camera-hongkong](#policy-camera-hongkong) |
| `towercam.butlersheriff.org` | media | unknown | [camera-butler](#policy-camera-butler) |
| `traffic.ottawa.ca` | media | unknown | [camera-ottawa](#policy-camera-ottawa) |
| `trafficnz.info` | media | unknown | [camera-nzta](#policy-camera-nzta) |
| `travelmidwest.com` | media | unknown | [camera-illinois](#policy-camera-illinois) |
| `tripcheck.com` | media | unknown | [camera-oregon](#policy-camera-oregon) |
| `vefmyndavelar.vegagerdin.is` | media | unknown | [camera-iceland](#policy-camera-iceland) |
| `video.autostrade.it` | media | unknown | [camera-autostrade](#policy-camera-autostrade) |
| `video.dot.state.mn.us` | media | unknown | [camera-minnesota](#policy-camera-minnesota) |
| `ville.montreal.qc.ca` | media | unknown | [camera-montreal](#policy-camera-montreal) |
| `wc-heli.chuv.ch` | media | unknown | [camera-chuv](#policy-camera-chuv) |
| `weathercam.digitraffic.fi` | media | unknown | [camera-fintraffic](#policy-camera-fintraffic) |
| `webcams.asfinag.at` | media | unknown | [camera-asfinag](#policy-camera-asfinag) |
| `webcams.transport.nsw.gov.au` | media | unknown | [camera-nsw](#policy-camera-nsw) |
| `www.511pa.com` | media | unknown | [camera-pennsylvania](#policy-camera-pennsylvania) |
| `www.cita.lu` | media | unknown | [camera-luxembourg](#policy-camera-luxembourg) |
| `www.cne-siar.gov.uk` | media | unknown | [camera-western-isles](#policy-camera-western-isles) |
| `www.dgt.es` | media | unknown | [camera-dgt](#policy-camera-dgt) |
| `www.drivebc.ca` | media | unknown | [camera-drivebc](#policy-camera-drivebc) |
| `www.drivenc.gov` | media | unknown | [camera-northcarolina](#policy-camera-northcarolina) |
| `www.kcscout.net` | media | unknown | [camera-kcscout](#policy-camera-kcscout) |
| `www.manitoba511.ca` | media | unknown | [camera-manitoba](#policy-camera-manitoba) |
| `www.northyorks.gov.uk` | media | unknown | [camera-northyorkshire](#policy-camera-northyorkshire) |
| `www.nvroads.com` | media | unknown | [camera-nevada](#policy-camera-nevada) |
| `www.quebec511.info` | media | unknown | [camera-quebec](#policy-camera-quebec) |
| `www.slupsk.pl` | media | unknown | [camera-slupsk](#policy-camera-slupsk) |
| `www.tamarcrossings.org.uk` | media | unknown | [camera-tamar](#policy-camera-tamar) |
| `www.travelmidwest.com` | media | unknown | [camera-illinois](#policy-camera-illinois) |
| `www.tripcheck.com` | media | unknown | [camera-oregon](#policy-camera-oregon) |
| `www.vegagerdin.is` | media | unknown | [camera-iceland](#policy-camera-iceland) |
| `www.westmorlandandfurness.gov.uk` | media | unknown | [camera-westmorland](#policy-camera-westmorland) |
| `www.youtube.com` | frames | unknown | [camera-youtube](#policy-camera-youtube) |
| `wzmedia.dot.ca.gov` | media | unknown | [camera-caltrans](#policy-camera-caltrans) |

## Maintenance

Review JSON changes by source ID; never copy a permissive policy solely because another product uses the same provider. Keep grants and correspondence in controlled records, with a non-sensitive reference if needed. Recheck terms before a commercial release and when a provider, product, endpoint or licence changes.

Regenerate this file with `python scripts/render_source_licences.py`; verify it with `--check`. Run `uv run pytest tests/test_source_licences.py --no-cov` in `backend`. Adding a catalogue ID without an explicit row must fail. No network lookup occurs during these checks.

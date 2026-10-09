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
null. `upstream_licence_note` preserves an existing code claim as an unverified lead.
These files are inventory only; KAN-195 owns runtime enforcement and KAN-165 owns
the public attribution presentation. Consumers must not interpret unknown or
permission-required records as approved, or treat conditional records as proof
that this deployment satisfies the conditions.

`terms_checked` means the cited terms were inspected, not that an agreement exists.
`partial_review` identifies narrower evidence or unresolved product rights.
`lookup_blocked` dates an attempted lookup only; `not_reviewed` has no terms-check
or attempted-lookup date. The code inventory date is separate from all of these.
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
   before treating any of them as commercially cleared. IODA's failed lookup must
   be resolved; its existing live feeds have different gates from research.

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

Inventory: **580 source identities**. Terms status by source: lookup_blocked: 22, not_reviewed: 303, partial_review: 94, terms_checked: 161.

## Camera index

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `camera:africa-live` [SkylineWebcams Africa](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:alaska` [Alaska 511](https://511.alaska.gov) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:alberta` [Alberta 511](https://511.alberta.ca/api/v2/get/cameras) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:arizona` [ADOT](https://az511.gov) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:asfinag` [ASFINAG (Austria)](https://odo.asfinag.at/odo/rest/sec/resource/001/json/webcams) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:asia-live` [SkylineWebcams Asia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:australia` [Transport for NSW](https://www.livetraffic.com/datajson/all-feeds-web.json) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:autostrade` [Autostrade per l'Italia](https://www.autostrade.it/it/viaggia-sicuro/webcam) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:baltic-live` [Baltic public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:bulgaria` [Bulgaria](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:caltrans` [Caltrans](https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHhighway/CCTV/FeatureServer/0/query) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:china-live` [China public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:connecticut` [CTroads](https://ctroads.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:czechia` [Czechia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:derbyshire` [Derbyshire County Council traffic cameras](https://apps.derbyshire.gov.uk/applications/traffic-cameras/camera-locations.asp) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:drivebc` [DriveBC](https://www.drivebc.ca/api/webcams/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:durham` [Durham County Council](https://www.durham.gov.uk/trafficcameras) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:eastasia` [OpenCCTV East Asia](https://opencctv.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:estonia` [Transpordiamet Tark Tee (Estonia)](https://tarktee.mnt.ee/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:europe-live` [SkylineWebcams Europe](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:fintraffic` [Fintraffic](https://www.digitraffic.fi/en/road-traffic/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:florida` [FDOT](https://fl511.com) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:france` [France](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:georgia` [GDOT](https://511ga.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:germany` [Germany](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:greece` [Greece](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:hongkong` [Hong Kong Transport Department](https://data.gov.hk/en-data/dataset/hk-td-tis_1-traffic-snapshot-images) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:hungary` [Magyar Kozut Utinform (Hungary)](https://www.utinform.hu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:iceland` [Vegagerðin (Iceland)](https://gagnaveita.vegagerdin.is/api/vefmyndavelar2014_1) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:idaho` [Idaho 511](https://511.idaho.gov) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:illinois` [Travel Midwest](https://travelmidwest.com/lmiga/cameraReport.json) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:indiana` [INDOT TrafficWise](https://511in.org/api/graphql) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:iowa` [Iowa 511](https://www.511ia.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:iraq-iran-live` [Iraq and Iran public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:ireland` [Transport Infrastructure Ireland](https://www.tiitraffic.ie/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:israel-live` [Israel public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:italy` [Italy](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:japan` [Japan public webcams and MLIT rivers](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:kansas` [KanDrive](https://www.kandrive.gov) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:latam-live` [SkylineWebcams Latin America](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:lithuania` [Lietuvos automobiliu keliu direkcija (eismoinfo.lt)](https://eismoinfo.lt/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:louisiana` [LADOTD](https://511la.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:luxembourg` [CITA (Luxembourg)](https://www.cita.lu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:lyon` [Metropole de Lyon (Criter)](https://data.grandlyon.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:macedonia` [North Macedonia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:madrid` [Ayuntamiento de Madrid (Informo)](https://informo.madrid.es/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:manitoba` [Manitoba 511](https://www.manitoba511.ca) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:massachusetts` [Mass511](https://mass511.com) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:michigan` [MDOT MiDrive](https://mdotjboss.state.mi.us/MiDrive/camera/list) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:middle-east` [Middle East public webcam streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:minnesota` [MnDOT 511](https://511mn.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:montreal` [Ville de Montreal](https://ville.montreal.qc.ca/circulation/sites/ville.montreal.qc.ca.circulation/files/cameras.json) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:netherlands` [Rijkswaterstaat](https://api.rwsverkeersinfo.nl/api/cameras/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:nevada` [NDOT](https://www.nvroads.com) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newbrunswick` [New Brunswick 511](https://511.gnb.ca) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newengland` [New England 511](https://newengland511.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newfoundland` [511 Newfoundland and Labrador](https://511nl.ca) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newyork` [511NY](https://511ny.org) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:newzealand` [NZTA Waka Kotahi](https://trafficnz.info/service/traffic/rest/4/cameras/all) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:northcarolina` [NCDOT](https://www.drivenc.gov) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:northeast` [North East Traffic Cameras (Tyne and Wear UTMC)](https://netrafficcams.co.uk/all-cameras) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:northyorkshire` [North Yorkshire Council weather cameras](https://www.northyorks.gov.uk/nycc_weather_cameras/markers) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:norway` [Statens vegvesen (Norway)](https://www.vegvesen.no/trafikk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:novascotia` [Nova Scotia 511](https://511.novascotia.ca) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:ontario` [Ontario 511](https://511on.ca/api/v2/get/cameras) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:oregon` [ODOT TripCheck](https://www.tripcheck.com/Scripts/map/data/cctvinventory.js) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:ottawa` [City of Ottawa](https://traffic.ottawa.ca/beta/camera_list) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:pennsylvania` [511PA](https://www.511pa.com) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:poland` [Poland](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:puertorico` [ACT Puerto Rico ITS](https://its.act.pr.gov/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:quebec` [Quebec 511](https://ws.mapserver.transports.gouv.qc.ca/swtq) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:queensland` [QLDTraffic (Queensland)](https://qldtraffic.qld.gov.au/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:romania` [Romania](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:russia-live` [Russia public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:saskatchewan` [Saskatchewan Highway Hotline](https://hotline.gov.sk.ca) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:seasia` [OpenCCTV Southeast Asia](https://opencctv.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:serbia` [Serbia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:singapore` [Singapore LTA](https://api.data.gov.sg/v1/transport/traffic-images) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:slovakia` [Slovakia](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:spain` [Spain](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:spain-dgt` [DGT (Spain)](https://www.dgt.es/.content/.assets/json/camaras.json) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:switzerland` [Switzerland](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:taiwan` [Taiwan Highway Bureau](https://thbapp.thb.gov.tw/services/cctv/thb) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:taiwan-live` [Taiwan public webcam streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:tallinn` [Tallinn junction cameras](https://ristmikud.tallinn.ee/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:tfl` [Transport for London](https://tfl.gov.uk/info-for/open-data-users/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:thailand` [Thailand public webcam streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:toronto` [City of Toronto](https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/a3309088-5fd4-4d34-8297-77c8301840ac/resource/4a568300-c7f8-496d-b150-dff6f5dc6d4f/download/traffic-camera-list-4326.geojson) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:traffic-scotland` [Traffic Scotland](https://www.traffic.gov.scot/traffic-cameras) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:turkey` [Turkey](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:uk-live` [UK public streams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:uk-local` [UK council, island and crossing cameras](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:us-published` [US published webcams](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv) (catalogue provenance only) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Locate each actual camera owner and terms. Catalogue provenance is not a primary media-licence link. |
| `camera:utah` [UDOT Traffic](https://prod-ut.ibi511.com) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:westasia` [OpenCCTV West and Central Asia](https://opencctv.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:westmorland` [Westmorland and Furness Council weather cameras](https://www.westmorlandandfurness.gov.uk/parking-streets-and-transport/streets-roads-and-pavements/weather-cameras) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:wsdot` [WSDOT](https://www.wsdot.wa.gov/traffic/api/) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | off_until_configured; ASE_WSDOT_ACCESS_CODE | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `camera:yukon` [511 Yukon](https://511yukon.ca) | terms unverified; not_reviewed; not checked | unknown / unknown | [camera-owner-rights](#policy-camera-owner-rights) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Feed

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `acled_events` [ACLED political violence and protest events](https://acleddata.com) | [terms](https://acleddata.com/eula); terms_checked; 2026-10-09 | permission_required / permission_required | [acled](#policy-acled) | off_until_configured; ASE_ACLED_REFRESH_TOKEN or ASE_ACLED_ACCESS_TOKEN | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_areas` [Traffic over watched areas (adsb.lol ADS-B)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_emergency` [Emergency squawks (adsb.lol ADS-B)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_global` [Worldwide sampled sweep (adsb.lol)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_ladd` [LADD aircraft (owners limiting display)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_mil` [Military aircraft (adsb.lol ADS-B)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_pia` [PIA aircraft (privacy ICAO addresses)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `adsb_viewport` [Aircraft in requested map areas (adsb.lol)](https://adsb.lol/) | [terms](https://www.adsb.lol/docs/open-data/api/); terms_checked; 2026-10-09 | conditional / conditional | [adsb-lol](#policy-adsb-lol) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `aisstream` [AISStream: global ship positions](https://aisstream.io/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_AISSTREAM_API_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `barentswatch_ais` [BarentsWatch AIS: Norwegian maritime zones](https://www.barentswatch.no/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_BARENTSWATCH_CLIENT_ID and ASE_BARENTSWATCH_CLIENT_SECRET | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bluesky_curated` [Bluesky curated accounts](https://bsky.app/) | [terms](https://bsky.social/about/support/tos); partial_review; 2026-10-09 | unknown / unknown | [bluesky](#policy-bluesky) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_active` [Active satellites (CelesTrak)](https://celestrak.org/) | [terms](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_military` [Public military satellite catalogue (CelesTrak)](https://celestrak.org/) | [terms](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_skynet` [Skynet public orbital elements (CelesTrak)](https://celestrak.org/) | [terms](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `celestrak_stations` [Space stations and crewed vehicles (CelesTrak)](https://celestrak.org/) | [terms](https://celestrak.org/usage-policy.php); partial_review; 2026-10-09 | unknown / unknown | [celestrak](#policy-celestrak) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cisa_kev` [CISA Known Exploited Vulnerabilities](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cloudflare_radar_outages` [Internet outages (Cloudflare Radar)](https://radar.cloudflare.com/outage-center) | [terms](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN | high; request_permission, legal_review; Token-only path: research non-commercial acknowledgement does not cover this path. Review permission before hosted/commercial use. |
| `digitraffic_ais` [Fintraffic AIS: Finnish waterways](https://www.digitraffic.fi/en/marine-traffic/) | [terms](https://www.digitraffic.fi/en/terms-of-service/); terms_checked; 2026-10-09 | conditional / conditional | [digitraffic](#policy-digitraffic) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `emsc_earthquakes` [EMSC earthquakes (M4+)](https://www.seismicportal.eu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_public_noaa20` [NASA FIRMS: public NOAA-20 24-hour detections](https://firms.modaps.eosdis.nasa.gov/) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_public_noaa21` [NASA FIRMS: public NOAA-21 24-hour detections](https://firms.modaps.eosdis.nasa.gov/) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_viirs_noaa20` [NASA FIRMS: NOAA-20 thermal detections](https://firms.modaps.eosdis.nasa.gov/) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | off_until_configured; ASE_FIRMS_MAP_KEY or Admin FIRMS key | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `firms_viirs_noaa21` [NASA FIRMS: NOAA-21 thermal detections](https://firms.modaps.eosdis.nasa.gov/) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | off_until_configured; ASE_FIRMS_MAP_KEY or Admin FIRMS key | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gdacs` [GDACS disaster alerts](https://www.gdacs.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gdelt_events` [GDELT 2.0 media signals (unreviewed)](https://www.gdeltproject.org/) | [terms](https://www.gdeltproject.org/about.html#termsofuse); terms_checked; 2026-10-09 | conditional / conditional | [gdelt](#policy-gdelt) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gdelt_news` [GDELT geolocated news signals (unreviewed)](https://www.gdeltproject.org/) | [terms](https://www.gdeltproject.org/about.html#termsofuse); terms_checked; 2026-10-09 | conditional / conditional | [gdelt](#policy-gdelt) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `google_news_watchlists` [Google News watchlists](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gvp_weekly` [Smithsonian weekly volcanic activity report](https://volcano.si.edu/reports_weekly.cfm) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ifrc_go` [IFRC GO emergencies](https://go.ifrc.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ioda_outage_events` [Internet outage event windows (IODA)](https://ioda.inetintel.cc.gatech.edu/) | [terms](https://ioda.inetintel.cc.gatech.edu/resources); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ioda](#policy-ioda) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Live path has no IODA acknowledgement gate; complete rights review separately from the research path. |
| `ioda_outages` [Internet outage alerts (IODA)](https://ioda.inetintel.cc.gatech.edu/) | [terms](https://ioda.inetintel.cc.gatech.edu/resources); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ioda](#policy-ioda) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Live path has no IODA acknowledgement gate; complete rights review separately from the research path. |
| `isw_assessments` [ISW Russian Offensive Campaign Assessments](https://www.understandingwar.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `jtwc` [JTWC tropical cyclone warnings](https://www.metoc.navy.mil/jtwc/jtwc.html) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `launch_library` [Upcoming launches (Launch Library 2)](https://thespacedevs.com/llapi) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nasa_eonet` [NASA EONET natural events](https://eonet.gsfc.nasa.gov/docs/v3) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nga_navarea` [NAVAREA broadcast warnings (NGA MSI)](https://msi.nga.mil/NavWarnings) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nhc_atlantic` [NHC Atlantic advisories](https://www.nhc.noaa.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nhc_east_pacific` [NHC Eastern Pacific advisories](https://www.nhc.noaa.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `noaa_swpc_alerts` [NOAA SWPC space weather alerts](https://www.swpc.noaa.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `noaa_swpc_scales` [NOAA SWPC current space weather scales](https://www.swpc.noaa.gov/noaa-scales-explanation) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ntwc_tsunami` [National Tsunami Warning Center bulletins](https://www.tsunami.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nws_alerts` [NWS severe weather alerts](https://www.weather.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ptwc_tsunami` [Pacific Tsunami Warning Center bulletins](https://www.tsunami.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ransomware_live` [Ransomware victim claims (ransomware.live)](https://www.ransomware.live/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reliefweb_reports` [ReliefWeb humanitarian reports (API)](https://reliefweb.int/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_RELIEFWEB_APPNAME | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `swpc_kp` [Planetary K index (NOAA SWPC)](https://www.swpc.noaa.gov/) | [terms](https://www.weather.gov/disclaimer); terms_checked; 2026-10-09 | conditional / conditional | [nws](#policy-nws) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ucdp_candidate` [UCDP monthly candidate violence events](https://ucdp.uu.se/downloads/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls; ASE_UCDP_ACCESS_TOKEN | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine_general_staff` [General Staff of Ukraine daily loss claims](https://russianwarship.rip/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `usgs_earthquakes` [USGS earthquakes (past day)](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) | [terms](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits); partial_review; 2026-10-09 | conditional / conditional | [usgs](#policy-usgs) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `who_don` [WHO Disease Outbreak News](https://www.who.int/emergencies/disease-outbreak-news) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Map layer

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `map:data_centres` [Data centres](https://www.openstreetmap.org/) | [terms](https://www.openstreetmap.org/copyright); terms_checked; 2026-10-09 | conditional / conditional | [osm](#policy-osm) | available_asset; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:energy_sites` [Energy sites](https://www.openstreetmap.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Review the combined OSM, Wikidata and curated-record provenance; retain each applicable notice. |
| `map:eox_s2cloudless` [Sentinel-2 cloudless imagery](https://s2maps.eu/) | [terms](https://cloudless.eox.at/license-non-commercial); terms_checked; 2026-10-09 | permission_required / permission_required | [eox-2024](#policy-eox-2024) | initial_hybrid_basemap; No display licence gate; image export requires suitable-use declaration | high; request_permission, legal_review; Prioritise commercial licence or replacement: 2024 imagery is selected by the initial hybrid basemap; export declarations do not grant display rights. |
| `map:ground_stations` [Satellite ground stations](https://www.wikidata.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:military_source_index` Military infrastructure source register (per-item) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:nasa_gibs_daily` [NASA GIBS daily imagery](https://www.earthdata.nasa.gov/gibs) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | off_until_selected; Map imagery overlay choice (off by default); no licence acknowledgement | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:natural_earth_countries` [Country outlines](https://www.naturalearthdata.com/) | [terms](https://www.naturalearthdata.com/about/terms-of-use/); terms_checked; 2026-10-09 | conditional / conditional | [natural-earth](#policy-natural-earth) | available_asset; No source-specific prerequisite recorded | low; keep; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:nuclear_facilities` [Nuclear facilities](https://raw.githubusercontent.com/wri/global-power-plant-database/7a91cfbb2a4e272597acbc00506d61fc1ec73b3d/output_database/global_power_plant_database.csv) | [terms](https://github.com/wri/global-power-plant-database); terms_checked; 2026-10-09 | conditional / conditional | [wri-power](#policy-wri-power) | available_asset; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:openfreemap` [OpenFreeMap vector base maps](https://openfreemap.org/) | [terms](https://openfreemap.org/); terms_checked; 2026-10-09 | conditional / conditional | [openfreemap](#policy-openfreemap) | initial_hybrid_labels; Basemap choice; no credential required | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:photon_places` [Photon place search](https://photon.komoot.io) | [terms](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [osm-service](#policy-osm-service) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:semiconductor_sites` [Semiconductor sites](https://www.openstreetmap.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Review the combined OSM, Wikidata and curated-record provenance; retain each applicable notice. |
| `map:submarine_cables` [Submarine cables](https://www.openstreetmap.org/) | [terms](https://www.openstreetmap.org/copyright); terms_checked; 2026-10-09 | conditional / conditional | [osm](#policy-osm) | available_asset; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:terrain_elevation` [Terrain elevation tiles](https://github.com/tilezen/joerd/blob/master/docs/attribution.md) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `map:valhalla_routing` [Valhalla routing](https://valhalla1.openstreetmap.de) | [terms](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [osm-service](#policy-osm-service) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Mastodon

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `mastodon_defcon_social` [Mastodon hashtags (defcon.social)](https://defcon.social/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mastodon_eupolicy_social` [Mastodon hashtags (eupolicy.social)](https://eupolicy.social/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mastodon_journa_host` [Mastodon hashtags (journa.host)](https://journa.host/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mastodon_mastodon_social` [Mastodon hashtags (mastodon.social)](https://mastodon.social/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## On demand or reference

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `cloudflare_radar_attack_trends` [Cloudflare Radar attack distributions](https://radar.cloudflare.com/security/application-layer) | [terms](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN | high; request_permission, legal_review; Token-only path: research non-commercial acknowledgement does not cover this path. Review permission before hosted/commercial use. |
| `economic-ecb` [ECB currency reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html) | [terms](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mitre_attack` [MITRE ATT&CK actor reference](https://attack.mitre.org/groups/) | [terms](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/); terms_checked; 2026-10-09 | conditional / conditional | [mitre](#policy-mitre) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-aiddata-projects` [AidData Chinese development projects](https://www.aiddata.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_AIDDATA_CATALOGUE_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-asset-register` Packaged infrastructure registers (per-item) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-certificate-transparency` [SSLMate certificate-transparency records](https://sslmate.com/ct_search_api/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_CERTIFICATE_TRANSPARENCY_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-cloudflare-radar-layer3` [Cloudflare Radar layer3 target distribution](https://radar.cloudflare.com/) | [terms](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN and ASE_CLOUDFLARE_RADAR_NONCOMMERCIAL_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-cloudflare-radar-layer7` [Cloudflare Radar layer7 target distribution](https://radar.cloudflare.com/) | [terms](https://radar.cloudflare.com/about); terms_checked; 2026-10-09 | permission_required / permission_required | [cloudflare-radar](#policy-cloudflare-radar) | off_until_configured; ASE_CLOUDFLARE_RADAR_TOKEN and ASE_CLOUDFLARE_RADAR_NONCOMMERCIAL_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-companies-house` [Companies House](https://developer.company-information.service.gov.uk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_COMPANIES_HOUSE_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-companies-house-officers` [Companies House officers](https://developer.company-information.service.gov.uk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_COMPANIES_HOUSE_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-companies-house-psc` [Companies House persons with significant control](https://developer.company-information.service.gov.uk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_COMPANIES_HOUSE_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-contracts-finder` [Contracts Finder publication notices](https://www.contractsfinder.service.gov.uk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-copernicus-footprints` [Copernicus satellite footprints](https://dataspace.copernicus.eu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-crossref` [Crossref scholarly metadata](https://www.crossref.org/) | [terms](https://www.crossref.org/services/metadata-retrieval/); terms_checked; 2026-10-09 | conditional / conditional | [crossref](#policy-crossref) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-eu_fsf` [EU financial sanctions imported snapshot](https://data.europa.eu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_EU_FSF_SNAPSHOT_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-ofac_sdn` [OFAC SDN imported snapshot](https://ofac.treasury.gov/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_OFAC_SDN_SNAPSHOT_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-uksl` [UK Sanctions List imported snapshot](https://www.gov.uk/government/publications/the-uk-sanctions-list) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | off_until_configured; ASE_UKSL_SNAPSHOT_PATH | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-designations-un_sc` [UN Security Council imported snapshot](https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_UN_SC_SNAPSHOT_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-a` [Google Public DNS A records](https://developers.google.com/speed/public-dns/docs/doh) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-aaaa` [Google Public DNS AAAA records](https://developers.google.com/speed/public-dns/docs/doh) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-mx` [Google Public DNS MX records](https://developers.google.com/speed/public-dns/docs/doh) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-dns-ns` [Google Public DNS NS records](https://developers.google.com/speed/public-dns/docs/doh) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ecb-gbp-reference-rate` [ECB GBP per EUR daily reference rates](https://www.ecb.europa.eu/) | [terms](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-eonet-area` [NASA EONET area hazard search](https://eonet.gsfc.nasa.gov/) | [terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy); partial_review; 2026-10-09 | unknown / unknown | [nasa-data](#policy-nasa-data) | on_demand; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-gleif-direct-parent` [GLEIF direct parent](https://www.gleif.org/) | [terms](https://www.gleif.org/en/meta/lei-data-terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [gleif](#policy-gleif) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-gleif-profile` [GLEIF legal entity profile](https://www.gleif.org/) | [terms](https://www.gleif.org/en/meta/lei-data-terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [gleif](#policy-gleif) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-gleif-ultimate-parent` [GLEIF ultimate parent](https://www.gleif.org/) | [terms](https://www.gleif.org/en/meta/lei-data-terms-of-use); terms_checked; 2026-10-09 | conditional / conditional | [gleif](#policy-gleif) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-hapi-food-security` [HDX HAPI food-security](https://hapi.humdata.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_HAPI_APP_IDENTIFIER | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-hapi-idps` [HDX HAPI idps](https://hapi.humdata.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_HAPI_APP_IDENTIFIER | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-hapi-operational-presence` [HDX HAPI operational-presence](https://hapi.humdata.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_HAPI_APP_IDENTIFIER | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ioda-outage-events` [IODA country outage event windows](https://ioda.inetintel.cc.gatech.edu/) | [terms](https://ioda.inetintel.cc.gatech.edu/resources); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [ioda](#policy-ioda) | off_until_configured; ASE_IODA_PUBLIC_DATA_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ons-cpih` [ONS UK CPIH monthly observations](https://www.ons.gov.uk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-ooni-aggregate` [OONI country connectivity aggregates](https://ooni.org/) | [terms](https://github.com/ooni/license/blob/master/data/LICENSE.md); terms_checked; 2026-10-09 | permission_required / permission_required | [ooni](#policy-ooni) | off_until_configured; ASE_OONI_NONCOMMERCIAL_USE_ACKNOWLEDGED | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-openalex` [OpenAlex scholarly metadata](https://openalex.org/) | [terms](https://help.openalex.org/access/overview/); terms_checked; 2026-10-09 | conditional / conditional | [openalex](#policy-openalex) | on_demand; ASE_OPENALEX_API_KEY | medium; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-openaq-area` [OpenAQ area air-quality observations](https://openaq.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_OPENAQ_API_KEY | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-osm-features` [OpenStreetMap feature search](https://www.openstreetmap.org/) | [terms](https://www.openstreetmap.org/copyright); partial_review; 2026-10-09 | unknown / unknown | [osm-service](#policy-osm-service) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-rdap` [Verisign domain registry RDAP](https://www.iana.org/rdap) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-retained-area-feeds` Retained public feeds (per-item) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-sec-company-directory` [SEC company identity candidates](https://www.sec.gov/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-sec-submissions` [SEC EDGAR submissions](https://www.sec.gov/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-uk-parliament` [UK Parliament written questions](https://www.parliament.uk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-usgs-area` [USGS area earthquake search](https://earthquake.usgs.gov/) | [terms](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits); partial_review; 2026-10-09 | conditional / conditional | [usgs](#policy-usgs) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-web-search` [Fresh web search](https://platform.openai.com/docs/guides/tools-web-search) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; model | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-world-bank` [World Bank annual indicators](https://data.worldbank.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research-youtube` [YouTube video search](https://www.youtube.com/) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ar` [Google News research (ar)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_de` [Google News research (de)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_en` [Google News research (en)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_es` [Google News research (es)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_fr` [Google News research (fr)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_hi` [Google News research (hi)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ja` [Google News research (ja)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ko` [Google News research (ko)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_pt` [Google News research (pt)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_ru` [Google News research (ru)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_uk` [Google News research (uk)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_zh-cn` [Google News research (zh-cn)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_google_news_zh-tw` [Google News research (zh-tw)](https://news.google.com/) | [terms](https://policies.google.com/terms); partial_review; 2026-10-09 | unknown / unknown | [google-news](#policy-google-news) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_import` Private document import (per-item) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_media` Private image and video import (per-item) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | on_demand; ASE_RESEARCH_TESSERACT_PATH, ASE_RESEARCH_FFMPEG_PATH and ASE_RESEARCH_FFPROBE_PATH | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_aljazeera_en` [Al Jazeera English](https://www.aljazeera.com/) | [terms](https://www.aljazeera.com/terms-and-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [aljazeera](#policy-aljazeera) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_anadolu_en` [Anadolu Agency English](https://www.aa.com.tr/en) | [terms](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_bbc_world` [BBC News World](https://www.bbc.co.uk/news/world) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_bellingcat` [Bellingcat](https://www.bellingcat.com/) | [terms](https://www.bellingcat.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [bellingcat](#policy-bellingcat) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cgtn_china` [CGTN China](https://www.cgtn.com/china) | [terms](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_crisis_group` [International Crisis Group](https://www.crisisgroup.org/) | [terms](https://www.crisisgroup.org/legal); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [crisisgroup](#policy-crisisgroup) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_acsc_advisories` [Australia ACSC advisories](https://www.cyber.gov.au/about-us/view-all-content/advisories) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_bleeping_computer` [BleepingComputer security news](https://www.bleepingcomputer.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cccs_alerts` [Canadian Centre for Cyber Security alerts and advisories](https://www.cyber.gc.ca/en/alerts-advisories) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cert_eu` [CERT-EU threat intelligence](https://cert.europa.eu/publications/threat-intelligence) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cert_fr` [CERT-FR alerts and advisories](https://www.cert.ssi.gouv.fr/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cert_ua` [CERT-UA incident and threat reports](https://cert.gov.ua/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cisa_advisories` [US CISA cybersecurity and ICS advisories](https://www.cisa.gov/news-events/cybersecurity-advisories) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_cisco_talos` [Cisco Talos threat intelligence](https://blog.talosintelligence.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_google_threat_intelligence` [Google Threat Intelligence and Mandiant](https://cloud.google.com/blog/topics/threat-intelligence) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_ic3_psa` [FBI IC3 public service announcements](https://www.ic3.gov/PSA) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_microsoft_threat_intelligence` [Microsoft Threat Intelligence](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_ncsc_news` [UK NCSC news and threat statements](https://www.ncsc.gov.uk/section/keep-up-to-date/news) | [terms](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_ncsc_reports` [UK NCSC threat reports](https://www.ncsc.gov.uk/section/keep-up-to-date/threat-reports) | [terms](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_sans_isc` [SANS Internet Storm Center diaries](https://isc.sans.edu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_the_record` [The Record from Recorded Future News](https://therecord.media/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_cyber_unit42` [Palo Alto Networks Unit 42 research](https://unit42.paloaltonetworks.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_dawn` [Dawn](https://www.dawn.com/) | [terms](https://www.dawn.com/terms/); terms_checked; 2026-10-09 | permission_required / permission_required | [dawn](#policy-dawn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_dw_world` [DW World](https://www.dw.com/en/) | [terms](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_canada` [Bank of Canada press releases](https://www.bankofcanada.ca/press/press-releases/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_england` [Bank of England news](https://www.bankofengland.co.uk/news) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_japan` [Bank of Japan releases](https://www.boj.or.jp/en/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bank_russia` [Bank of Russia press releases](https://www.cbr.ru/eng/press/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bbc_business` [BBC Business](https://www.bbc.com/business) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bis_speeches` [BIS central bankers' speeches](https://www.bis.org/cbspeeches/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bls_consumer_prices` [BLS consumer price index](https://www.bls.gov/cpi/) | [terms](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bls_employment` [BLS employment situation](https://www.bls.gov/ces/) | [terms](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_bls_producer_prices` [BLS producer price index](https://www.bls.gov/ppi/) | [terms](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | on_demand; No source-specific prerequisite recorded | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_census_indicators` [US Census economic indicators](https://www.census.gov/economic-indicators/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_cgtn_business` [CGTN Business](https://www.cgtn.com/business) | [terms](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_dw_business` [DW Business](https://www.dw.com/en/business/s-1431) | [terms](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_ecb_press` [European Central Bank press releases](https://www.ecb.europa.eu/press/html/index.en.html) | [terms](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_economist_finance` [The Economist finance and economics](https://www.economist.com/finance-and-economics) | [terms](https://www.economist.com/syndication/permissions); partial_review; 2026-10-09 | permission_required / permission_required | [economist](#policy-economist) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_eia_energy` [EIA Today in Energy](https://www.eia.gov/todayinenergy/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_federal_reserve` [Federal Reserve press releases](https://www.federalreserve.gov/newsevents/pressreleases.htm) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_france24_business` [France 24 Business](https://www.france24.com/en/business/) | [terms](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_guardian_business` [The Guardian business](https://www.theguardian.com/business) | [terms](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_hm_treasury` [HM Treasury announcements](https://www.gov.uk/government/organisations/hm-treasury) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_intellinews` [bne IntelliNews](https://www.intellinews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_ons_releases` [ONS statistical releases](https://www.ons.gov.uk/releasecalendar) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_reserve_bank_india` [Reserve Bank of India press releases](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_scmp_china` [SCMP China economy](https://www.scmp.com/economy/china-economy) | [terms](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_tehran_times` [Tehran Times economy](https://www.tehrantimes.com/service/economy) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_the_bell` [The Bell](https://en.thebell.io/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_economic_wto_news` [WTO latest news](https://www.wto.org/english/news_e/news_e.htm) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_france24_en` [France 24 English](https://www.france24.com/en/) | [terms](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_fcdo_news` [GOV.UK FCDO news](https://www.gov.uk/government/organisations/foreign-commonwealth-development-office) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_home_office` [GOV.UK Home Office news](https://www.gov.uk/government/organisations/home-office) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_mod_news` [GOV.UK Ministry of Defence news](https://www.gov.uk/government/organisations/ministry-of-defence) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_number_10` [GOV.UK Prime Minister's Office news](https://www.gov.uk/government/organisations/prime-ministers-office-10-downing-street) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_gov_uk_travel_advice` [GOV.UK foreign travel advice](https://www.gov.uk/foreign-travel-advice) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | on_demand; No source-specific prerequisite recorded | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_guardian_world` [The Guardian World](https://www.theguardian.com/world) | [terms](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_kyiv_independent` [The Kyiv Independent](https://kyivindependent.com/) | [terms](https://kyivindependent.com/terms-of-use/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [kyiv-independent](#policy-kyiv-independent) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_lemonde_en` [Le Monde in English](https://www.lemonde.fr/en/) | [terms](https://www.lemonde.fr/le-monde-et-vous/article/2025/07/14/les-flux-rss-du-monde_fr_5498778_3237.html); terms_checked; 2026-10-09 | permission_required / permission_required | [lemonde](#policy-lemonde) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_meduza_en` [Meduza in English](https://meduza.io/en) | [terms](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_nikkei_asia` [Nikkei Asia](https://asia.nikkei.com/) | [terms](https://info.asia.nikkei.com/rss); terms_checked; 2026-10-09 | permission_required / permission_required | [nikkei](#policy-nikkei) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_pravda_ua_en` [Ukrainska Pravda in English](https://www.pravda.com.ua/eng/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_reliefweb_updates` [ReliefWeb updates](https://reliefweb.int/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_russia_mfa_ru` [Russian MFA news (Russian)](https://mid.ru/ru/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_scmp_news` [South China Morning Post](https://www.scmp.com/) | [terms](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_tass_en` [TASS English](https://tass.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_times_of_israel` [The Times of Israel](https://www.timesofisrael.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_un_news` [UN News](https://news.un.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_un_press` [UN press releases and meetings coverage](https://press.un.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_us_dod_news` [US Department of Defense news](https://www.defense.gov/News/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_us_state_travel_advisories` [US State Department travel advisories](https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_publisher_whitehouse_news` [White House news](https://www.whitehouse.gov/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_anadolu_ar` [Anadolu Agency Arabic](https://www.aa.com.tr/ar) | [terms](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_afrique` [BBC News Afrique](https://www.bbc.com/afrique) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_arabic` [BBC News Arabic](https://www.bbc.com/arabic) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_hausa` [BBC News Hausa](https://www.bbc.com/hausa) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_hindi` [BBC News Hindi](https://www.bbc.com/hindi) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_japanese` [BBC News Japanese](https://www.bbc.com/japanese) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_korean` [BBC News Korean](https://www.bbc.com/korean) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_swahili` [BBC News Swahili](https://www.bbc.com/swahili) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_bbc_urdu` [BBC News Urdu](https://www.bbc.com/urdu) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_belta_ru` [BelTA in Russian](https://belta.by/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_cdt_zh` [China Digital Times in Chinese](https://chinadigitaltimes.net/chinese/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_deutschlandfunk_de` [Deutschlandfunk Nachrichten](https://www.deutschlandfunk.de/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_express_urdu` [Express News Urdu](https://www.express.pk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_hrana_en` [HRANA in English](https://www.en-hrana.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_hrana_fa` [HRANA in Persian](https://www.hra-news.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_insider_ru` [The Insider in Russian](https://theins.ru/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_interfax_ru` [Interfax in Russian](https://www.interfax.ru/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_iranwire_en` [IranWire in English](https://iranwire.com/en/) | [terms](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_iranwire_fa` [IranWire in Persian](https://iranwire.com/fa/) | [terms](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_maariv_he` [Maariv Hebrew](https://www.maariv.co.il/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_mediazona_ru` [Mediazona in Russian](https://zona.media/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_meduza_ru` [Meduza in Russian](https://meduza.io/) | [terms](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_ndtv_hindi` [NDTV India Hindi](https://ndtv.in/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_radio_okapi_fr` [Radio Okapi French](https://www.radiookapi.net/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_trt_haber_tr` [TRT Haber Turkish](https://www.trthaber.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_regional_ukrinform_en` [Ukrinform in English](https://www.ukrinform.net/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_social_bluesky` [Bluesky curated accounts research](https://bsky.social/) | [terms](https://bsky.social/about/support/tos); partial_review; 2026-10-09 | unknown / unknown | [bluesky](#policy-bluesky) | on_demand; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `research_social_telegram` [Curated Telegram channels](https://telegram.org/) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | on_demand; No source-specific prerequisite recorded | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Reference dataset

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `reference:conflicts` Conflict and tension areas (per-item) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reference:entities` [Ship and aircraft reference](https://www.wikidata.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [mixed-evidence](#policy-mixed-evidence) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reference:public_figures` [Public figures](https://www.wikidata.org/) | [terms](https://www.wikidata.org/wiki/Wikidata:Licensing); partial_review; 2026-10-09 | unknown / unknown | [wikidata-mixed](#policy-wikidata-mixed) | available_asset; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Rss

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `aljazeera_en` [Al Jazeera English](https://www.aljazeera.com/) | [terms](https://www.aljazeera.com/terms-and-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [aljazeera](#policy-aljazeera) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `anadolu_ar` [Anadolu Agency Arabic](https://www.aa.com.tr/ar) | [terms](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `anadolu_en` [Anadolu Agency English](https://www.aa.com.tr/en) | [terms](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari); terms_checked; 2026-10-09 | permission_required / permission_required | [anadolu](#policy-anadolu) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_afrique` [BBC News Afrique](https://www.bbc.com/afrique) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_arabic` [BBC News Arabic](https://www.bbc.com/arabic) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_hausa` [BBC News Hausa](https://www.bbc.com/hausa) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_hindi` [BBC News Hindi](https://www.bbc.com/hindi) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_japanese` [BBC News Japanese](https://www.bbc.com/japanese) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_korean` [BBC News Korean](https://www.bbc.com/korean) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_swahili` [BBC News Swahili](https://www.bbc.com/swahili) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_urdu` [BBC News Urdu](https://www.bbc.com/urdu) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bbc_world` [BBC News World](https://www.bbc.co.uk/news/world) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `bellingcat` [Bellingcat](https://www.bellingcat.com/) | [terms](https://www.bellingcat.com/terms-and-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [bellingcat](#policy-bellingcat) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `belta_ru` [BelTA in Russian](https://belta.by/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cdt_zh` [China Digital Times in Chinese](https://chinadigitaltimes.net/chinese/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cgtn_china` [CGTN China](https://www.cgtn.com/china) | [terms](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `crisis_group` [International Crisis Group](https://www.crisisgroup.org/) | [terms](https://www.crisisgroup.org/legal); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [crisisgroup](#policy-crisisgroup) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_acsc_advisories` [Australia ACSC advisories](https://www.cyber.gov.au/about-us/view-all-content/advisories) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_bleeping_computer` [BleepingComputer security news](https://www.bleepingcomputer.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cccs_alerts` [Canadian Centre for Cyber Security alerts and advisories](https://www.cyber.gc.ca/en/alerts-advisories) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cert_eu` [CERT-EU threat intelligence](https://cert.europa.eu/publications/threat-intelligence) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cert_fr` [CERT-FR alerts and advisories](https://www.cert.ssi.gouv.fr/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cert_ua` [CERT-UA incident and threat reports](https://cert.gov.ua/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cisa_advisories` [US CISA cybersecurity and ICS advisories](https://www.cisa.gov/news-events/cybersecurity-advisories) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_cisco_talos` [Cisco Talos threat intelligence](https://blog.talosintelligence.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_google_threat_intelligence` [Google Threat Intelligence and Mandiant](https://cloud.google.com/blog/topics/threat-intelligence) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_ic3_psa` [FBI IC3 public service announcements](https://www.ic3.gov/PSA) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_microsoft_threat_intelligence` [Microsoft Threat Intelligence](https://www.microsoft.com/en-us/security/blog/topic/threat-intelligence/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_ncsc_news` [UK NCSC news and threat statements](https://www.ncsc.gov.uk/section/keep-up-to-date/news) | [terms](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_ncsc_reports` [UK NCSC threat reports](https://www.ncsc.gov.uk/section/keep-up-to-date/threat-reports) | [terms](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions); terms_checked; 2026-10-09 | conditional / conditional | [ncsc](#policy-ncsc) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_sans_isc` [SANS Internet Storm Center diaries](https://isc.sans.edu/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_the_record` [The Record from Recorded Future News](https://therecord.media/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `cyber_unit42` [Palo Alto Networks Unit 42 research](https://unit42.paloaltonetworks.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `dawn` [Dawn](https://www.dawn.com/) | [terms](https://www.dawn.com/terms/); terms_checked; 2026-10-09 | permission_required / permission_required | [dawn](#policy-dawn) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `deutschlandfunk_de` [Deutschlandfunk Nachrichten](https://www.deutschlandfunk.de/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `dw_world` [DW World](https://www.dw.com/en/) | [terms](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_canada` [Bank of Canada press releases](https://www.bankofcanada.ca/press/press-releases/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_england` [Bank of England news](https://www.bankofengland.co.uk/news) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_japan` [Bank of Japan releases](https://www.boj.or.jp/en/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bank_russia` [Bank of Russia press releases](https://www.cbr.ru/eng/press/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bbc_business` [BBC Business](https://www.bbc.com/business) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bis_speeches` [BIS central bankers' speeches](https://www.bis.org/cbspeeches/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bls_consumer_prices` [BLS consumer price index](https://www.bls.gov/cpi/) | [terms](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bls_employment` [BLS employment situation](https://www.bls.gov/ces/) | [terms](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_bls_producer_prices` [BLS producer price index](https://www.bls.gov/ppi/) | [terms](https://www.bls.gov/bls/linksite.htm); terms_checked; 2026-10-09 | conditional / conditional | [bls](#policy-bls) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | low; keep, attribute; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_census_indicators` [US Census economic indicators](https://www.census.gov/economic-indicators/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_cgtn_business` [CGTN Business](https://www.cgtn.com/business) | [terms](https://www.cgtn.com/terms-of-use); terms_checked; 2026-10-09 | permission_required / permission_required | [cgtn](#policy-cgtn) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_dw_business` [DW Business](https://www.dw.com/en/business/s-1431) | [terms](https://b2b.dw.com/page/dw-terms-conditions); partial_review; 2026-10-09 | unknown / unknown | [dw-rss](#policy-dw-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_ecb_press` [European Central Bank press releases](https://www.ecb.europa.eu/press/html/index.en.html) | [terms](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html); terms_checked; 2026-10-09 | conditional / conditional | [ecb](#policy-ecb) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_economist_finance` [The Economist finance and economics](https://www.economist.com/finance-and-economics) | [terms](https://www.economist.com/syndication/permissions); partial_review; 2026-10-09 | permission_required / permission_required | [economist](#policy-economist) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_eia_energy` [EIA Today in Energy](https://www.eia.gov/todayinenergy/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_federal_reserve` [Federal Reserve press releases](https://www.federalreserve.gov/newsevents/pressreleases.htm) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_france24_business` [France 24 Business](https://www.france24.com/en/business/) | [terms](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_guardian_business` [The Guardian business](https://www.theguardian.com/business) | [terms](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_hm_treasury` [HM Treasury announcements](https://www.gov.uk/government/organisations/hm-treasury) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_intellinews` [bne IntelliNews](https://www.intellinews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_ons_releases` [ONS statistical releases](https://www.ons.gov.uk/releasecalendar) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_reserve_bank_india` [Reserve Bank of India press releases](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_scmp_china` [SCMP China economy](https://www.scmp.com/economy/china-economy) | [terms](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_tehran_times` [Tehran Times economy](https://www.tehrantimes.com/service/economy) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_the_bell` [The Bell](https://en.thebell.io/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `economic_wto_news` [WTO latest news](https://www.wto.org/english/news_e/news_e.htm) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `express_urdu` [Express News Urdu](https://www.express.pk/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `france24_en` [France 24 English](https://www.france24.com/en/) | [terms](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_fcdo_news` [GOV.UK FCDO news](https://www.gov.uk/government/organisations/foreign-commonwealth-development-office) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_home_office` [GOV.UK Home Office news](https://www.gov.uk/government/organisations/home-office) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_mod_news` [GOV.UK Ministry of Defence news](https://www.gov.uk/government/organisations/ministry-of-defence) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_number_10` [GOV.UK Prime Minister's Office news](https://www.gov.uk/government/organisations/prime-ministers-office-10-downing-street) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `gov_uk_travel_advice` [GOV.UK foreign travel advice](https://www.gov.uk/foreign-travel-advice) | [terms](https://www.gov.uk/help/terms-conditions); terms_checked; 2026-10-09 | conditional / conditional | [govuk](#policy-govuk) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | medium; keep, attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `guardian_world` [The Guardian World](https://www.theguardian.com/world) | [terms](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `hrana_en` [HRANA in English](https://www.en-hrana.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `hrana_fa` [HRANA in Persian](https://www.hra-news.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `insider_ru` [The Insider in Russian](https://theins.ru/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `interfax_ru` [Interfax in Russian](https://www.interfax.ru/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `iranwire_en` [IranWire in English](https://iranwire.com/en/) | [terms](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `iranwire_fa` [IranWire in Persian](https://iranwire.com/fa/) | [terms](https://iranwire.com/en/pages/terms); terms_checked; 2026-10-09 | permission_required / permission_required | [iranwire](#policy-iranwire) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `kyiv_independent` [The Kyiv Independent](https://kyivindependent.com/) | [terms](https://kyivindependent.com/terms-of-use/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [kyiv-independent](#policy-kyiv-independent) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `lemonde_en` [Le Monde in English](https://www.lemonde.fr/en/) | [terms](https://www.lemonde.fr/le-monde-et-vous/article/2025/07/14/les-flux-rss-du-monde_fr_5498778_3237.html); terms_checked; 2026-10-09 | permission_required / permission_required | [lemonde](#policy-lemonde) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `maariv_he` [Maariv Hebrew](https://www.maariv.co.il/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `mediazona_ru` [Mediazona in Russian](https://zona.media/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `meduza_en` [Meduza in English](https://meduza.io/en) | [terms](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `meduza_ru` [Meduza in Russian](https://meduza.io/) | [terms](https://meduza.io/en/pages/terms); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [meduza](#policy-meduza) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ndtv_hindi` [NDTV India Hindi](https://ndtv.in/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_abc_australia` [ABC News Australia](https://www.abc.net.au/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_abc_us_international` [ABC News International](https://abcnews.go.com/International) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_africanews` [Africanews](https://www.africanews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_agencia_brasil_en` [Agência Brasil English](https://agenciabrasil.ebc.com.br/en) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_antara_en` [ANTARA News English](https://en.antaranews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_arab_news` [Arab News](https://www.arabnews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bangkok_post` [Bangkok Post](https://www.bangkokpost.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_batimes` [Buenos Aires Times](https://www.batimes.com.ar/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_northern_ireland` [BBC News Northern Ireland](https://www.bbc.co.uk/news/northern_ireland) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_scotland` [BBC News Scotland](https://www.bbc.co.uk/news/scotland) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_uk` [BBC News UK](https://www.bbc.co.uk/news/uk) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_bbc_wales` [BBC News Wales](https://www.bbc.co.uk/news/wales) | [terms](https://www.bbc.co.uk/usingthebbc/terms/); partial_review; 2026-10-09 | unknown / unknown | [bbc-rss](#policy-bbc-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_belfast_live` [BelfastLive](https://www.belfastlive.co.uk/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_birmingham_live` [BirminghamLive](https://www.birminghammail.co.uk/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_cbc_canada` [CBC News top stories](https://www.cbc.ca/news) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_cbs_world` [CBS News World](https://www.cbsnews.com/world/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_cna_asia` [CNA Asia](https://www.channelnewsasia.com/asia) | [terms](https://www.channelnewsasia.com/rss/rssterms); terms_checked; 2026-10-09 | permission_required / permission_required | [cna-rss](#policy-cna-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_el_pais` [El País Spanish](https://elpais.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_euronews` [Euronews](https://www.euronews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_france24_ar` [France 24 Arabic](https://www.france24.com/ar/) | [terms](https://www.france24.com/en/legal-notice); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [france24](#policy-france24) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_guardian_uk` [The Guardian UK news](https://www.theguardian.com/uk-news) | [terms](https://www.theguardian.com/help/terms-of-service); terms_checked; 2026-10-09 | permission_required / permission_required | [guardian](#policy-guardian) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_herald_scotland` [The Herald Scotland](https://www.heraldscotland.com/) | [terms](https://www.heraldscotland.com/terms/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [herald-scotland](#policy-herald-scotland) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_hindustan_times` [Hindustan Times India](https://www.hindustantimes.com/india-news) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_independent_uk` [The Independent UK](https://www.independent.co.uk/news/uk) | [terms](https://www.independent.co.uk/service/rss-feeds-775086.html); terms_checked; 2026-10-09 | permission_required / permission_required | [independent-rss](#policy-independent-rss) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_indian_express` [The Indian Express](https://indianexpress.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_infobae` [Infobae](https://www.infobae.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_insight_crime` [InSight Crime](https://insightcrime.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_japan_times` [The Japan Times](https://www.japantimes.co.jp/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_manchester_evening` [Manchester Evening News](https://www.manchestereveningnews.co.uk/news/) | [terms](https://www.manchestereveningnews.co.uk/terms-conditions/); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [reach-manchester](#policy-reach-manchester) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_mercopress` [MercoPress](https://en.mercopress.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_mexico_news_daily` [Mexico News Daily](https://mexiconewsdaily.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_middle_east_eye` [Middle East Eye](https://www.middleeasteye.net/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_myjoyonline` [MyJoyOnline Ghana](https://www.myjoyonline.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_nation_kenya` [Nation Kenya](https://nation.africa/kenya) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_newsroom_nz` [Newsroom New Zealand](https://newsroom.co.nz/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_northern_echo` [The Northern Echo](https://www.thenorthernecho.co.uk/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_npr_world` [NPR World](https://www.npr.org/sections/world/) | [terms](https://www.npr.org/about-npr/179876898/terms-of-use); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [npr](#policy-npr) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_nytimes_world` [The New York Times World](https://www.nytimes.com/section/world) | [terms](https://www.nytimes.com/content/help/rights/terms/terms-of-service.html); lookup_blocked; attempt 2026-10-09 | unknown / unknown | [nytimes](#policy-nytimes) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_oc_media` [OC Media](https://oc-media.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_pbs_news` [PBS News headlines](https://www.pbs.org/newshour/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_premium_times` [Premium Times Nigeria](https://www.premiumtimesng.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_publico_pt` [Público Portugal](https://www.publico.pt/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_radio_dabanga` [Radio Dabanga](https://www.dabangasudan.org/en) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_rappler` [Rappler](https://www.rappler.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_rfi_en` [RFI English](https://www.rfi.fr/en/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_rfi_fr` [RFI French](https://www.rfi.fr/fr/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_sabc_news` [SABC News](https://www.sabcnews.com/sabcnews/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_sky_uk` [Sky News UK](https://news.sky.com/uk) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_stv_scotland` [STV News Scotland](https://news.stv.tv/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_the_diplomat` [The Diplomat](https://thediplomat.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_the_national_uae` [The National UAE](https://www.thenationalnews.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_times_central_asia` [The Times of Central Asia](https://timesca.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `news_wales_online` [WalesOnline](https://www.walesonline.co.uk/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `nikkei_asia` [Nikkei Asia](https://asia.nikkei.com/) | [terms](https://info.asia.nikkei.com/rss); terms_checked; 2026-10-09 | permission_required / permission_required | [nikkei](#policy-nikkei) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `pravda_ua_en` [Ukrainska Pravda in English](https://www.pravda.com.ua/eng/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `radio_okapi_fr` [Radio Okapi French](https://www.radiookapi.net/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `reliefweb_updates` [ReliefWeb updates](https://reliefweb.int/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `russia_mfa_ru` [Russian MFA news (Russian)](https://mid.ru/ru/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `scmp_news` [South China Morning Post](https://www.scmp.com/) | [terms](https://www.scmp.com/terms-conditions); terms_checked; 2026-10-09 | permission_required / permission_required | [scmp](#policy-scmp) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `tass_en` [TASS English](https://tass.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `times_of_israel` [The Times of Israel](https://www.timesofisrael.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `trt_haber_tr` [TRT Haber Turkish](https://www.trthaber.com/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukrinform_en` [Ukrinform in English](https://www.ukrinform.net/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `un_news` [UN News](https://news.un.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `un_press` [UN press releases and meetings coverage](https://press.un.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `us_dod_news` [US Department of Defense news](https://www.defense.gov/News/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `us_state_travel_advisories` [US State Department travel advisories](https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.html) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `whitehouse_news` [White House news](https://www.whitehouse.gov/news/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-publisher](#policy-unknown-publisher) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Telegram

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `telegram_agentstvonews` [Agentstvo (Telegram)](https://t.me/agentstvonews) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_astrapress` [ASTRA (Telegram)](https://t.me/astrapress) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_bazabazon` [Baza (Telegram)](https://t.me/bazabazon) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_bleepingcomputer` [BleepingComputer (Telegram)](https://t.me/BleepingComputer) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_bloomberg` [Bloomberg (Telegram)](https://t.me/bloomberg) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_boris_rozhin` [Colonelcassad (Telegram)](https://t.me/boris_rozhin) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_centralbank_russia` [Bank of Russia (Telegram)](https://t.me/centralbank_russia) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_deepstateua` [DeepState (Telegram)](https://t.me/DeepStateUA) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_dsns_telegram` [State Emergency Service of Ukraine (Telegram)](https://t.me/dsns_telegram) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_dva_majors` [Dva Majora (Telegram)](https://t.me/dva_majors) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_epoddubny` [Yevgeny Poddubny (Telegram)](https://t.me/epoddubny) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_generalstaffzsu` [General Staff of the Armed Forces of Ukraine (Telegram)](https://t.me/generalstaffZSU) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_idfofficial` [Israel Defense Forces (Telegram)](https://t.me/idfofficial) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_intelslava` [Intel Slava Z (Telegram)](https://t.me/intelslava) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_irna_1313` [IRNA (Telegram)](https://t.me/irna_1313) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_israelwarroom` [Israel War Room (Telegram)](https://t.me/IsraelWarRoom) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_izvestia` [Izvestia (Telegram)](https://t.me/izvestia) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_kommersant` [Kommersant (Telegram)](https://t.me/kommersant) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_kpszsu` [Air Force Command of the Armed Forces of Ukraine (Telegram)](https://t.me/kpszsu) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_kyivindependent_official` [The Kyiv Independent (Telegram)](https://t.me/kyivindependent_official) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mali_actu` [Mali Actu (Telegram)](https://t.me/Mali_Actu) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mchs_official` [EMERCOM of Russia (Telegram)](https://t.me/mchs_official) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mediazzzona` [Mediazona (Telegram)](https://t.me/mediazzzona) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_meduzalive` [Meduza (Telegram)](https://t.me/meduzalive) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mfarussia` [Russian MFA (English) (Telegram)](https://t.me/MFARussia) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mid_russia` [Russian Ministry of Foreign Affairs (Telegram)](https://t.me/MID_Russia) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_milinfolive` [Voenny Osvedomitel (Telegram)](https://t.me/milinfolive) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mod_russia` [Russian Ministry of Defence (Telegram)](https://t.me/mod_russia) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mod_russia_en` [Russian Ministry of Defence (English) (Telegram)](https://t.me/mod_russia_en) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_mvs_ukraine` [Ministry of Internal Affairs of Ukraine (Telegram)](https://t.me/mvs_ukraine) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_nbu_ua` [National Bank of Ukraine (Telegram)](https://t.me/nbu_ua) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_nexta_live` [NEXTA (Telegram)](https://t.me/nexta_live) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_nvua_official` [NV (Telegram)](https://t.me/nvua_official) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_operativnozsu` [Operatyvno ZSU (Telegram)](https://t.me/operativnoZSU) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_osintdefender` [OSINTdefender (Telegram)](https://t.me/OSINTdefender) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ostorozhno_novosti` [Ostorozhno Novosti (Telegram)](https://t.me/ostorozhno_novosti) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_pravda_gerashchenko` [Anton Gerashchenko (Telegram)](https://t.me/Pravda_Gerashchenko) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_presstv` [Press TV (Telegram)](https://t.me/PressTV) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_qudsnen` [Quds News Network (Telegram)](https://t.me/QudsNen) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_radiosvoboda` [Radio Svoboda (Telegram)](https://t.me/radiosvoboda) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rbc_news` [RBC (Telegram)](https://t.me/rbc_news) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_readovkanews` [Readovka (Telegram)](https://t.me/readovkanews) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_redpacketsecurity` [RedPacket Security (Telegram)](https://t.me/RedPacketSecurity) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rian_ru` [RIA Novosti (Telegram)](https://t.me/rian_ru) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rvvoenkor` [Rusvesna war correspondents (Telegram)](https://t.me/RVvoenkor) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_rybar` [Rybar (Telegram)](https://t.me/rybar) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_sashakots` [Kotsnews (Telegram)](https://t.me/sashakots) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_scmpnews` [South China Morning Post (Telegram)](https://t.me/scmpnews) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_shot_shot` [SHOT (Telegram)](https://t.me/shot_shot) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_solovievlive` [Vladimir Solovyov (Telegram)](https://t.me/SolovievLive) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_suspilnenews` [Suspilne News (Telegram)](https://t.me/suspilnenews) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_tass_agency` [TASS (Telegram)](https://t.me/tass_agency) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_thehackernews` [The Hacker News (Telegram)](https://t.me/thehackernews) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_tsaplienko` [Andriy Tsaplienko (Telegram)](https://t.me/Tsaplienko) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrainenow` [Ukraine NOW (Telegram)](https://t.me/UkraineNow) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrenergo` [Ukrenergo (Telegram)](https://t.me/ukrenergo) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrinform_news` [Ukrinform (Telegram)](https://t.me/ukrinform_news) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_ukrpravda_news` [Ukrainska Pravda (Telegram)](https://t.me/ukrpravda_news) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_united24media` [UNITED24 Media (Telegram)](https://t.me/United24media) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_v_zelenskiy_official` [Volodymyr Zelenskyy (Telegram)](https://t.me/V_Zelenskiy_official) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_voenkorkotenok` [Yuri Kotenok (Telegram)](https://t.me/voenkorKotenok) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_vxunderground` [vx-underground (Telegram)](https://t.me/vxunderground) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `telegram_wargonzo` [WarGonzo (Telegram)](https://t.me/wargonzo) | [terms](https://telegram.org/tos/content-licensing); terms_checked; 2026-10-09 | permission_required / permission_required | [telegram](#policy-telegram) | scheduled; ASE_FEEDS_ENABLED; ASE_FEEDS_DISABLED; Admin source controls | high; legal_review, request_permission, replace; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Ukraine dataset

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `ukraine:deepstate` [DeepStateMap frontline](https://deepstatemap.live/) | [terms](https://deepstatemap.live/license.html); terms_checked; 2026-10-09 | permission_required / permission_required | [deepstate](#policy-deepstate) | off_until_configured; ASE_UKRAINE_DEEPSTATE_ACCESS | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:hrmmu_casualties` [Civilian casualty reports](https://ukraine.ohchr.org/en/reports/protection-of-civilians) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:oblast_outlines` [Oblast outlines](https://www.geoboundaries.org/) | [terms](https://www.geoboundaries.org/index.html); terms_checked; 2026-10-09 | conditional / conditional | [geoboundaries](#policy-geoboundaries) | available_asset; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:ocha_frontline` [OCHA humanitarian frontline](https://gis.unocha.org/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_UKRAINE_OCHA_HUMANITARIAN | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:oryx_losses` [Visually confirmed equipment losses](https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | available_asset; No source-specific prerequisite recorded | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:reference_catalogue` [Equipment, forces and timeline notes](https://www.wikidata.org/) | [terms](https://www.wikidata.org/wiki/Wikidata:Licensing); partial_review; 2026-10-09 | unknown / unknown | [wikidata-mixed](#policy-wikidata-mixed) | available_asset; No source-specific prerequisite recorded | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:viina_control` [VIINA territorial control](https://github.com/zhukovyuri/VIINA) | [terms](https://github.com/zhukovyuri/VIINA); terms_checked; 2026-10-09 | conditional / conditional | [viina](#policy-viina) | available_asset; No source-specific prerequisite recorded | medium; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `ukraine:warspotting` [WarSpotting geolocated losses](https://ukr.warspotting.net/) | terms unverified; not_reviewed; not checked | unknown / unknown | [unknown-source](#policy-unknown-source) | off_until_configured; ASE_UKRAINE_WARSPOTTING | high; request_permission, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

## Youtube

| Source ID and discovery link | Terms and check | C / H | Attribution / redistribution | Current default and gates | Risk and action |
| --- | --- | --- | --- | --- | --- |
| `yt_al_jazeera` [Al Jazeera English (YouTube)](https://www.youtube.com/@AlJazeeraEnglish) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_ap` [Associated Press (YouTube)](https://www.youtube.com/@AssociatedPress) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_bbc_news` [BBC News (YouTube)](https://www.youtube.com/@BBCNews) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_black_hat` [Black Hat (YouTube)](https://www.youtube.com/@BlackHatOfficialYT) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_cgtn` [CGTN (YouTube)](https://www.youtube.com/@CGTN) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_chatham_house` [Chatham House (YouTube)](https://www.youtube.com/@ChathamHouse) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_cnbc` [CNBC (YouTube)](https://www.youtube.com/@CNBC) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_defcon` [DEF CON (YouTube)](https://www.youtube.com/@DEFCONConference) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_dw_news` [DW News (YouTube)](https://www.youtube.com/@dwnews) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_economist` [The Economist (YouTube)](https://www.youtube.com/@TheEconomist) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_euronews` [euronews (YouTube)](https://www.youtube.com/@euronews) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_european_commission` [European Commission (YouTube)](https://www.youtube.com/@EuropeanCommission) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_financial_times` [Financial Times (YouTube)](https://www.youtube.com/@FinancialTimes) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_france24` [FRANCE 24 English (YouTube)](https://www.youtube.com/@FRANCE24English) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_guardian` [The Guardian (YouTube)](https://www.youtube.com/@guardiannews) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_kyiv_independent` [The Kyiv Independent (YouTube)](https://www.youtube.com/@kyivindependent) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_meduza` [Meduza (YouTube)](https://www.youtube.com/@meduzalive) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_middle_east_eye` [Middle East Eye (YouTube)](https://www.youtube.com/@MiddleEastEye) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_nato` [NATO (YouTube)](https://www.youtube.com/@NATO) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_number_10` [Number10gov (YouTube)](https://www.youtube.com/@10DowningStreet) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_pbs_newshour` [PBS NewsHour (YouTube)](https://www.youtube.com/@PBSNewsHour) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_perun` [Perun (YouTube)](https://www.youtube.com/@PerunAU) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_reuters` [Reuters (YouTube)](https://www.youtube.com/@Reuters) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_scmp` [South China Morning Post (YouTube)](https://www.youtube.com/@SouthChinaMorningPost) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_sky_news` [Sky News (YouTube)](https://www.youtube.com/@SkyNews) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_taiwan_plus` [TaiwanPlus News (YouTube)](https://www.youtube.com/@TaiwanPlusNews) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_united_nations` [United Nations (YouTube)](https://www.youtube.com/@unitednations) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_war_on_the_rocks` [War on the Rocks (YouTube)](https://www.youtube.com/@WarontheRocks) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |
| `yt_white_house` [The White House (YouTube)](https://www.youtube.com/@WhiteHouse) | [terms](https://developers.google.com/youtube/terms/developer-policies); partial_review; 2026-10-09 | unknown / unknown | [youtube](#policy-youtube) | off_until_configured; ASE_YOUTUBE_API_KEY | high; attribute, legal_review; Verify this exact publisher/product and intended retention, export and hosted use before commercial enablement. |

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

### Policy acled

**ACLED event data**: Eligibility and licence-specific EULA.

[Primary terms](https://acleddata.com/eula). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Prominent ACLED credit, access date, data scope and changes, including visualisations.

Redistribution: Raw sharing restricted. Non-commercial external outputs must be transformative and prevent dataset reconstruction; a dashboard alone is insufficient.

Corporate/public-sector and third-party-service permissions require the appropriate agreement. Account/API entitlement is not redistribution permission.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://acleddata.com/contentusage); [reference 2](https://acleddata.com/attributionpolicy). These links are not separate verification dates.

### Policy adsb-fi

**adsb.fi open data**: Personal, non-commercial terms.

[Primary terms](https://github.com/adsbfi/opendata/blob/main/README.md). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Cite adsb.fi and link its home page.

Redistribution: No licensing, sale, rental or lease of the data/service under the public terms.

Commercial enquiries are invited. Current aviation code uses adsb.lol instead; do not confuse the providers or assume personal use covers team hosting.

Risk: high. Action: request_permission, legal_review.

### Policy adsb-lol

**ADSB.lol API data**: ODbL 1.0.

[Primary terms](https://www.adsb.lol/docs/open-data/api/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit ADSB.lol and ODbL; preserve database notices.

Redistribution: ODbL attribution/share-alike and derivative-database obligations apply.

The API page specifies ODbL. Its separate contributor CC0 grant is not a replacement API-output licence. Review derived databases and publication; no availability guarantee.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://opendatacommons.org/licenses/odbl/1-0/); [reference 2](https://www.adsb.lol/privacy-license/). These links are not separate verification dates.

### Policy aljazeera

**Al Jazeera**: Restricted.

[Primary terms](https://www.aljazeera.com/terms-and-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source credit.

Redistribution: Commercial reuse and automated collection need permission.

Review section 6.

Risk: high. Action: request_permission, legal_review.

### Policy anadolu

**Anadolu Agency**: Subscription agreement required.

[Primary terms](https://www.aa.com.tr/tr/ayrimcilikhatti/p/yasal-uyari). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official Turkish notice requires website publisher subscription and restricts use and transfer outside the contract; no project subscription or onward-use scope established.

Risk: high. Action: request_permission, legal_review.

### Policy bbc-rss

**BBC RSS**: Current terms lookup blocked; older BBC terms available.

[Primary terms](https://www.bbc.co.uk/usingthebbc/terms/). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Older terms require prominent BBC News name and linked source; preserve embedded branding.

Redistribution: No current commercial or multi-user grant verified; do not treat historical personal-use terms as clearance.

Current page blocked by robots. Official September 2022 PDF section 15 requires permission for business RSS and a metadata licence. Confirm current scope before use.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://downloads.bbc.co.uk/usingthebbc/bbc_terms_of_use_19September2022english.pdf). These links are not separate verification dates.

### Policy bellingcat

**Bellingcat**: Unverified.

[Primary terms](https://www.bellingcat.com/terms-and-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms lookup failed. Establish current publication-specific licensing before approving collection, hosted excerpts or exports.

Risk: high. Action: request_permission, legal_review.

### Policy bls

**US Bureau of Labor Statistics**: Public-domain BLS material; photo/illustration exceptions.

[Primary terms](https://www.bls.gov/bls/linksite.htm). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite BLS; do not use its emblem without authority.

Redistribution: Covered public-domain statistics may be redistributed; exclude separately copyrighted material.

BLS permits reuse of its public-domain publications; emblem and previously copyrighted images are excluded.

Risk: low. Action: keep, attribute.

### Policy bluesky

**Bluesky user content**: Platform terms; user-owned content.

[Primary terms](https://bsky.social/about/support/tos). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve author, post URL and platform identity.

Redistribution: Bluesky platform licences do not establish blanket third-party report/export rights.

Review developer terms, deletion propagation and individual author rights; AT Protocol accessibility is not a public-domain dedication.

Risk: high. Action: request_permission, legal_review.

### Policy camera-owner-rights

**Camera owner and host rights not reviewed**: Index metadata and camera media have separate rights.

Status: `not_reviewed`. Checked: not verified. Attempted: not attempted.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Keep each camera owner and provider credit; do not substitute directory credit.

Redistribution: Public stream/embed URLs and an allowlisted host do not authorise copying, proxying, capture, resale or report export.

Review each host, camera owner and delivery method. OSIRIS MIT catalogue code/data notices do not license third-party streams. A directory or government index does not establish rights in every image.

Risk: high. Action: request_permission, legal_review.

### Policy celestrak

**CelesTrak service usage**: Usage policy reviewed; commercial redistribution licence not established.

[Primary terms](https://celestrak.org/usage-policy.php). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Retain CelesTrak and upstream provenance pending rights clarification.

Redistribution: Free service access does not by itself establish downstream licensing rights.

Policy updated 22 May 2026: download once per update (GP every two hours); stop on non-200 responses. Check scheduler/backoff compliance separately.

Risk: medium. Action: attribute, legal_review.

### Policy cgtn

**CGTN**: Personal, non-commercial site access.

[Primary terms](https://www.cgtn.com/terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve CGTN and contributor copyright notices; branding is separately restricted.

Redistribution: No commercial resale, third-party copying or automated extraction grant under ordinary access.

Terms updated 1 May 2026 restrict extraction, derivatives and third-party copying. Commercial reuse needs express written consent.

Risk: high. Action: request_permission, legal_review.

### Policy cloudflare-radar

**Cloudflare Radar API data**: CC BY-NC 4.0 (API/download data).

[Primary terms](https://radar.cloudflare.com/about). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit Cloudflare Radar, source link and CC BY-NC 4.0; identify changes.

Redistribution: Non-commercial sharing subject to the licence. Commercial display/export needs a separate grant.

API data is distinct from CC BY 4.0 embeddable/downloadable graphs. Non-commercial hosted suitability is fact-specific; no project exception verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://creativecommons.org/licenses/by-nc/4.0/). These links are not separate verification dates.

### Policy cna-rss

**CNA RSS**: Personal, non-commercial RSS terms.

[Primary terms](https://www.channelnewsasia.com/rss/rssterms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Direct link to the full article; no intermediate page; preserve supplied content.

Redistribution: Third-party distribution, forwarding, licensing and transfer restricted, including non-commercial use.

Attribution alone does not authorise multi-user redistribution. Seek a separate content-hosting agreement.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.channelnewsasia.com/contact-us/help-and-feedback). These links are not separate verification dates.

### Policy crisisgroup

**International Crisis Group**: Unverified.

[Primary terms](https://www.crisisgroup.org/legal). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary legal page returned 403; search found a feed description but no current republication grant.

Risk: high. Action: request_permission, legal_review.

### Policy crossref

**Crossref metadata**: Metadata reuse without restriction, as described by Crossref.

[Primary terms](https://www.crossref.org/services/metadata-retrieval/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Preserve Crossref provenance, authors and DOI links.

Redistribution: Metadata access is not a grant to republish linked full articles or third-party images.

Review any source-specific copyrighted abstract/full-text field before exporting more than the implemented metadata.

Risk: medium. Action: keep, attribute, legal_review.

### Policy dawn

**Dawn**: Restricted.

[Primary terms](https://www.dawn.com/terms/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve notices.

Redistribution: Commercial reuse requires prior written permission.

Review intellectual-property terms.

Risk: high. Action: request_permission, legal_review.

### Policy deepstate

**DeepState API**: Provider API licence; commercial use by prior agreement.

[Primary terms](https://deepstatemap.live/license.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve DeepState identification and approved links/branding.

Redistribution: API distribution, publication, proxying or transfer is restricted without authorisation.

Visual/text material reuse rules are separate from API rights. Hosted cache/display and exports require express scope confirmation; no grant verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://api.deepstatemap.live/request). These links are not separate verification dates.

### Policy digitraffic

**Fintraffic Digitraffic**: CC BY 4.0 data and service terms.

[Primary terms](https://www.digitraffic.fi/en/terms-of-service/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Source: Fintraffic / digitraffic.fi, licence CC BY 4.0; identify changes.

Redistribution: Covered data may be reused with licence conditions; verify any third-party exception.

Review camera-image scope separately where contributor rights differ; preserve rate limits and service identification.

Risk: medium. Action: keep, attribute, legal_review.

### Policy dw-rss

**Deutsche Welle RSS**: Distribution registration and product-specific terms.

[Primary terms](https://b2b.dw.com/page/dw-terms-conditions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

DW promotes German News Service integration, but that is a specific registered offering. Do not assume the existing world/business feeds have its rights. Exact feed and report/export agreement unverified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://amp.dw.com/en/benefit-from-smart-content-made-in-germany/a-19470839). These links are not separate verification dates.

### Policy ecb

**ECB reference rates and releases**: ECB reproduction conditions.

[Primary terms](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite ECB, reproduce accurately and identify modifications.

Redistribution: Sold documents require notice before payment and at access that ECB information is freely available; authored papers have separate restrictions.

Reference rates are informational, not transaction prices. Apply the free-source notice to relevant commercial reports/subscriptions.

Risk: medium. Action: keep, attribute, legal_review.

### Policy economist

**The Economist**: Permission/licensing service.

[Primary terms](https://www.economist.com/syndication/permissions). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Official permissions page offers a licence for the specified reuse. General terms direct access blocked; no project licence or automated-feed/AI scope verified.

Risk: high. Action: request_permission, legal_review.

### Policy eox-2024

**EOxCloudless 2024**: CC BY-NC-SA 4.0 or suitable EOX commercial licence.

[Primary terms](https://cloudless.eox.at/license-non-commercial). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH (Contains modified Copernicus Sentinel data 2024).

Redistribution: Preserve visible attribution; independent downstream reuse/sublicensing needs scope review.

2018–2025 imagery is non-commercial under published free terms. The 2016 CC BY offer does not cover the implemented 2024 layer. Map export declarations are not licence verification.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://cloudless.eox.at/documentation/license). These links are not separate verification dates.

### Policy france24

**France 24**: Unverified.

[Primary terms](https://www.france24.com/en/legal-notice). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary lookup inaccessible; site search also blocked. Obtain current terms and precise feed/hosted rights from the publisher.

Risk: high. Action: request_permission, legal_review.

### Policy gdelt

**GDELT datasets**: GDELT published data-use terms.

[Primary terms](https://www.gdeltproject.org/about.html#termsofuse). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Cite GDELT and link its website.

Redistribution: Dataset redistribution, mirrors and commercial use permitted under the published terms.

This covers GDELT data, not copyright in linked news articles, photographs or publisher excerpts.

Risk: medium. Action: attribute, legal_review.

### Policy geoboundaries

**geoBoundaries**: CC BY 4.0.

[Primary terms](https://www.geoboundaries.org/index.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit geoBoundaries and its requested Runfola et al. (2020) citation.

Redistribution: Commercial reuse and redistribution with attribution, licence notice and indication of changes.

Confirm the packaged boundary release and preserve its source-specific metadata.

Risk: medium. Action: attribute, legal_review.

### Policy gfw

**Global Fishing Watch**: CC BY-NC 4.0 default plus service/dataset terms.

[Primary terms](https://globalfishingwatch.org/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Source/access date, licence and provider notices; include the specified apparent-fishing disclaimer where applicable.

Redistribution: Non-commercial reuse is conditional and dataset-specific; terms additionally address same-term reuse.

API/bulk registration is not commercial permission. Third-party data and hosted audience need review; software Apache licensing is not a data grant.

Risk: high. Action: request_permission, legal_review.

### Policy gleif

**GLEIF LEI data**: CC0 data with access-service terms.

[Primary terms](https://www.gleif.org/en/meta/lei-data-terms-of-use). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: GLEIF provenance recommended; no CC0 attribution condition.

Redistribution: CC0 reuse of covered LEI data; service terms and unrelated materials remain separate.

No licence claim is made for linked company filings or third-party source documents.

Risk: low. Action: keep, attribute.

### Policy google-news

**Google News aggregation**: Google service terms; publisher content separately owned.

[Primary terms](https://policies.google.com/terms). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

The Other content section requires publisher permission or a lawful basis. General Google access does not license third-party News material. RSS-specific permission remains unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy govuk

**GOV.UK published content**: OGL v3 for covered content, with exceptions.

[Primary terms](https://www.gov.uk/help/terms-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Attribute the originating department and OGL; identify third-party material.

Redistribution: Reuse covered Crown content under OGL; exclude content carrying separate rights.

GOV.UK permits feed reuse. Service-specific terms, personal data, logos and third-party rights still need review.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). These links are not separate verification dates.

### Policy guardian

**Guardian**: Restricted.

[Primary terms](https://www.theguardian.com/help/terms-of-service). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve notices.

Redistribution: Commercial aggregation and AI reuse require approval.

Review section 3.

Risk: high. Action: request_permission, legal_review.

### Policy herald-scotland

**Herald Scotland**: Unverified.

[Primary terms](https://www.heraldscotland.com/terms/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms and domain search blocked; exact publisher rights remain unresolved.

Risk: high. Action: request_permission, legal_review.

### Policy independent-rss

**The Independent RSS**: Personal, non-commercial RSS terms.

[Primary terms](https://www.independent.co.uk/service/rss-feeds-775086.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Keep publisher notices and links; agreed licensing credit remains unverified.

Redistribution: Republication needs licensing; general terms restrict network storage accessible to others.

Request hosted display, selected-excerpt retention and report-export permission before relying on these uses.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.independent.co.uk/service/user-policies-a6184151.html). These links are not separate verification dates.

### Policy ioda

**IODA public data**: Terms not extractable from current page.

[Primary terms](https://ioda.inetintel.cc.gatech.edu/resources). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Credit IODA/Georgia Tech and originating measurements pending exact terms.

Redistribution: No verified commercial or hosted redistribution grant.

Lookup returned only a logo. Existing research acknowledgement is not permission; live feed paths have different gates.

Risk: high. Action: request_permission, legal_review.

### Policy iranwire

**IranWire**: Personal use; commercial licence required.

[Primary terms](https://iranwire.com/en/pages/terms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit IranWire and identified contributors; retain linked source.

Redistribution: Commercial reuse requires licence; personal extracts are not an onward-hosting grant.

Terms reserve commercial use and prohibit text/data mining and scraping. Quotation provision does not establish rights for the implemented hosted collector or AI reports.

Risk: high. Action: request_permission, legal_review.

### Policy kyiv-independent

**Kyiv Independent**: Unverified.

[Primary terms](https://kyivindependent.com/terms-of-use/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms candidate could not be retrieved; do not confuse this publisher with The Independent.

Risk: high. Action: request_permission, legal_review.

### Policy lemonde

**Le Monde RSS**: Personal, non-professional and non-collective RSS use.

[Primary terms](https://www.lemonde.fr/le-monde-et-vous/article/2025/07/14/les-flux-rss-du-monde_fr_5498778_3237.html). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve Le Monde and author attribution and original link.

Redistribution: Team or commercial republication is outside the personal RSS allowance.

Other RSS exploitation requires authorisation and payment. Verify language-edition/feed scope and saved evidence with syndication.

Risk: high. Action: request_permission, legal_review.

### Policy meduza

**Meduza**: Unverified.

[Primary terms](https://meduza.io/en/pages/terms). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms candidate inaccessible and primary-domain search did not establish current reuse terms. Ask publisher for the current policy and scope.

Risk: high. Action: request_permission, legal_review.

### Policy mitre

**MITRE ATT&CK**: MITRE ATT&CK licence.

[Primary terms](https://attack.mitre.org/resources/legal-and-branding/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain MITRE copyright designation and full licence in copies.

Redistribution: Research/development/commercial copying permitted with the specified notices.

Trademark/branding and third-party linked reports remain separate.

Risk: low. Action: keep, attribute.

### Policy mixed-evidence

**Mixed or user-supplied evidence**: Per-item rights; no blanket licence.

Status: `not_reviewed`. Checked: not verified. Attempted: not attempted.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve originating author/provider, licence and any required notices.

Redistribution: Each selected item retains its own restrictions; combining it into a report grants no new rights.

Applies to uploads, retained feeds, mixed curated assets and web-search evidence. Review source-specific licences, privacy, image rights and onward use.

Risk: high. Action: request_permission, legal_review.

### Policy nasa-data

**NASA Earth science products**: NASA-led mission data CC0 unless marked otherwise; contributor exceptions.

[Primary terms](https://www.earthdata.nasa.gov/engage/open-data-services-software/data-use-policy). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Use product-specific NASA/LANCE/FIRMS/GIBS credit and dataset citation.

Redistribution: Check each product or contributing source restriction; no blanket NASA-site clearance.

General policy located, but per-product and EONET contributing-source terms need completion. The older Worldview copyright URL was inaccessible in this lookup.

Risk: high. Action: attribute, legal_review.

### Policy natural-earth

**Natural Earth**: Public domain.

[Primary terms](https://www.naturalearthdata.com/about/terms-of-use/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit optional; suggested: Made with Natural Earth.

Redistribution: Electronic and printed redistribution and modification permitted.

The provider explicitly permits commercial use. This does not settle third-party overlays or jurisdiction-specific boundary presentation.

Risk: low. Action: keep.

### Policy ncsc

**UK NCSC**: OGL v3 for covered Crown content.

[Primary terms](https://www.ncsc.gov.uk/section/about-this-website/terms-and-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Acknowledge NCSC source and link OGL where possible.

Redistribution: Covered Crown content reusable under OGL; obtain third-party and logo permission separately.

Official indexed terms allow OGL reuse; third-party images/material and logos are excluded. Confirm the exact report notices.

Risk: medium. Action: keep, attribute, legal_review.

### Policy nikkei

**Nikkei Asia RSS**: Personal, non-commercial headline reading.

[Primary terms](https://info.asia.nikkei.com/rss). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No onward republication/copying/redistribution grant in the public RSS terms.

Feed terms expressly prohibit republication, copying and redistribution. A subscription does not establish the required separate scope.

Risk: high. Action: request_permission, legal_review.

### Policy npr

**NPR**: Unverified.

[Primary terms](https://www.npr.org/about-npr/179876898/terms-of-use). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Primary terms blocked; indexed programme notices reserve rights and refer to permission policy. No current grant verified.

Risk: high. Action: request_permission, legal_review.

### Policy nws

**NOAA National Weather Service data**: Public domain for NWS-produced information unless otherwise noted.

[Primary terms](https://www.weather.gov/disclaimer). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain notices; credit NWS; do not imply endorsement or present modified data as official.

Redistribution: Lawful reuse permitted for covered NWS data; third-party material requires separate review.

Applies to NWS/NHC/SWPC/tsunami information, not every item hosted anywhere on noaa.gov.

Risk: medium. Action: attribute, legal_review.

### Policy nytimes

**New York Times**: Unverified.

[Primary terms](https://www.nytimes.com/content/help/rights/terms/terms-of-service.html). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms retrieval and primary-domain search blocked. Obtain current terms and RSS syndication permission.

Risk: high. Action: request_permission, legal_review.

### Policy ooni

**OONI data**: CC BY-NC-SA 4.0.

[Primary terms](https://github.com/ooni/license/blob/master/data/LICENSE.md). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Credit OONI, link source and licence, identify changes.

Redistribution: Non-commercial sharing/adaptations subject to attribution and share-alike; no commercial grant verified.

The acknowledgement setting records an operator assertion, not permission. Review whether the actual hosted use is non-commercial and the effect on derived outputs.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://creativecommons.org/licenses/by-nc-sa/4.0/). These links are not separate verification dates.

### Policy open-meteo

**Open-Meteo data and service**: CC BY 4.0 data; free API non-commercial; commercial service subscription.

[Primary terms](https://open-meteo.com/en/terms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `conditional`.

Attribution: Credit Open-Meteo beside displayed data, link source/licence and identify changes.

Redistribution: Data redistribution is allowed under CC BY 4.0; API subscription/access conditions still apply.

Commercial calls to the free API are not authorised by the open data licence. Paid entitlement is unverified; no current catalogue connector.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://open-meteo.com/en/licence). These links are not separate verification dates.

### Policy openalex

**OpenAlex metadata**: CC0 metadata; service tiers separate.

[Primary terms](https://help.openalex.org/access/overview/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: OpenAlex provenance recommended; retain original publication/DOI references.

Redistribution: Metadata reuse permitted; this does not relicense linked full text or images.

Data openness does not establish a particular API tier or allowance.

Risk: medium. Action: keep, attribute.

### Policy openfreemap

**OpenFreeMap maps**: Commercial use stated; OSM/ODbL and OpenMapTiles rights remain.

[Primary terms](https://openfreemap.org/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: OpenFreeMap (optional), © OpenMapTiles, Data from OpenStreetMap; retain links and printed/export credit.

Redistribution: Observe underlying data/style licences and ODbL. Service terms do not grant unrestricted bulk extraction.

Commercial web/app maps expressly contemplated. Public service has no SLA; reconcile automated bulk collection with service terms. Existing image export must retain credits.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://openfreemap.org/tos/); [reference 2](https://www.openstreetmap.org/copyright). These links are not separate verification dates.

### Policy opensanctions

**OpenSanctions**: Public CC BY-NC 4.0; separate API/bulk commercial contracts.

[Primary terms](https://www.opensanctions.org/licensing/). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: CC credit/link/change notice for public data; confirm paid-contract requirements.

Redistribution: Bulk internal, bulk reseller and API grants differ. Substantial standalone dataset redistribution is restricted.

Current paid API terms contemplate customer-facing products; do not apply the bulk internal-only rule to that contract. No purchased entitlement or catalogue connector verified.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://www.opensanctions.org/docs/terms/data/202509/); [reference 2](https://www.opensanctions.org/docs/terms/api/202609/); [reference 3](https://www.opensanctions.org/docs/commercial/exemption/). These links are not separate verification dates.

### Policy osm

**OpenStreetMap data**: ODbL 1.0.

[Primary terms](https://www.openstreetmap.org/copyright). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: © OpenStreetMap contributors; link copyright/ODbL and preserve required notices.

Redistribution: Data/derivative-database share-alike conditions differ from produced-work image attribution.

Data rights do not grant unlimited use of OSM or third-party tile/geocoding/routing servers. Review service policy separately.

Risk: medium. Action: keep, attribute, legal_review.

Related evidence: [reference 1](https://opendatacommons.org/licenses/odbl/1-0/). These links are not separate verification dates.

### Policy osm-service

**OSM-derived public service**: ODbL data; service entitlement not reviewed.

[Primary terms](https://www.openstreetmap.org/copyright). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve OpenStreetMap and service attribution.

Redistribution: Data licence does not settle hosted service quotas, result caching or redistribution.

Photon/Valhalla/Overpass are separate operators. Review exact public-instance terms or self-host before approving commercial service use.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://github.com/komoot/photon); [reference 2](https://valhalla.openstreetmap.de/). These links are not separate verification dates.

### Policy reach-manchester

**Manchester Evening News**: Unverified.

[Primary terms](https://www.manchestereveningnews.co.uk/terms-conditions/). Status: `lookup_blocked`. Checked: not verified. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: No project-specific onward-sharing or export grant established.

Terms redirected to an inaccessible Tollbit page; primary-domain search did not establish reuse rights.

Risk: high. Action: request_permission, legal_review.

### Policy reddit

**Reddit Data API**: Data API Terms and Responsible Builder Policy.

[Primary terms](https://redditinc.com/policies/data-api-terms). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Developer-policy attribution and owner restrictions; exact display specification needs review.

Redistribution: Only approved app use; limited display rights are not general resale or independent redistribution.

Current policy requires API approval and written commercial approval. Retention, deletion and sensitive inference need review. No current catalogue connector.

Risk: high. Action: request_permission, legal_review.

Related evidence: [reference 1](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy). These links are not separate verification dates.

### Policy scmp

**South China Morning Post**: Personal, non-commercial access; written permission for reuse.

[Primary terms](https://www.scmp.com/terms-conditions). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Preserve source, author, date and links; confirm required credit.

Redistribution: Written permission required for copying/distribution and restricted automated/AI uses; third-party rights remain.

15 September 2026 terms section 3 covers extracts and metadata, automated collection, analytics and AI/RAG. Primary indexed terms retrieved after direct fetch failed; no exception verified.

Risk: high. Action: request_permission, legal_review.

### Policy telegram

**Telegram content**: Restricted platform content licence; owner rights remain.

[Primary terms](https://telegram.org/tos/content-licensing). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `permission_required`. Hosted/multi-user: `permission_required`.

Attribution: Retain channel/author and post link; credit is not permission.

Redistribution: Non-standard access and transfer restricted. Content-owner conditions apply separately.

The current terms broadly prohibit scraping/aggregation and use for AI development, enhancement or deployment without specific consent. Legal review needed for existing collectors, model input and frozen report evidence.

Risk: high. Action: legal_review, request_permission, replace.

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

### Policy usgs

**USGS-produced data**: US public-domain USGS-produced data; third-party exceptions.

[Primary terms](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit USGS and retain third-party notices where present.

Redistribution: USGS-produced information reusable; non-USGS images and other supplied materials can retain copyright.

This assessment covers earthquake observations, not a blanket licence for every linked page or image.

Risk: medium. Action: keep, attribute, legal_review.

### Policy viina

**VIINA territorial-control data**: ODbL 1.0; database contents licence.

[Primary terms](https://github.com/zhukovyuri/VIINA). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Retain VIINA notices and follow the README citation requirements.

Redistribution: ODbL attribution/share-alike and access to adapted databases may apply to public outputs.

Review the exact adapted snapshot and report exports. Linked publishers retain separate article rights.

Risk: medium. Action: attribute, legal_review.

### Policy wikidata-mixed

**Wikidata plus separately licensed media**: Structured data CC0; other text/media separate.

[Primary terms](https://www.wikidata.org/wiki/Wikidata:Licensing). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: Wikidata credit useful; preserve individual Commons author/licence/change notices.

Redistribution: CC0 facts do not license linked portraits, photographs, prose or curated source material.

Review every included image and seed source before approving the whole mixed catalogue. Do not label the complete asset CC0.

Risk: high. Action: attribute, legal_review.

### Policy wri-power

**WRI Global Power Plant Database**: CC BY 4.0 (database); MIT (code).

[Primary terms](https://github.com/wri/global-power-plant-database). Status: `terms_checked`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `conditional`. Hosted/multi-user: `conditional`.

Attribution: Credit WRI Global Power Plant Database and link licence/source.

Redistribution: Database reuse with CC BY conditions; retain provenance and identify alterations.

Latest published database version is 1.3.0; maintenance stopped. Software MIT is separate from data rights.

Risk: medium. Action: attribute, legal_review.

### Policy youtube

**YouTube Data API metadata**: YouTube API terms and developer policies.

[Primary terms](https://developers.google.com/youtube/terms/developer-policies). Status: `partial_review`. Checked: 2026-10-09. Attempted: 2026-10-09.

Commercial: `unknown`. Hosted/multi-user: `unknown`.

Attribution: YouTube-required branding/links and uploader attribution; review exact presentation.

Redistribution: Non-authorised API data requires delete/refresh within 30 days; redistribution and independent media reuse are not blanket permissions.

Review saved evidence, exports, retention/deletion and application privacy/terms before approving use. A key alone does not establish compliance.

Risk: high. Action: attribute, legal_review.

## Camera host review queue

All 120 configured media/frame hosts remain under the [camera-owner-rights](#policy-camera-owner-rights) policy. This is an allowlist inventory, not evidence that every camera on a host is authorised. No live stream was fetched. Confirm the actual owner, embedding, proxying, recording, export and commercial terms separately.

| Host | Configured use | Rights |
| --- | --- | --- |
| `511.alaska.gov` | media | unknown |
| `511.alberta.ca` | media | unknown |
| `511.gnb.ca` | media | unknown |
| `511.idaho.gov` | media | unknown |
| `511.novascotia.ca` | media | unknown |
| `511ga.org` | media | unknown |
| `511in.org` | media | unknown |
| `511la.org` | media | unknown |
| `511nl.ca` | media | unknown |
| `511ny.org` | media | unknown |
| `511on.ca` | media | unknown |
| `511yukon.ca` | media | unknown |
| `apps.derbyshire.gov.uk` | media | unknown |
| `atmsqf.iowadot.gov` | media | unknown |
| `az511.gov` | media | unknown |
| `cam.river.go.jp` | media | unknown |
| `cameras.qldtraffic.qld.gov.au` | media | unknown |
| `camsecure.co` | media | unknown |
| `cctv-ss01.thb.gov.tw` | media | unknown |
| `cctv-ss02.thb.gov.tw` | media | unknown |
| `cctv-ss03.thb.gov.tw` | media | unknown |
| `cctv-ss04.thb.gov.tw` | media | unknown |
| `cctv-ss05.thb.gov.tw` | media | unknown |
| `cctv-ss06.thb.gov.tw` | media | unknown |
| `cctv-ss07.thb.gov.tw` | media | unknown |
| `cdn.uab.org` | media | unknown |
| `cdnuiwebcams.utinform.hu` | media | unknown |
| `ctroads.org` | media | unknown |
| `cwwp2.dot.ca.gov` | media | unknown |
| `d1wse1.its.nv.gov` | media | unknown |
| `d1wse2.its.nv.gov` | media | unknown |
| `d1wse3.its.nv.gov` | media | unknown |
| `d1wse4.its.nv.gov` | media | unknown |
| `d1wse5.its.nv.gov` | media | unknown |
| `d2wse1.its.nv.gov` | media | unknown |
| `d2wse2.its.nv.gov` | media | unknown |
| `d3wse1.its.nv.gov` | media | unknown |
| `dcc.ussgroup.co.uk` | media | unknown |
| `download.data.grandlyon.com` | media | unknown |
| `drivebc.ca` | media | unknown |
| `drivenc.gov` | media | unknown |
| `eismoinfo.lt` | media | unknown |
| `etraffic.dgt.es` | media | unknown |
| `files.argyll-bute.gov.uk` | media | unknown |
| `fl511.com` | media | unknown |
| `gsccam.butlersheriff.org` | media | unknown |
| `home-solutions.bg` | media | unknown |
| `hotline.gov.sk.ca` | media | unknown |
| `images.data.gov.sg` | media | unknown |
| `images.drivebc.ca` | media | unknown |
| `images.gov.im` | media | unknown |
| `images.wsdot.wa.gov` | media | unknown |
| `infocar.dgt.es` | media | unknown |
| `informo.madrid.es` | media | unknown |
| `ipcamlive.com` | frames | unknown |
| `irecam.carsprogram.org` | media | unknown |
| `its.act.pr.gov` | media | unknown |
| `itsstreamingbr.dotd.la.gov` | media | unknown |
| `itsstreamingbr2.dotd.la.gov` | media | unknown |
| `itsstreamingno.dotd.la.gov` | media | unknown |
| `kamera.atlas.vegvesen.no` | media | unknown |
| `kamera.vegvesen.no` | media | unknown |
| `kamere.amss.org.rs` | media | unknown |
| `kscam.carsprogram.org` | media | unknown |
| `ls.tkchopin.pl` | media | unknown |
| `meteo.chavo.biz` | media | unknown |
| `micamerasimages.net` | media | unknown |
| `netrafficcams.co.uk` | media | unknown |
| `newengland511.org` | media | unknown |
| `opendata.toronto.ca` | media | unknown |
| `pics.smartburgas.eu` | media | unknown |
| `prod-ut.ibi511.com` | media | unknown |
| `public.carsprogram.org` | media | unknown |
| `ristmikud.tallinn.ee` | media | unknown |
| `s3-eu-west-1.amazonaws.com` | media | unknown |
| `s51.nysdot.skyvdn.com` | media | unknown |
| `s52.nysdot.skyvdn.com` | media | unknown |
| `s53.nysdot.skyvdn.com` | media | unknown |
| `s7.nysdot.skyvdn.com` | media | unknown |
| `s9.nysdot.skyvdn.com` | media | unknown |
| `skysfs4.trafficwise.org` | media | unknown |
| `stream.inmoves.nl` | media | unknown |
| `stream.uzivobeograd.rs` | media | unknown |
| `stream1.mgw-is.uk` | media | unknown |
| `stream2.mgw-is.uk` | media | unknown |
| `streaming1.neotel.net.mk` | media | unknown |
| `tarktee.transpordiamet.ee` | media | unknown |
| `tdcctv.data.one.gov.hk` | media | unknown |
| `towercam.butlersheriff.org` | media | unknown |
| `traffic.ottawa.ca` | media | unknown |
| `trafficnz.info` | media | unknown |
| `travelmidwest.com` | media | unknown |
| `tripcheck.com` | media | unknown |
| `vefmyndavelar.vegagerdin.is` | media | unknown |
| `video.autostrade.it` | media | unknown |
| `video.dot.state.mn.us` | media | unknown |
| `ville.montreal.qc.ca` | media | unknown |
| `wc-heli.chuv.ch` | media | unknown |
| `weathercam.digitraffic.fi` | media | unknown |
| `webcams.asfinag.at` | media | unknown |
| `webcams.transport.nsw.gov.au` | media | unknown |
| `www.511pa.com` | media | unknown |
| `www.cita.lu` | media | unknown |
| `www.cne-siar.gov.uk` | media | unknown |
| `www.dgt.es` | media | unknown |
| `www.drivebc.ca` | media | unknown |
| `www.drivenc.gov` | media | unknown |
| `www.kcscout.net` | media | unknown |
| `www.manitoba511.ca` | media | unknown |
| `www.northyorks.gov.uk` | media | unknown |
| `www.nvroads.com` | media | unknown |
| `www.quebec511.info` | media | unknown |
| `www.slupsk.pl` | media | unknown |
| `www.tamarcrossings.org.uk` | media | unknown |
| `www.travelmidwest.com` | media | unknown |
| `www.tripcheck.com` | media | unknown |
| `www.vegagerdin.is` | media | unknown |
| `www.westmorlandandfurness.gov.uk` | media | unknown |
| `www.youtube.com` | frames | unknown |
| `wzmedia.dot.ca.gov` | media | unknown |

## Maintenance

Review JSON changes by source ID; never copy a permissive policy solely because another product uses the same provider. Keep grants and correspondence in controlled records, with a non-sensitive reference if needed. Recheck terms before a commercial release and when a provider, product, endpoint or licence changes.

Regenerate this file with `python scripts/render_source_licences.py`; verify it with `--check`. Run `uv run pytest tests/test_source_licences.py --no-cov` in `backend`. Adding a catalogue ID without an explicit row must fail. No network lookup occurs during these checks.

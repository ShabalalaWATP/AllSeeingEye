# Commercial source replacement candidates

Reviewed on 9 October 2026 for KAN-194. These are candidates with identified primary
terms, not approvals or changes already applied. Check the exact product, credit,
service limits, retained evidence and export behaviour before substituting it.
No source provides an automatic replacement for every field or coverage area.

| Restricted or unresolved use | Candidate and primary terms | Commercial basis and remaining work |
| --- | --- | --- |
| EOX 2024 initial satellite basemap | [OpenFreeMap](https://openfreemap.org/) and [service terms](https://openfreemap.org/tos/) | Commercial map use is explicitly supported. Use vector styles and retain OpenMapTiles/OSM credit. This loses satellite imagery. Review hosted tile-service terms separately from self-hosted data/code. |
| EOX imagery where a static, low-resolution base is sufficient | [Natural Earth terms](https://www.naturalearthdata.com/about/terms-of-use/) | Public-domain raster/vector data supports commercial use. It is not current high-resolution satellite imagery. Provide useful provenance and avoid implying endorsement. |
| adsb.fi personal/non-commercial feed proposal | [ADSB.lol API data](https://www.adsb.lol/docs/open-data/api/) | API output is ODbL 1.0, with attribution and database share-alike obligations. The contributor CC0 grant is not the API output licence. Seven current aircraft source IDs already use ADSB.lol. Verify service limits and retained/exported derived data. |
| Publisher RSS republication | [GDELT dataset terms](https://www.gdeltproject.org/about.html#termsofuse) | Commercial use of GDELT datasets is permitted with credit. Dataset records can replace some event/link discovery, but do not grant rights to copy linked articles, publisher descriptions or photographs. |
| Licensed baseline boundaries | [geoBoundaries](https://www.geoboundaries.org/index.html) | CC BY 4.0 supports commercial reuse with attribution. Preserve the requested citation, release and source metadata. Boundaries do not replace a conflict front line. |
| DeepState API territory data | [VIINA data terms](https://github.com/zhukovyuri/VIINA) | ODbL provides an alternative for territorial-control data, subject to citation and adapted-database obligations. Methodology, precision and update lag differ; no claim of equivalence or permission to copy linked news. |
| Commercial disaster information | [NWS terms](https://www.weather.gov/disclaimer) | NWS-produced weather information is public domain unless stated otherwise. Retain notices, separate third-party content and avoid suggesting modified data is official. US weather coverage does not replace global disaster sources. |
| Restricted entity enrichment | [GLEIF LEI terms](https://www.gleif.org/en/meta/lei-data-terms-of-use) | LEI data is CC0 and supports commercial corporate-identity enrichment. It does not replace sanctions, politically exposed person or adverse-media coverage. |
| Restricted publication metadata | [OpenAlex data access](https://help.openalex.org/access/overview/) and [Crossref metadata retrieval](https://www.crossref.org/services/metadata-retrieval/) | OpenAlex metadata is CC0; Crossref permits metadata reuse. Service access conditions remain. Neither source gives a blanket right to redistribute publisher full text. |
| Unlicensed camera stills in matching coverage areas | [Madrid camera dataset](https://datos.madrid.es/dataset/202088-0-trafico-camaras/information) and [North East UTMC documentation](https://www.netraveldata.co.uk/?page_id=13) | Madrid identifies CC BY 4.0 snapshots and UTMC documents OGL 3.0 still JPEGs. Limit substitution to the exact covered service, retain credit/update metadata and verify endpoint correspondence. Neither establishes continuous-video or unrelated camera rights. |

Cloudflare Radar and OONI have no verified like-for-like replacement in this review.
Seek permission or omit those features from the affected offering until an
appropriate substitute is reviewed. Open-Meteo offers a paid commercial API route
under its [terms](https://open-meteo.com/en/terms), while its output has
[CC BY 4.0 terms](https://open-meteo.com/en/licence); this is a procurement option,
not permission to use the free endpoint commercially. Do not purchase anything
or enable a paid endpoint without Alex's approval.

For camera footage, a public URL or iframe is not a commercially usable substitute.
Prefer an owner-authorised embed or a link to the owner's site after checking its
terms. Record permission per owner and delivery mode. No bulk permission was
established for the 120 configured media/frame hosts.

## Handoff to KAN-195 and KAN-165

KAN-195 should decide enforcement from the source register and actual deployment
licences, with unknown rights requiring review. A purchase or signed agreement
must identify the operator, product, users, exports, retention and any sublicensing
rights before updating the register. KAN-165 should show source attribution and
licence notices for the data actually displayed, including export-specific credit.
Keep owner permissions private and expose only non-sensitive scope/reference
metadata. Source switching, removal and commercial-mode behaviour are separate work.

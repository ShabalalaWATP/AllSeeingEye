# Public satellite ground stations

The bundled `backend/src/ase/resources/ground_stations.json` contains 25 illustrative
ground-station sites and localities across NASA/JPL, ESA, KSAT, SSC Space, JAXA,
ISRO/ISTRAC and SANSA. Primary references were checked on 8 September 2026.
This is a curated global sample, not a complete inventory or live operational feed.

## Position and interpretation

Every coordinate is approximate and has at most two decimal places. SSC entries
use the operator's published two-decimal site directory. SANSA's published degree
and minute position is rounded. Goldstone and Canberra use public JPL complex/site
coordinates rounded to two decimals. Troll uses KSAT's coarse regional description.

The remaining markers deliberately use the named town, city or island where the
official reference establishes a locality without a readily verifiable coordinate.
They must be displayed as approximate locations with their `note`, not exact
antenna positions. For example, the New Norcia, Cebreros and Malargüe markers are
town/city markers and the notes explain the station's separation from the locality.
Usuda is represented by Saku, and the Madrid complex by Robledo de Chavela.

The dataset does not describe current links, spacecraft assignments, activity,
operational availability or a station's military role. Ground-station presence
does not establish that a satellite is communicating with it. Country values are
ISO 3166-1 alpha-2 geographic codes, including SJ for Svalbard, GF for French
Guiana and AQ for Antarctica; they do not describe operator nationality.

## Primary references and attribution

- [NASA's DSN complexes](https://www.nasa.gov/directorates/somd/space-communications-navigation-program/dsn-complexes/)
  establishes Goldstone, Madrid and Canberra. The [NASA space-flight reference](https://science.nasa.gov/learn/basics-of-space-flight/chapter18-1/)
  identifies Robledo and Tidbinbilla. Coordinate cross-checks use
  [JPL's public terrestrial-reference station table](https://www.jpl.nasa.gov/site/jsgt/jtrf/solutions/jtrf2014/stations/)
  for Goldstone and the [published JPL site report](https://tmo.jpl.nasa.gov/progress_report/42-196/196A.pdf)
  for Canberra.
- [ESA's ESTRACK directory](https://www.esa.int/Enabling_Support/Operations/ESA_Ground_Stations)
  links the six individual station pages retained in the records. This avoids
  treating the retired Perth station in older ESA overviews as current.
- [SSC Space's station directory](https://sscspace.com/services/satellite-ground-stations/our-stations/)
  supplies eight station names and approximate public site coordinates. The
  source's Irbene coordinate appeared inconsistent with its stated locality and
  was not included without further verification.
- [KSAT's public overview](https://www.ksat.no/cosa/about-us/),
  [Troll anniversary article](https://www.ksat.no/news/news-archive/2016/troll-station-10-years/)
  and [Punta Arenas opening](https://www.ksat.no/news/news-archive/2019/Royal-opening-of-the-Punta-Arenas-Ground-Station/)
  establish the three KSAT entries. SvalSat uses a Longyearbyen locality marker.
- [JAXA's Usuda centre page](https://global.jaxa.jp/about/centers/udsc/index.html)
  establishes the facility and Saku locality. The mountain facility is not placed
  at the city marker with any claim of precision.
- [ISRO's ISTRAC overview](https://www.isro.gov.in/ISTRAC.html) names the public
  network localities represented by Bengaluru, Port Blair and Biak. These are city
  markers. No inference is made about individual antennas or present activity.
- [SANSA Space Operations](https://www.sansa.org.za/products-and-services/space-operations/)
  publishes Hartebeesthoek's general location and coordinates.

Only factual names, operator names, general locations and source links are
retained. Notes are original application text. No source images, logos, maps or
article bodies are redistributed. Attribution remains attached to each record.
Adding providers or more precise positions requires checking their primary
references, updating these notes and retaining honest location precision.

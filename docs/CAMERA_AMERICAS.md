# Americas public camera sources

Implementation: `backend/src/ase/adapters/geo/camera_americas*.py`.
Reference: [OSIRIS camera adapters](https://github.com/simplifaisoul/osiris/tree/master/src/app/api/cctv), inspected at commit `fac8d1b` on 8 September 2026.

The adapters reproduce the public provider catalogue formats, not OSIRIS's proxy,
stealth fetching, access-control workarounds or fabricated fallback locations.
All requests use the application's DNS-pinned, size-bounded HTTP client. Catalogues
are requested from fixed URLs; media is restricted to exact provider-specific HTTPS
hosts. A camera record cannot choose an arbitrary remote proxy target.

| Provider | Catalogue and capability |
| --- | --- |
| Washington WSDOT | Referenced public JSON endpoint currently returns 404. Registered as unavailable. |
| California Caltrans | Official ArcGIS CCTV FeatureServer, paginated by OBJECTID. Snapshots and published HLS URLs. |
| Ottawa | Official municipal camera list and snapshots. |
| Quebec 511 | Official transport WFS catalogue, provider MP4 camera clips and original player links. |
| Ontario 511 | Official camera REST catalogue, enabled snapshot views only. |
| Alberta 511 | Referenced REST endpoint returns 400 without credentials. Registered as unavailable. |
| Montreal | Referenced municipal JSON URL redirects to a Quebec player page, not a JSON catalogue. Registered as unavailable; Quebec source covers the wider area. |
| Toronto | Official municipal GeoJSON and snapshots. |
| British Columbia | DriveBC public webcam API at its canonical www host, snapshots. |
| Illinois | Travel Midwest returns status messages without camera records. Registered as unavailable. |
| Oregon | TripCheck public feature inventory, snapshots, including URL-encoded filename spaces. |
| Michigan | MiDrive public camera list, snapshots. HTML strings are parsed for coordinates and image URLs and are never rendered. |
| Indiana | TrafficWise public GraphQL map query, active camera posters and HLS playlists. GET was verified; no authentication or session negotiation. Closed camera icons are excluded. |
| Utah | UDOT public IBI catalogue, snapshots. |
| Nevada | NDOT public IBI catalogue, snapshots and ungated HLS. |
| Louisiana | LADOTD public IBI catalogue, snapshots and ungated HLS. |
| Florida | FDOT public IBI catalogue, snapshots. Streams explicitly marked authentication-required are not offered. |
| Georgia | GDOT public IBI catalogue, snapshots. Authentication-required streams are not offered. |
| North Carolina | NCDOT public IBI catalogue at canonical www host, snapshots. Authentication-required streams are not offered. |
| Arizona | ADOT public IBI catalogue, snapshots. |
| Published US webcams | Two Butler County public webcams, CincyVision YouTube public livestream and Cincinnati-Covington EarthCam. Third-party player pages remain external links; curated positions are marked approximate. |

The three curated Toronto OSIRIS fallback points are deliberately excluded: they
point to an entire JSON catalogue rather than actual cameras. Official Toronto and
Ontario indexes supply real camera coordinates instead. Video availability is a
provider capability, not a guarantee that each encoder is currently producing live
frames. Quebec MP4 responses can be short clips rather than continuous broadcasts.
Indiana streams can show a provider pre-roll while the encoder warms up.

IBI pagination is bounded at 50 pages of 100 records and four concurrent requests.
Sources larger than 5,000 records are intentionally capped, not represented as
exhaustive. Any missing page fails the refresh so the service can retain previous
cached data. One transient HTTP 5xx retry is allowed; access denials are not retried.
Caltrans follows at most 5,000 records and fails explicitly if additional pages
remain. Other catalogues are bounded to 5,000 input rows. No feed depends on a paid
API key, and missing/retired feeds have no fake camera fallback.

## Verification

Offline parser, media origin, coordinate, disabled/authentication flag, malformed
payload, deduplication and pagination regression tests run without network.
The 8 September live probes used the production pinned client for every dynamic
source. Original endpoint failures are recorded above and exposed as unavailable.
Counts are observations at probe time, not a guaranteed ongoing inventory.

## OSIRIS attribution and licence

Provider endpoint and format research, including IBI WKT parsing and Indiana
playlist construction, derives from the MIT-licensed OSIRIS repository. The
provider imagery itself remains subject to each provider's terms; the software
licence does not grant rights to redistribute third-party camera imagery.

MIT License

Copyright (c) 2026 simplifaisoul

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Bounded live probe results, 8 September 2026

- Caltrans: 2,836 cameras, 1,904 published HLS URLs. Sample playlist HTTP 200 and valid HLS.
- Nevada: 640 cameras, 625 published HLS URLs. Sample playlist HTTP 200 and valid HLS.
- Louisiana: 336 cameras, 335 published HLS URLs. Sample playlist HTTP 200 and valid HLS.
- Quebec: 678 catalogue entries with provider MP4 URLs. Sample playback request returned 403 in this environment. These are not verified playable here; original provider links remain available.
- Indiana: 155 active camera URLs and 592 closed-camera placeholders, which were excluded. Sample HLS request returned 503. The catalogue is available, but playback was not verified in this run.
- Snapshot catalogues: Ottawa 428, Ontario 944, Toronto 336, DriveBC 1,062, Oregon 1,144, Michigan 714, Utah 2,075, Florida 4,953, Georgia 4,043, North Carolina 1,139, Arizona 644.
- WSDOT, Alberta, Montreal and Illinois failed as documented above. Four curated US public camera links were registered; their current streams were not individually verified.

A successful catalogue response establishes the camera index, not the freshness or
availability of every image. Verification sampled streams without recording footage.

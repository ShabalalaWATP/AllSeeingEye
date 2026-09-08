# Asia, Oceania and world cameras

Implemented from the public [OSIRIS CCTV adapters](https://github.com/simplifaisoul/osiris/tree/master/src/app/api/cctv), reference revision `fac8d1b` inspected on 8 September 2026. The static catalogue is a derived data file, `camera_world_catalogue.json`, not an executable copy of upstream code. Its 666 records retain upstream identifiers, names, coordinates and operator links.

| OSIRIS source | App integration | Observed result on 8 September 2026 |
|---|---|---|
| Australia | Fixed Transport for NSW JSON index, HTTPS snapshots | Catalogue HTTP 200, 217 cameras |
| New Zealand | NZTA XML index, offline/maintenance rows excluded | Catalogue HTTP 200, 252 accepted cameras |
| Taiwan | Highway Bureau JSON index plus 4 curated YouTube entries | THB request failed TLS connection locally; no insecure retry or invented fallback |
| Singapore (`route.ts` Asia) | Official data.gov.sg LTA traffic images | Catalogue HTTP 200, 8 cameras in this response |
| Japan | 51 public curated records: YouTube and MLIT river snapshots | Example MLIT JPEG HTTP 200, 29,030 bytes; whole catalogue playback not verified |
| Thailand | 6 public YouTube streams | Bangkok Soi 11 `UemFRPrl1hk` oEmbed returned HTTP 200 and The Real Samui Webcam attribution |
| Middle East (`route.ts`) | 4 public YouTube entries | Catalogue imported; individual current playback unverified |
| `asia-live` and generated Skyline data | 260 public operator pages | External pages only |
| `world-live` and generated Skyline data | 162 Latin America, 27 Africa, 152 Europe pages | External pages only |
| OpenCCTV East, Southeast, West/Central Asia | Public marker index and read-only 50-ID batches; respective caps 1,200, 800, 600 | Marker index HTTP 200, 7,147,890 bytes; two-record batch from each region returned valid records |

The existing Hong Kong integration remains separate. Region names mirror OSIRIS coverage; they are not assertions that every camera in those countries is included. Dynamic indexes are capped at 5,000 rows. OpenCCTV uses deterministic spatial sampling like OSIRIS and a maximum of four simultaneous batch requests per source. A failed batch fails that source rather than silently reporting complete coverage.

## Video and coordinate semantics

YouTube entries use the public embed player on explicit user request. A catalogue record with a stream URL indicates its playback method, not confirmation that the owner is broadcasting now. Streams can end, become private or refuse embedding. An oEmbed response confirms metadata and embed capability, not continuous current video playback. Root browser verification is recorded separately.

Skyline's `liveNNNN.jpg` URLs are catalogue posters, often static, and upstream code uses a proxy to work around hotlink restrictions. This implementation deliberately keeps all those records as public operator links. It does not pretend those posters are live images, extract protected video tokens or bypass provider restrictions.

All curated and OpenCCTV positions are labelled approximate. OSIRIS Skyline positions are geocoded locality locations, sometimes shared across several cameras, rather than surveyed lens positions. Multi-camera streams cover more than their single marker. Provider coordinates and locations may contain errors; consult the linked operator before analytical use.

OpenCCTV aggregates third-party camera records. It is not sufficient evidence that an arbitrary feed host is authorised or appropriate to access. Records from unreviewed hosts expose only the public OpenCCTV directory page; they do not link directly to or proxy arbitrary cameras. Approved public HTTPS snapshot hosts and YouTube embeds can display media. No private IP cameras, login bypass, stealth fetching, arbitrary URL proxy or insecure TLS retry is implemented.

Official requests use the application's DNS-pinned, bounded HTTP client and fixed source URLs with redirects disabled. Media is constrained to exact HTTPS origins; credentials, explicit ports, non-ASCII/control characters, fragments and unapproved hosts are rejected. The parent camera service provides caching, request deadlines and source status.

## Adaptation licence

Catalogue data and source mappings adapted from OSIRIS by simplifaisoul. This licence applies to the copied software/catalogue portion, not to third-party camera imagery. Provider terms still apply.

```text
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
```

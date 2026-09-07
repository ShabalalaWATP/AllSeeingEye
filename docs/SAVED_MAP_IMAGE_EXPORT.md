# Saved-map image export

Implementation and acceptance record, 7 September 2026. This is an E5/E9 milestone
within the full research expansion plan, not a replacement for its release gates.

## Exact revision and rendering

Export resolves one immutable saved-map revision and its exact frozen report
version. A dedicated 1,200 by 800 pixel renderer uses that revision's camera,
projection, filters, selection and versioned geometry transforms. Unsaved edits
and temporary catalogue footprints never enter this renderer. Both globe and
Mercator use the existing MapLibre/deck.gl pipeline. Capturing only the basemap
canvas is incorrect because evidence and annotation layers occupy a second canvas.

The engine must wait for complete basemap loading and the corresponding deck
render, then compose both canvases. Capture has bounded elapsed time, dimensions
and bytes, and fails on rendering errors, context loss, mutation, missing tiles,
aborted authority or origin-clean/readback failure. Only dedicated export engines
retain drawing buffers; normal dashboard rendering keeps its current behaviour.

Saved views do not retain provider tile bytes or the original viewport size.
The exported image therefore reproduces saved state at the recorded output size
using provider content fetched at export time. It is not proof of historical
cartography or identical pixels from the moment the view was saved. The export
records this limitation, the output dimensions and renderer policy.

## Privacy and source-use controls

The default export omits saved private overlays, AOI and measurement annotations.
An operator can explicitly include them with a bounded permitted-use declaration.
The exported state and image must apply the same choice. Frozen research evidence
markers and geometry remain included according to the saved filters; omitting
annotations does not remove all potentially sensitive locations from a report.

The image is rendered by the client. Server checks establish current access,
revision integrity and valid bounded PNG bytes, not pixel fidelity, authenticity
or independent verification of redaction. The UI and package describe that
boundary explicitly. No sharing, public publication or durable image retention
happens automatically.

All basemaps keep their identity; export must not silently replace a restricted
style. The initial source-use policy is:

| Basemap | Export condition |
| --- | --- |
| Dark, streets, light | Preserve OpenFreeMap, OpenMapTiles and OpenStreetMap credits and the full OSM copyright URL |
| Satellite, hybrid | Declare non-commercial use under the stated EOX terms, or possession of a suitable licence; preserve EOX/2024 Copernicus credit and applicable links |
| OS styles | Declare possession of a suitable export licence; preserve Crown copyright credit |

Declarations record operator assertions rather than legal verification. Included
overlay attributions and dataset dates remain visible in the export metadata.
Attribution is burned into the delivered image because interactive HTML credit
controls are outside the captured canvases.

Primary source references checked on 7 September 2026:

- [OpenFreeMap attribution requirements](https://openfreemap.org/#attribution).
- [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright).
- [EOX licence summary](https://cloudless.eox.at/documentation/license).

## Delivery contract

`POST /api/map/views/{view_id}/revisions/{revision_id}/image-package` receives
bounded JSON containing `png_base64`, `include_annotations`, `use_basis` and
`permitted_use`. Use bases are `standard`, `noncommercial` and `licensed`.
Current map access and a two-slot process export allowance precede body intake.
The JSON envelope is limited to 12 MiB, original PNG bytes to 8 MiB, each image
dimension to 2,048 and pixel count to four million. Only non-animated, complete
PNG images are accepted. Existing Pillow support validates and re-encodes the
image in a bounded worker, discarding untrusted image metadata.

The ZIP contains a generated image name, revision/export-state metadata,
attribution and limitations, and a versioned integrity manifest. All uncompressed
members together are limited to 16 MiB. There are no arbitrary filesystem paths,
backend URL fetches or new database records. Client image bytes cannot override
server-resolved revision IDs or content hashes.

Admission remains held through decoding, packaging and final checks. Cancellation
cannot release a still-running worker's allowance. The service then re-resolves
the exact revision using fresh session, scope and integrity checks and compares
the immutable snapshot before delivery. Client account/workspace/version changes
abort rendering and prevent a stale download.

## Required acceptance

- Real globe and flat-map captures contain aligned basemap and evidence layers,
  rather than a blank buffer or basemap-only image.
- Capturing an old revision ignores newer revisions and current editor drafts.
- Annotation exclusion removes its coordinates and attributes from metadata and
  its layers from the client image; frozen evidence remains explicitly separate.
- Missing tiles, context loss, redraw races, timeout and cancellation fail clearly.
- Unauthorised requests do not consume image bodies. Wrong scope/version,
  revocation and deletion before final release prevent delivery.
- Malformed, animated, truncated, oversized and excessive-pixel PNGs are rejected;
  packages cannot exceed their aggregate bound or inject image metadata/paths.
- Required attribution, source-use declarations, polar/geometry omissions and
  current-basemap limitations remain in the delivered artefact.
- Static checks, behaviour tests and actual browser/GPU capture acceptance are
  separate evidence. Unit mocks do not establish rendered-image correctness.

## Local implementation and verification

The API, bounded PNG sanitiser, source credits, ZIP manifest, fixed-size preview
and two-canvas capture pipeline are implemented. Visible overlay credits use
packaged Latin/Cyrillic/CJK glyphs; unsupported characters are represented by
explicit Unicode code points and retained intact in metadata. Footer dimensions
are included in the 2,048-pixel/four-million-pixel output bound.

Backend checks passed 74 saved-map and image cases plus 16 final renderer cases
(82 distinct cases). Mypy (564 source files), Ruff and two architecture contracts
passed. Frontend checks passed 30 integration cases and 29 capture/engine cases;
13 final integration regressions, TypeScript and scoped ESLint passed. Caddy
configuration validation passed. Logs are under `data/map-image-*`.

These are local tests, including mocked canvas behaviour. Real globe/flat-map GPU
acceptance remains open: the browser security check could not verify the
admin-enforced policy and denied tab access. No workaround was attempted. No
operator migration, provider account, public publication or deployment occurred.

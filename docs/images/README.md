# App screenshots

These images show the current application UI at a 1600 × 1000 desktop viewport.
They were captured from a local Vite session using Playwright, with API responses
supplied by documentation fixtures. They contain no real account, API key, private
research or production administration data.

| Image | What it shows |
| --- | --- |
| [globe.png](globe.png) | Globe navigation, layer controls and illustrative observations |
| [research.png](research.png) | Question entry and research depth controls, before submitting a request |

The account name and observations are illustrative. The UI itself is not a design
mock-up. No AI request was made for these captures. The globe uses the application's
normal map imagery; its provider attribution is visible in the screenshot and
must be retained when reusing it.

To refresh the images, run the current frontend locally, use an isolated test
account or fixture session, and capture the relevant view at the same size.
Store working captures under `output/playwright/`, inspect them for private data,
then copy the approved images here. Keep captions and alternative text aligned
with what the images actually show.

## Product page assets

The public product page's illustrative images and its Open Graph image are made by
a repeatable Playwright capture, not by hand. It drives the development-only
preview pages (`/dev/*-preview` and `/brand/capture`) with their synthetic
fixtures. Every request to another origin is aborted and every API call is
answered locally, so no backend, account, map tile or third-party image is used.
A preview that still tries to reach the network is skipped and reported, never
written.

From `frontend/`:

```
pnpm test:browser:install       # once, or set CAPTURE_BROWSER_CHANNEL=chrome (or msedge)
pnpm capture:assets             # starts Vite on 127.0.0.1:5183, captures, stops it
```

Port 5183 must be free. The run writes:

| Output | What it is |
| --- | --- |
| `frontend/public/product/<id>.webp` and `.png` | Each capture as WebP (encoded in the browser with `canvas.toBlob`) with a PNG fallback |
| `frontend/public/brand/og-enterprise.png` | 1200 × 630 Open Graph image: the real Evil Eye from `/brand/capture` beside the page title and description |
| `frontend/src/features/product/content/assets.ts` | Generated typed manifest with each image's width, height, paths and alternative text |
| `output/playwright/capture-report.json` | What was captured, what was skipped and why, and the assets that cannot be captured yet |

Each run deletes the previous `public/product` images first, so always run the
whole capture rather than a filtered subset. The targets and the list of assets
that cannot be captured live in `frontend/browser/captureTargets.ts`; the capture
itself is `frontend/browser/assets.capture.ts`.

Captures use a still story (reduced motion), a 1280 × 800 desktop or 390 × 844
phone viewport and a device pixel ratio of 1. Development-only preview controls
are hidden before capture. Every image must be captioned "Illustrative" wherever
it is shown, and reviewed for data and licence cleanliness before use. Motion
loops are not produced: no video encoder is installed and Playwright records only
untrimmed VP8 WebM.

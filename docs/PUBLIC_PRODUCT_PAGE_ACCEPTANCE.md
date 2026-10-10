# Public product page acceptance

KAN-172 covers the opt-in `/enterprise` route. The existing chapters remain in
place. The cost estimator remains hidden pending approved figures. This record
separates implemented controls from browser and deployment evidence.

## Current mobile target and result, 10 October 2026

Alex explicitly requested a mobile performance target of 90. Jira KAN-172 now
records that target, with accessibility at least 95 and SEO at least 90. The
earlier 95-performance figures below remain historical evidence.

The final build scores **90/97/100 in three consecutive mobile runs** and
**100/97/100 on desktop**. Tests use the complete `/enterprise` story with normal
motion and both runtime flags enabled. Lighthouse 13.5.0, Chrome 155.0.8059.39,
the default mobile profile (412 by 823, DPR 1.75, 150 ms RTT, 1,638.4 Kbps,
four-times CPU slowdown) and fresh browser profiles are unchanged. No builds,
tests or other browser checks ran during measurement.

The production comparison uses Caddy 2.11.4, HTTPS/HTTP2, the repository's full
CSP and the existing Brotli/gzip precompression script. A synthetic local API
returns public flags and accepts fixture enquiries without storing or forwarding
their contents. The disposable local certificate uses a process-only exception.
The old and new builds use the same server configuration, compression and URL.

| Build/run | Performance/accessibility/SEO | FCP | LCP | Blocking time | Layout shift |
| --- | --- | --- | --- | --- | --- |
| Clean `f9393e3e` baseline | 87/97/100 | 2.112 s | 3.837 s | 9 ms | 0 |
| Final mobile 1 | 90/97/100 | 2.038 s | 3.313 s | 18 ms | 0 |
| Final mobile 2 | 90/97/100 | 2.038 s | 3.388 s | 24 ms | 0 |
| Final mobile 3 | 90/97/100 | 2.041 s | 3.316 s | 16 ms | 0 |
| Final desktop | 100/97/100 | 0.452 s | 0.652 s | 0 ms | 0.00002 |

The separate HTTP/gzip fixture previously used for the 85 baseline now scores
87/97/100 (FCP 2.290 s, LCP 3.680 s, blocking time 16 ms, no layout shift).
Its transport differs from production Caddy, so 85 to 90 is not presented as a
like-for-like code comparison. A score of 90 also does not imply a sub-2.5-second
mobile LCP; that remains a possible future improvement.

Changes remove account bootstrap, broad validation and private navigation metadata
from the public startup dependency chain. Public schemas use the existing Zod Mini
package entry with unchanged validation, and the shared API client accepts both
Zod variants through their common core. Supported public eye workers no longer
download the synchronous graphics engine; fallback loads it on demand with
cleanup and failure guards. Four dependency-free shared modules form one chunk,
saving repeated response headers without changing CSP. The manifest uses existing
WebP captures with PNG fallback. The hero's opening and still states remain visible.

Final gzip JavaScript totals are 129,212 initial bytes, 847,574 additional globe
bytes and 62,200 additional product bytes. All existing budgets are unchanged;
the product budget includes the worker and dynamically loaded fallback engine.
The moved vendored component retains its existing tool exclusions; the new
compatibility wrappers remain checked. No dependency, lockfile or licence changed.

Validation: 196 affected brand/product/session/API tests pass; a separate group of
108 title/focus/auth/public-policy tests passes; 13 bundle/import-boundary tooling
tests pass. Both TypeScript configurations, scoped ESLint/Prettier, source-length
checks, production build and bundle gates pass. Independent architecture and
security reviews found no actionable regressions. Full published-head CI remains
required; these focused runs do not claim a new full-suite coverage percentage.

Native Chrome confirms the full story, no overflow at 320/390/1440 pixels, visible
paused/reduced-motion hero, same-origin-only public requests, one public flags
request without account bootstrap, contact navigation and synthetic enquiry
submission. Disabled/unavailable flags fail closed, disabled enquiries hide the
form, worker startup failure loads a fresh main-thread canvas, and sign-in retains
its title and form. The normal page reported no console errors or warnings before
deliberate fault injection. Configuration and security headers are unchanged.

Raw reports, traces, build logs and browser evidence are retained under the
isolated acceptance worktree's ignored `output/playwright/`, with final report
names `lighthouse-mobile-90-final-{1,2,3}.json`,
`lighthouse-desktop-90-final.json` and `lighthouse-mobile-90-http-final.json`.
API/style/font-preload and off-screen containment experiments did not improve the
result and were removed. This evidence authorises no merge or production deployment.

## Implemented controls

- `/api/site` gates the page. Disabled or unavailable configuration renders the
  not-found view. Only the enabled page installs its title, description, canonical
  URL and Open Graph metadata.
- The canonical URL uses the current origin and `/enterprise`, without query
  strings or fragments. The social image is the existing, same-origin
  `/brand/eye-512.png`: a 512 by 512 PNG capture of the original React Bits Evil Eye,
  292,756 bytes. It adds no image service or third-party request.
- Metadata restores prior head values when the route unmounts. Application,
  account and not-found views use `noindex, follow`. Caddy also sends that header
  for application URLs, including `/` and `/index.html`. It leaves `/enterprise`
  and its static assets crawlable. Existing CSP and cache rules are unchanged.
- Direct public document visits defer account bootstrap until a visitor enters an
  account or application route. This uses the matched route definition, including
  recognised mixed-case, encoded and trailing-slash URLs. Product motion uses
  device-only settings, including
  the operating system's reduced-motion preference. Its pause control performs no
  account reads or writes, including for a signed-in visitor.
- `pnpm lint` checks the product's transitive source imports. Account stores,
  other feature code, authenticated shells and map/media runtimes are prohibited,
  including indirect re-exports and lazy imports.
- The existing CI `pnpm check:bundle` step also measures the `ProductPage` static
  JavaScript closure beyond the common entry. The ceiling is 150 KiB gzip
  (153,600 bytes), with shared route chunks counted once. Initial JavaScript keeps
  its separate 240 KiB ceiling. CSS, fonts and images are not JavaScript budget
  measurements; browser performance must account for their actual loading.

## Prerender recommendation

Recommend a separately reviewed, deployment-aware prerender of this single route
before relying on search indexing or non-JavaScript social previews. The current
SPA installs metadata after the public configuration check. A crawler that does
not execute JavaScript receives the generic application HTML; Open Graph tags
alone do not prove that a social crawler displayed a preview. The disabled route
also remains an HTTP 200 SPA shell with a client-rendered not-found view.

The shared HTML intentionally has no initial `noindex`: Google may skip rendering
a response that already forbids indexing. Google supports rendered canonical tags
and recommends server rendering or prerendering for crawlers without JavaScript.
See [Google's JavaScript SEO guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics).
The image fields follow the [Open Graph protocol](https://ogp.me/).

A future prerender must respect the installation's runtime product-page flag and
approved public content, use that installation's canonical origin, and return a
real not-found response when disabled. Building an always-visible product page
into the shared image would defeat the existing installation gate. No rendering
dependency or crawler service is introduced here. Caddy applies response headers
before URI rewrites under its [documented directive order](https://caddyserver.com/docs/caddyfile/directives#directive-order).

## Verification record

Source checks on the KAN-172 working tree based on `c523a3ad`, using Node
24.19.0, pnpm 11.25.0 and Vite 8.3.1:

| Check | Result |
| --- | --- |
| Frozen dependency install | Passed, lockfile unchanged. |
| Source import boundary | Passed, 64 source files traversed. |
| Node build/import guard tests | 12 passed. |
| Python Caddy/crawler source-policy tests | 12 passed; Caddy runtime validation remains pending. |
| TypeScript application and tooling checks | Passed. |
| Full ESLint and touched-file formatting | Passed. |
| Production build | Passed. |
| Repository file-length check | Passed; pre-existing warnings only. |
| Initial JavaScript gzip | 204,649 bytes, below 245,760. |
| Globe route JavaScript gzip | 810,692 bytes, below 870,400. |
| Product route JavaScript gzip | 20,792 bytes, below 153,600. |

## Integrated browser baseline, 10 October 2026

The production source at `793524d8` includes KAN-165 public documents, KAN-168
enquiries and KAN-182 session handling. The combined DOM/style run passed 104 of
106 cases. The policy heading and duplicate landmark failures were repaired;
all 14 cases in the affected files then passed. Product metadata restoration,
flag combinations, signed-in public motion, route aliases, deferred bootstrap and
enquiry behaviour passed. The rebuilt product closure remained 23,306 bytes gzip;
initial JavaScript was 209,151 bytes and the globe closure 810,682 bytes.

Playwright CLI 0.1.22 and Chrome 155 used a private browser context and compressed
build served at `http://127.0.0.1:5188`, with a same-origin fixture API. The fixture
never forwarded or saved synthetic enquiries. Checks covered desktop 1440 by
1000, phone 390 by 844 and narrow phone 320 by 740 viewports. Product and policy
pages had no horizontal page overflow. Contact navigation, keyboard order,
announced validation, throttling/success focus, draft disposal, reduced motion,
canonical/social metadata and app noindex restoration behaved as expected.
Observed page resources used only the fixture origin. Public visits requested
`/api/site`; there was no third-party page resource. Policy pages retained their
draft noindex state. Local screenshots and reports are in `output/playwright/`.

Lighthouse 13.5.0 used Headless Chrome 155.0.0.0. The mobile run used its unchanged
default profile: 412 by 823 at device scale 1.75, simulated 150 ms RTT, 1,638.4 Kbps
throughput and four-times CPU slowdown. The desktop run used `--preset=desktop`.
Neither measurement forced reduced motion or disabled a scene.

| Profile | Performance | Accessibility | SEO | Result |
| --- | --- | --- | --- | --- |
| Mobile | 60 | 97 | 100 | Performance below the required 95. |
| Desktop | 99 | 97 | 100 | Above the 95/95/90 targets. |

Mobile first contentful paint was 3.2 seconds, largest contentful paint 4.4 seconds
and total blocking time 750 ms. The report attributed 1.44 seconds of script
execution to the common entry, whose static imports include private shells,
assistant UI, account controls and the eye renderer. Its longest observed main
thread task was 385.6 ms. The common stylesheet transferred 21.3 KB and the three
loaded fonts 91.9 KB. The remaining accessibility audit concerns the existing
faded review timeline text. A passing source budget does not establish mobile
performance acceptance; KAN-172 remains open for measured optimisation.

These are local fixture results, not Caddy runtime validation, social-crawler
preview confirmation, legal publication approval or a production release.

## Measured optimisation, 10 October 2026

The original compressed assets and reports are retained separately in
`output/playwright/baseline-dist`. A diagnostic run added Lighthouse's explicit
CPU sampling category and saved its trace. Source-map attribution sampled about
227 ms in eye initialisation, including 130 ms in OGL renderer construction and
63 ms generating deterministic noise. Globe drawing accounted for about 5 ms.
These sampled times are diagnostic observations, not simulated mobile timings.

Each eye now shares the original generator's immutable 256 KiB CPU pixel buffer.
Every eye retains its own WebGL context, texture, shader, motion and cleanup.
Independent source review confirmed that OGL uploads the buffer without changing
or detaching it. The new two-instance regression failed before the change; all
nine graphics-lifetime cases then passed.

After integrating the reviewed KAN-195 source controls and regenerating public
attributions, a compressed default-mobile run scored 75/97/100. First contentful
paint was 3.18 seconds, largest contentful paint 4.22 seconds and total blocking
time 239 ms. Host benchmark indices differed from the original run, so the score
is not an isolated causal comparison. It remains below the required 95.
An earlier repeat accidentally served an uncompressed rebuild; that report is
retained as fixture-error evidence and excluded from the comparison. Subsequent
measurements run the existing deployment precompression step before scoring.

The next candidate keeps route identities and guards intact while loading private
layouts and account forms only when their routes render. A static bundle guard
rejects those private chunks in the common entry. The enabled product starts its
existing, cached public configuration request alongside the lazy route download.
The existing local Inter and JetBrains Mono fonts are preloaded from the same
origin; Vite rewrites their paths to the same assets used by the stylesheet.
Initial JavaScript is now 145,596 bytes gzip and the product closure 44,424 bytes.
The existing budget limits are unchanged.

Public product eyes retain their captured frame until their first actual viewport
intersection, then construct their original renderer. Below-fold eyes therefore
avoid creating an unused WebGL context during startup. The original animation,
shader, pause controls and graphics cleanup remain intact. An unavailable
IntersectionObserver uses the original immediate initialisation path. Tests cover
first visibility, repeated notifications and disposal before a queued notification.
All 87 cases across the product and graphics files pass; the application type
check, production build and all three bundle budgets pass.
The broader auth compatibility run exposed asynchronous test assumptions and a
duplicate responsive navigation landmark; the repaired affected group passed all
19 cases. Independent source review found no guard, bootstrap, error-boundary or
graphics-lifetime regression in this candidate.

An intermediate measurement, before viewport initialisation and Mono font
preloading, scored 78/97/100: first contentful paint 2.59 seconds, largest
contentful paint 4.18 seconds and total blocking time 224 ms. Its largest contentful
paint candidate was the hero's monospace eyebrow after a late font request. The
viewport/font candidate also scored 78/97/100, with first contentful paint at
2.28 seconds, largest contentful paint at 4.08 seconds and total blocking time
290 ms. No score in this record establishes mobile performance of 95.

The retained CPU trace also exposed React's Suspense fallback retry throttle:
297 ms and 277 ms timers map to `scheduleTimeout(completeRootWhenReady)` in the
installed React implementation. The product now uses the existing data router's
route-level lazy loader, retaining its path, loading shell, error boundary and
runtime configuration gate. The focused group passed 48 cases, including pending
and disabled configuration, direct route aliases, contact navigation and safe
recovery from rejected route modules. All 11 policy checks passed; the publication
command still intentionally blocks the incomplete, unapproved legal draft.

The route-loader candidate scored 78/97/100. Observed LCP render delay fell from
591 ms to 298 ms; simulated mobile metrics remained about 2.3 seconds FCP,
4.1 seconds LCP and 300 ms blocking time. A new diagnostic profile attributes
214 ms of sampled startup work to the eye's viewport callback: 161 ms constructing
OGL renderers, 24 ms compiling shaders and 22 ms generating the shared noise.
React scheduler work totalled 49 ms and globe drawing about 5 ms. The first layout
cost about 50 ms. These diagnostic samples are not simulated mobile timings.

The original KAN-172 performance criterion referred to placeholder chapters. This
record measures the complete delivered story and enquiry form with ordinary motion
and every scene present. It does not substitute a stripped page or claim that the
full page meets the earlier 95 threshold. Further substantial gains would require
separate work on native graphics startup or public-entry delivery; the metadata,
import boundary and route-budget checks do not establish that performance result.

## Final integrated verification

The final build at `2d48753c` includes the reviewed KAN-182 session fixtures,
KAN-167 retention repair, KAN-169 route/lifecycle fixtures and KAN-195 map-policy
follow-up. TypeScript, production build and all bundle checks pass: initial
JavaScript 145,644 bytes gzip, product closure 44,422 bytes and globe closure
829,167 bytes. The product import boundary traverses 75 source files. No package
or lockfile change was needed for these optimisations.

The default desktop profile scores 99/97/100, with FCP 0.6 seconds, LCP 0.8 seconds,
blocking time 30 ms and zero layout shift. The most recent ordinary mobile result
for the same public source remains 78/97/100. The final intervening map-control
change does not modify the public page; it was included in the final build and
desktop/browser checks, not presented as a new mobile measurement.

A fresh Chrome 155 browser context verified the final build at 390 and 320 pixels
with the default motion preference. Header and hero eyes render while visible;
the contact eye starts only when its chapter enters view. A direct contact visit
and the sign-in enquiry link focus the contact heading, scroll it below the sticky
header and render its eye while the unseen hero remains uninitialised. Returning
to sign-in removes product metadata and restores noindex. Disabled flags render
not-found without a form or canonical tag. Public resource requests stay on the
same origin, with only `/api/site` requested from the API. There is no horizontal
page overflow and the browser reported no errors or warnings. Final hero/contact
screenshots were inspected. The private browser and loopback fixture server were
closed after verification.

## Exact texture optimisation follow-up

The retained startup trace still attributes about 22 ms to noise generation.
At an exact lattice point, its three neighbouring interpolation weights are zero.
The generator now returns the first corner directly in that case, retaining the
original calculation everywhere else. At texture size 256, five of the eight
octaves use this shortcut for every pixel. Shader code, animation scheduling,
graphics ownership and the resulting pixels are unchanged.

Before editing the generator, SHA256 digests were recorded from its complete
RGBA buffers at sizes 17, 256 and 257 on `2e00cd2e`. All three fingerprint tests
passed before and after the change; the odd sizes exercise fractional paths.
The affected noise and graphics group passed all 19 tests, and scoped lint and
format checks passed. Independent review found no output or lifecycle change.

A local Node 24.19.0 microbenchmark alternated the original and changed generators
over 25 samples each, after six warm-ups. Median generation time for the 256-pixel
texture fell from 8.293 ms to 6.005 ms. This is a warm, isolated CPU measurement,
not a new browser score or evidence of meeting mobile performance 95. The last
measured full-page mobile score remains 78; native graphics startup and public
entry delivery still dominate the remaining gap. A proposed account-code import
change was not made: its estimated 3.8 KiB gzip saving did not justify adding
authentication lifecycle complexity for this measured bottleneck.

Both TypeScript configurations and the production build passed. The unchanged
gzip budgets also passed: initial 145,638 bytes, globe additions 829,249 bytes and
product additions 44,439 bytes. These measurements describe the public delivery
branch, not the independently built combined integration bundle.

## Contact focus and final browser follow-up

A fresh default-mobile Lighthouse run on `81b5c554` at 01:54 UTC on 10 October
again scored 78/97/100: FCP 2.28 seconds, LCP 4.09 seconds, blocking time 304 ms
and zero layout shift. It used Lighthouse 13.5.0, Chrome 155.0.8059.39, the normal
motion preference and the unchanged mobile profile (412 by 823, 150 ms RTT,
1,638.4 Kbps and four-times CPU slowdown). The host benchmark index was 3,987.5.
The complete precompressed page was served from an isolated loopback fixture.
This result does not meet the mobile 95 criterion or isolate the texture change's
effect from host variation.

An additional real-browser check reproduced a contact-focus defect: direct
`#contact` visits focused the heading, but native in-page contact anchors left
focus on the body after fragment navigation. The header and hero contact links
now use the existing router, allowing its contact effect to own scrolling and
focus. Both navigation regressions failed before the repair, while the direct
route control passed. The repaired contact, metadata, product and sign-in group
passes all 16 cases. The metadata lifecycle test now waits for the required route
effects instead of treating a visible heading as proof that metadata has settled;
all previous assertions remain, with additional canonical and social restoration
checks.

Chrome 155 at 390 by 844 verifies heading focus from both contact links, repeated
activation after focusing the Name field, and direct lazy contact loading. The
heading sits below the sticky header, there is no horizontal overflow, sign-in
restores noindex and removes product metadata, and returning restores the product
canonical tag. Resource requests remain on the loopback origin and the console
contains no errors or warnings. The private browser and fixture server were
closed after verification.

Both TypeScript configurations, scoped lint/format, production build and unchanged
bundle budgets pass. The public build contains 145,663 bytes of initial JavaScript
gzip, 829,249 additional globe bytes and 44,436 additional product bytes. Full
published-head CI remains required; this follow-up does not approve publication
or waive the mobile performance target.

## Public graphics worker, 10 October 2026

The public header, hero and contact mark now opt into an OffscreenCanvas worker.
The same extracted OGL engine, shader, noise pixels, uniforms and document-frame
timestamps render the original eye. Other callers remain synchronous. Unsupported
workers and startup failures use a fresh canvas for synchronous fallback. A lost
context stops its surface and retains the original capture without a recovery loop.
Startup and disposal have bounded watchdogs. Each worker accepts one frame or resize
at a time; successive resize requests coalesce to the latest dimensions.

Caddy preloads the existing 512-pixel WebP capture only on exact `/enterprise`
variants, including an optional trailing slash and case variants. The hero requests
high image priority. Runtime flags, publication approval, CSP, shader output and
motion preferences are unchanged. No package or lockfile changed. The worker and
its static dependencies count towards the existing 150 KiB product budget.

All measurements below used Lighthouse 13.5.0 and Chrome 155.0.8059.39, cold page
loads, normal motion and the complete story. The same precompressed HTTP loopback
fixture and unchanged default mobile profile were used: 412 by 823, DPR 1.75,
150 ms RTT, 1,638.4 Kbps and four-times CPU slowdown. No tests or builds ran during
measurement. Scores are performance/accessibility/SEO.

| Build | Scores | FCP | LCP | Blocking time | Layout shift |
| --- | --- | --- | --- | --- | --- |
| `21e9d1d9`, before worker | 77/97/100 | 2.30 s | 4.09 s | 301 ms | 0 |
| Worker, before image preload | 84/97/100 | 2.28 s | 4.06 s | 24 ms | 0 |
| Worker and image preload, final | 85/97/100 | 2.28 s | 3.93 s | 22 ms | 0 |

The final mobile run started at 02:38:54 UTC, with host benchmark index 3,929.
An earlier worker/preload run also scored 85. The default desktop run at 02:39:07
scored 100/97/100, with FCP 0.51 seconds, LCP 0.79 seconds, zero blocking time and
zero layout shift. **The mobile performance requirement of 95 remains unmet.**

Retained traces locate the two approximately 153 ms graphics startup handlers on
dedicated worker threads. The longest main-thread task is approximately 60 ms,
mostly layout. Image discovery moves from approximately 88 ms to 8 ms in the
unthrottled trace, with one download at initial High priority. These trace timings
are distinct from Lighthouse's simulated mobile timings.

A separate local HTTPS Caddy/HTTP2 check scored 86/97/100. It retained the security
headers and used a per-process certificate exception for the disposable local CA;
it is not compared to the HTTP baseline as a code improvement. A further experiment
preloading the route's static dependencies and configuration did not improve that
score and delayed first content on HTTP, so it was removed. No extra HTML shell,
configuration preload, cache-policy change or dependency remains.

Native Chrome verified normal motion, pause/resume, reduced motion, disposal on
navigation, fresh-canvas startup fallback and terminal context loss. Final Caddy
checks confirm the unchanged gated HTML/CSP, exact route preload scope and missing
asset 404s. The final 390-pixel browser check has one hero download, two visible
same-origin workers, only `/api/site` requested, no third-party resource, no overflow
and zero console errors or warnings. Earlier 320-pixel and contact-focus checks
also passed. Worker fault injection used synthetic local state only.

The final affected brand/product group passes 138 cases across 26 files; 12 bundle
and public-boundary tooling tests pass. Both TypeScript configurations, scoped
ESLint/Prettier, the source-length gate, production build and real Caddy web-image
smoke checks pass. New worker/engine module coverage in the focused run is 99.31%
lines and 95.38% branches. Independent architecture and security reviews are clear.
Final gzip totals are 145,648 initial bytes, 829,209 additional globe bytes and
61,645 additional product bytes, all within unchanged budgets. Full published-head
CI remains required. No merge, infrastructure change or deployment is authorised
by this evidence.

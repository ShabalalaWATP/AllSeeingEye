# Public product page acceptance

KAN-172 covers the opt-in `/enterprise` route. The existing chapters remain in
place. The cost estimator remains hidden pending approved figures. This record
separates implemented controls from browser and deployment evidence.

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

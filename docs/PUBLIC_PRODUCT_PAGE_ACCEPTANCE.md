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

DOM tests are prepared for metadata restoration, flag gating, signed-in public
motion and deferred bootstrap. At this source milestone, Vitest and browser
runtime testing remain reserved for KAN-206. No Lighthouse score, browser network
result or successful production deployment is claimed.

Final launch measurement must use the integrated KAN-165 public documents and
KAN-168 enquiry form, a production build and a local fixture API. Record the
revision, browser/Lighthouse versions, mobile profile, scores, measured product
closure, viewport sizes, keyboard/reduced-motion checks and all requested network
origins. Targets from KAN-172 are performance at least 95, accessibility at least
95 and SEO at least 90. These are acceptance targets, not current measurements.

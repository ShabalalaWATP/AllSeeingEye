// Guards what every visitor downloads before the first page renders, including the
// sign-in page, and what the globe (the root route and default landing page) adds on top.
// Run after `pnpm build`: node scripts/check-bundle.js dist
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

// Measured at 187 KB gzip on 25 September 2026; the headroom absorbs ordinary growth.
export const INITIAL_JS_GZIP_BUDGET = 240 * 1024;
// The globe route's own closure: GlobePage, MapLibre, deck.gl and the MapLibre worker,
// excluding what the initial load already fetched. Measured at 772 KiB gzip on 1 October
// 2026; about 10 percent headroom. See docs/01_ARCHITECTURE.md for what it covers.
export const GLOBE_ROUTE_GZIP_BUDGET = 850 * 1024;
// The public /enterprise route's static closure beyond the common entry, including
// shared route dependencies. This is a separate ceiling, not extra initial allowance.
export const PRODUCT_ROUTE_GZIP_BUDGET = 150 * 1024;
const PRODUCT_ROUTE = /^ProductPage-[\w-]+\.js$/;
// Libraries reached only through lazy routes. Loading one up front costs every visitor.
const LAZY_ONLY = /^(?:deck|maplibre|three|hls|GlobePage)-/;
const PRIVATE_ROUTES =
  /^(?:AppShell|AdminShell|AuthLayout|LoginPage|ForgotPasswordPage|RequestAccountPage|SetPasswordPage|AdminSessionGate|guards)-/;
// Fixture pages mounted only by the development server.
const DEV_ONLY = /(?:PreviewPage|BrandCapturePage)-/;
const GLOBE_ROUTE = /^GlobePage-[\w-]+\.js$/;
// The MapLibre worker starts with the globe, so its chunks count towards the route.
const GLOBE_WORKER = /^maplibre-gl-worker-[\w-]+\.js$/;
// Map tool panels load when their tool opens, not with the route.
const GLOBE_TOOL_ONLY = /^(?:MapMeasurementPanel|MapAreaResearchPanel)-/;
// Unhashed MapLibre files would be fetched again beside the hashed shared chunk and could
// pair old main-thread code with a new worker after a deploy.
const FIXED_NAME_MAPLIBRE = /^maplibre-gl-(?:worker|shared)\.mjs$/;
// Rolldown writes static imports with quoted specifiers (import{a}from"./x.js") and
// dynamic ones with template literals (import(`./x.js`)), so only static imports match.
// Revisit this if a toolchain upgrade starts quoting dynamic imports.
const STATIC_IMPORT = /(?:\bimport|\bfrom)\s*["'](\.\/[^"']+\.js)["']/g;

/** Every chunk statically reachable from `entries`, as sorted dist-relative paths. */
function staticClosure(dist, entries) {
  const pending = [...entries];
  const seen = new Set();
  while (pending.length) {
    const chunk = pending.pop();
    if (seen.has(chunk) || !existsSync(path.join(dist, chunk))) continue;
    seen.add(chunk);
    const code = readFileSync(path.join(dist, chunk), 'utf8');
    for (const match of code.matchAll(STATIC_IMPORT)) {
      pending.push(path.posix.join(path.posix.dirname(chunk), match[1]));
    }
  }
  return [...seen].sort();
}

function initialChunks(dist) {
  const html = readFileSync(path.join(dist, 'index.html'), 'utf8');
  const entries = [...html.matchAll(/(?:src|href)="\/(assets\/[^"]+\.js)"/g)].map((m) => m[1]);
  return staticClosure(dist, entries);
}

function gzipTotal(dist, chunks) {
  let total = 0;
  for (const chunk of chunks) {
    total += gzipSync(readFileSync(path.join(dist, chunk)), { level: 9 }).length;
  }
  return total;
}

/** The globe route's chunks beyond the initial load, or null when the build has none. */
function globeRouteChunks(dist, assets, initial) {
  const route = assets.filter((name) => GLOBE_ROUTE.test(name));
  if (route.length === 0) return null;
  const entries = [...route, ...assets.filter((name) => GLOBE_WORKER.test(name))];
  const loaded = new Set(initial);
  return staticClosure(
    dist,
    entries.map((name) => `assets/${name}`),
  ).filter((chunk) => !loaded.has(chunk));
}

/** Returns the initial and lazy-route chunks, their gzip totals and any failures. */
export function inspectBundle(dist) {
  const chunks = initialChunks(dist);
  const assets = readdirSync(path.join(dist, 'assets'));
  const failures = [];
  if (chunks.length === 0) failures.push('index.html references no JavaScript entry.');
  for (const chunk of chunks) {
    const name = path.posix.basename(chunk);
    if (LAZY_ONLY.test(name)) failures.push(`${name} loads on first paint but is lazy-only.`);
    if (PRIVATE_ROUTES.test(name)) failures.push(`${name} loads before a private route needs it.`);
  }
  const gzipBytes = gzipTotal(dist, chunks);
  if (gzipBytes > INITIAL_JS_GZIP_BUDGET) {
    failures.push(
      `Initial JavaScript is ${gzipBytes} bytes gzip, over the ${INITIAL_JS_GZIP_BUDGET} budget.`,
    );
  }
  const routeChunks = globeRouteChunks(dist, assets, chunks);
  const route = { chunks: routeChunks ?? [], gzipBytes: gzipTotal(dist, routeChunks ?? []) };
  const productEntries = assets.filter((name) => PRODUCT_ROUTE.test(name));
  const productChunks = staticClosure(
    dist,
    productEntries.map((name) => `assets/${name}`),
  ).filter((chunk) => !chunks.includes(chunk));
  const product = { chunks: productChunks, gzipBytes: gzipTotal(dist, productChunks) };
  if (productEntries.length === 0)
    failures.push('No ProductPage chunk was found for the product route budget.');
  for (const chunk of productChunks) {
    if (LAZY_ONLY.test(path.posix.basename(chunk)))
      failures.push(
        `${chunk} is in the public product route but belongs to an application runtime.`,
      );
  }
  if (product.gzipBytes > PRODUCT_ROUTE_GZIP_BUDGET)
    failures.push(
      `Product route JavaScript is ${product.gzipBytes} bytes gzip, over the ${PRODUCT_ROUTE_GZIP_BUDGET} budget.`,
    );
  if (routeChunks === null) {
    failures.push('No GlobePage chunk was found for the globe route budget.');
  } else {
    for (const chunk of routeChunks) {
      const name = path.posix.basename(chunk);
      if (GLOBE_TOOL_ONLY.test(name))
        failures.push(`${name} is in the globe route but loads only when its tool opens.`);
    }
    if (route.gzipBytes > GLOBE_ROUTE_GZIP_BUDGET) {
      failures.push(
        `Globe route JavaScript is ${route.gzipBytes} bytes gzip, over the ${GLOBE_ROUTE_GZIP_BUDGET} budget.`,
      );
    }
  }
  for (const name of assets) {
    if (FIXED_NAME_MAPLIBRE.test(name))
      failures.push(`${name} is a fixed-name MapLibre file; ship the hashed chunks only.`);
    if (DEV_ONLY.test(name)) failures.push(`${name} is a development preview in the build.`);
  }
  return { chunks, gzipBytes, route, product, failures };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { chunks, gzipBytes, route, product, failures } = inspectBundle(process.argv[2] ?? 'dist');
  console.log(
    `Initial JavaScript: ${chunks.length} chunks, ${gzipBytes} bytes gzip (budget ${INITIAL_JS_GZIP_BUDGET}).`,
  );
  console.log(
    `Globe route JavaScript: ${route.chunks.length} more chunks, ${route.gzipBytes} bytes gzip (budget ${GLOBE_ROUTE_GZIP_BUDGET}).`,
  );
  console.log(
    `Product route JavaScript: ${product.chunks.length} more chunks, ${product.gzipBytes} bytes gzip (budget ${PRODUCT_ROUTE_GZIP_BUDGET}).`,
  );
  for (const failure of failures) console.error(`check-bundle: ${failure}`);
  process.exit(failures.length ? 1 : 0);
}

// Guards what every visitor downloads before the first page renders, including the
// sign-in page. Run after `pnpm build`: node scripts/check-bundle.js dist
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';

// Measured at 187 KB gzip on 25 September 2026; the headroom absorbs ordinary growth.
export const INITIAL_JS_GZIP_BUDGET = 240 * 1024;
// Libraries reached only through lazy routes. Loading one up front costs every visitor.
const LAZY_ONLY = /^(?:deck|maplibre|three|hls|GlobePage)-/;
// Fixture pages mounted only by the development server.
const DEV_ONLY = /(?:PreviewPage|BrandCapturePage)-/;
// Rolldown writes static imports with quoted specifiers (import{a}from"./x.js") and
// dynamic ones with template literals (import(`./x.js`)), so only static imports match.
// Revisit this if a toolchain upgrade starts quoting dynamic imports.
const STATIC_IMPORT = /(?:\bimport|\bfrom)\s*["'](\.\/[^"']+\.js)["']/g;

function initialChunks(dist) {
  const html = readFileSync(path.join(dist, 'index.html'), 'utf8');
  const pending = [...html.matchAll(/(?:src|href)="\/(assets\/[^"]+\.js)"/g)].map((m) => m[1]);
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

/** Returns the initial chunks, their gzip total and any budget or placement failures. */
export function inspectBundle(dist) {
  const chunks = initialChunks(dist);
  const failures = [];
  if (chunks.length === 0) failures.push('index.html references no JavaScript entry.');
  let gzipBytes = 0;
  for (const chunk of chunks) {
    const name = path.posix.basename(chunk);
    if (LAZY_ONLY.test(name)) failures.push(`${name} loads on first paint but is lazy-only.`);
    gzipBytes += gzipSync(readFileSync(path.join(dist, chunk)), { level: 9 }).length;
  }
  if (gzipBytes > INITIAL_JS_GZIP_BUDGET) {
    failures.push(
      `Initial JavaScript is ${gzipBytes} bytes gzip, over the ${INITIAL_JS_GZIP_BUDGET} budget.`,
    );
  }
  for (const name of readdirSync(path.join(dist, 'assets'))) {
    if (DEV_ONLY.test(name)) failures.push(`${name} is a development preview in the build.`);
  }
  return { chunks, gzipBytes, failures };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { chunks, gzipBytes, failures } = inspectBundle(process.argv[2] ?? 'dist');
  console.log(`Initial JavaScript: ${chunks.length} chunks, ${gzipBytes} bytes gzip.`);
  for (const failure of failures) console.error(`check-bundle: ${failure}`);
  process.exit(failures.length ? 1 : 0);
}

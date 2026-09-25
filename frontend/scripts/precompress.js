// Writes .br and .gz siblings for compressible build output so Caddy can serve them
// with `file_server { precompressed br gzip }` instead of compressing on every request.
// Usage: node scripts/precompress.js dist
import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { brotliCompressSync, constants, gzipSync } from 'node:zlib';

const COMPRESSIBLE = new Set([
  '.css',
  '.html',
  '.js',
  '.json',
  '.mjs',
  '.svg',
  '.txt',
  '.webmanifest',
]);
const MIN_BYTES = 1024;

function* files(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* files(full);
    else if (entry.isFile()) yield full;
  }
}

/** Compresses eligible files under `root` and returns the number of files written. */
export function precompress(root) {
  let written = 0;
  for (const file of files(root)) {
    if (!COMPRESSIBLE.has(path.extname(file)) || statSync(file).size < MIN_BYTES) continue;
    const source = readFileSync(file);
    const variants = [
      ['.br', brotliCompressSync(source, { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } })],
      ['.gz', gzipSync(source, { level: 9 })],
    ];
    for (const [suffix, body] of variants) {
      // A variant that saves nothing only costs disk and a wasted Vary lookup.
      if (body.length >= source.length) continue;
      writeFileSync(file + suffix, body);
      written += 1;
    }
  }
  return written;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const root = process.argv[2];
  if (!root) {
    console.error('Usage: node scripts/precompress.js <dir>');
    process.exit(2);
  }
  console.log(`precompress: wrote ${precompress(root)} files under ${root}`);
}

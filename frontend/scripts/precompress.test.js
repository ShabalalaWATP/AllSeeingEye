import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { brotliDecompressSync, gunzipSync } from 'node:zlib';
import { precompress } from './precompress.js';

test('writes round-tripping brotli and gzip siblings for compressible files only', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'ase-precompress-'));
  try {
    mkdirSync(path.join(root, 'assets'));
    const script = 'export const value = "repeat";\n'.repeat(200);
    writeFileSync(path.join(root, 'assets', 'index-a1.js'), script);
    writeFileSync(path.join(root, 'assets', 'tiny-b2.js'), 'export{}');
    writeFileSync(path.join(root, 'assets', 'font-c3.woff2'), Buffer.alloc(4096, 7));

    assert.equal(precompress(root), 2);

    const base = path.join(root, 'assets', 'index-a1.js');
    assert.equal(brotliDecompressSync(readFileSync(`${base}.br`)).toString(), script);
    assert.equal(gunzipSync(readFileSync(`${base}.gz`)).toString(), script);
    assert.equal(existsSync(path.join(root, 'assets', 'tiny-b2.js.br')), false);
    assert.equal(existsSync(path.join(root, 'assets', 'font-c3.woff2.gz')), false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

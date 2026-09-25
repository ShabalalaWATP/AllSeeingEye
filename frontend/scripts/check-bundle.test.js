import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { INITIAL_JS_GZIP_BUDGET, inspectBundle } from './check-bundle.js';

function build(files) {
  const root = mkdtempSync(path.join(os.tmpdir(), 'ase-bundle-'));
  mkdirSync(path.join(root, 'assets'));
  for (const [name, body] of Object.entries(files)) writeFileSync(path.join(root, name), body);
  return root;
}

const html = (entry, preloads = []) =>
  `<script type="module" src="/assets/${entry}"></script>` +
  preloads.map((name) => `<link rel="modulepreload" href="/assets/${name}">`).join('');

test('follows static imports from the entry and accepts a lean first paint', () => {
  const root = build({
    'index.html': html('index-a1.js', ['react-b2.js']),
    'assets/index-a1.js': 'import{a as b}from"./react-b2.js";import"./auth-c3.js";',
    'assets/react-b2.js': 'export const a=1;',
    'assets/auth-c3.js': 'export{}',
    'assets/deck-d4.js': 'export{}',
    'assets/GlobePage-e5.js': 'import"./deck-d4.js";',
  });
  try {
    const result = inspectBundle(root);
    assert.deepEqual(result.chunks, [
      'assets/auth-c3.js',
      'assets/index-a1.js',
      'assets/react-b2.js',
    ]);
    assert.deepEqual(result.failures, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('reports lazy-only libraries on first paint and development previews', () => {
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'import{l as T}from"./deck-d4.js";',
    'assets/deck-d4.js': 'export const l=1;',
    'assets/UkrainePreviewPage-f6.js': 'export{}',
  });
  try {
    const { failures } = inspectBundle(root);
    assert.equal(failures.length, 2);
    assert.match(failures[0], /deck-d4\.js loads on first paint/);
    assert.match(failures[1], /UkrainePreviewPage-f6\.js is a development preview/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('reports an initial payload over the gzip budget', () => {
  // Random-looking text barely compresses, so its gzip size stays near its length.
  let noise = '';
  for (let i = 0; noise.length < INITIAL_JS_GZIP_BUDGET * 2; i += 1) {
    noise += Math.imul(i, 2654435761).toString(36);
  }
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': `export const x="${noise}";`,
  });
  try {
    const { failures } = inspectBundle(root);
    assert.equal(failures.length, 1);
    assert.match(failures[0], /over the \d+ budget/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

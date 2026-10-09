import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import {
  GLOBE_ROUTE_GZIP_BUDGET,
  INITIAL_JS_GZIP_BUDGET,
  PRODUCT_ROUTE_GZIP_BUDGET,
  inspectBundle,
} from './check-bundle.js';

function build(files) {
  const root = mkdtempSync(path.join(os.tmpdir(), 'ase-bundle-'));
  mkdirSync(path.join(root, 'assets'));
  writeFileSync(path.join(root, 'assets/ProductPage-p1.js'), 'export{}');
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

test('measures product static dependencies once and leaves later scenes out', () => {
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'import"./react-b2.js";',
    'assets/react-b2.js': 'export{}',
    'assets/GlobePage-g1.js': 'export{}',
    'assets/ProductPage-p1.js':
      'import"./react-b2.js";import"./story-s1.js";const scene=()=>import(`./later-l1.js`);',
    'assets/story-s1.js': 'export{}',
    'assets/later-l1.js': 'export{}',
  });
  try {
    const result = inspectBundle(root);
    assert.deepEqual(result.product.chunks, ['assets/ProductPage-p1.js', 'assets/story-s1.js']);
    assert.ok(result.product.gzipBytes > 0);
    assert.deepEqual(result.failures, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('rejects product runtime imports, oversized payloads and a missing product route', () => {
  let noise = '';
  for (let i = 0; noise.length < PRODUCT_ROUTE_GZIP_BUDGET * 2; i += 1)
    noise += Math.imul(i, 2654435761).toString(36);
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'export{}',
    'assets/GlobePage-g1.js': 'export{}',
    'assets/ProductPage-p1.js': `import"./maplibre-m1.js";export const data="${noise}";`,
    'assets/maplibre-m1.js': 'export{}',
  });
  try {
    assert.match(inspectBundle(root).failures.join('\n'), /application runtime/);
    assert.match(inspectBundle(root).failures.join('\n'), /Product route JavaScript.*over/);
    rmSync(path.join(root, 'assets/ProductPage-p1.js'));
    assert.deepEqual(inspectBundle(root).failures, [
      'No ProductPage chunk was found for the product route budget.',
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('reports lazy-only libraries on first paint and development previews', () => {
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'import{l as T}from"./deck-d4.js";',
    'assets/deck-d4.js': 'export const l=1;',
    'assets/GlobePage-e5.js': 'export{}',
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
    'assets/GlobePage-e5.js': 'export{}',
  });
  try {
    const { failures } = inspectBundle(root);
    assert.equal(failures.length, 1);
    assert.match(failures[0], /over the \d+ budget/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('measures the globe route closure on top of the initial chunks', () => {
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'import"./react-b2.js";const g=()=>import(`./GlobePage-e5.js`);',
    'assets/react-b2.js': 'export const a=1;',
    'assets/GlobePage-e5.js':
      'import"./react-b2.js";import{m}from"./maplibre-f6.js";const t=()=>import(`./MapMeasurementPanel-g7.js`);',
    'assets/maplibre-f6.js': 'import"./maplibre-shared-h8.js";export const m=1;',
    'assets/maplibre-shared-h8.js': 'export const s=1;',
    'assets/maplibre-gl-worker-i9.js': 'import"./maplibre-shared-h8.js";',
    'assets/MapMeasurementPanel-g7.js': 'export{}',
  });
  try {
    const result = inspectBundle(root);
    assert.deepEqual(result.route.chunks, [
      'assets/GlobePage-e5.js',
      'assets/maplibre-f6.js',
      'assets/maplibre-gl-worker-i9.js',
      'assets/maplibre-shared-h8.js',
    ]);
    assert.ok(result.route.gzipBytes > 0);
    assert.deepEqual(result.failures, []);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('reports a globe route over its budget, tool panels in its closure and fixed-name workers', () => {
  let noise = '';
  for (let i = 0; noise.length < GLOBE_ROUTE_GZIP_BUDGET * 2; i += 1) {
    noise += Math.imul(i, 2654435761).toString(36);
  }
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'const g=()=>import(`./GlobePage-e5.js`);',
    'assets/GlobePage-e5.js': `import"./MapAreaResearchPanel-g7.js";export const x="${noise}";`,
    'assets/MapAreaResearchPanel-g7.js': 'export{}',
    'assets/maplibre-gl-shared.mjs': 'export{}',
  });
  try {
    const { failures } = inspectBundle(root);
    assert.equal(failures.length, 3);
    assert.match(failures[0], /MapAreaResearchPanel-g7\.js is in the globe route but loads/);
    assert.match(failures[1], /Globe route JavaScript is \d+ bytes gzip, over the \d+ budget/);
    assert.match(failures[2], /maplibre-gl-shared\.mjs is a fixed-name MapLibre file/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test('reports a build without a globe route chunk', () => {
  const root = build({
    'index.html': html('index-a1.js'),
    'assets/index-a1.js': 'export{}',
  });
  try {
    const { failures } = inspectBundle(root);
    assert.deepEqual(failures, ['No GlobePage chunk was found for the globe route budget.']);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

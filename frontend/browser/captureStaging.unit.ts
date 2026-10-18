/**
 * Checks for the capture staging (KAN-179). Run with
 * `node --test browser/captureStaging.unit.ts`; the name keeps it out of the
 * Playwright lanes, which collect `*.spec.ts` and `*.test.ts` from this folder.
 */
import assert from 'node:assert/strict';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { missingCaptures, promoteCaptures, resetStaging } from './captureStaging.ts';

function workspace() {
  const root = mkdtempSync(join(tmpdir(), 'ase-capture-'));
  const staging = join(root, 'staging');
  const product = join(root, 'product');
  mkdirSync(staging);
  mkdirSync(product);
  return { root, staging, product };
}

function write(dir: string, id: string, text: string, types = ['png', 'webp']) {
  for (const type of types) writeFileSync(join(dir, `${id}.${type}`), `${text}.${type}`);
}

void test('lists the targets missing either image, in target order', () => {
  const { root, staging } = workspace();
  try {
    write(staging, 'globe', 'new');
    write(staging, 'economy', 'new', ['png']);
    assert.deepEqual(missingCaptures(staging, ['globe', 'economy', 'sources']), [
      'economy',
      'sources',
    ]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

void test('leaves every committed image in place when a target was not captured', () => {
  const { root, staging, product } = workspace();
  try {
    write(product, 'globe', 'old');
    write(product, 'sources', 'old');
    write(product, 'retired', 'old');
    write(staging, 'globe', 'new');
    assert.throws(
      () => promoteCaptures(staging, product, ['globe', 'sources'], ['retired']),
      /Not every target was captured: sources\./,
    );
    assert.equal(readFileSync(join(product, 'globe.png'), 'utf8'), 'old.png');
    assert.equal(readFileSync(join(product, 'sources.webp'), 'utf8'), 'old.webp');
    assert.ok(existsSync(join(product, 'retired.png')));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

void test('replaces captured images and removes only the retired ids once all succeed', () => {
  const { root, staging, product } = workspace();
  try {
    write(product, 'globe', 'old');
    write(product, 'retired', 'old');
    write(product, 'unlisted', 'old');
    write(staging, 'globe', 'new');
    write(staging, 'sources', 'new');
    promoteCaptures(staging, product, ['globe', 'sources'], ['retired', 'globe']);
    assert.equal(readFileSync(join(product, 'globe.png'), 'utf8'), 'new.png');
    assert.equal(readFileSync(join(product, 'globe.webp'), 'utf8'), 'new.webp');
    assert.equal(readFileSync(join(product, 'sources.png'), 'utf8'), 'new.png');
    assert.ok(!existsSync(join(product, 'retired.png')));
    assert.ok(!existsSync(join(product, 'retired.webp')));
    assert.ok(existsSync(join(product, 'unlisted.webp')));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

void test('starts each run with an empty staging directory', () => {
  const { root, staging } = workspace();
  try {
    write(staging, 'globe', 'stale');
    resetStaging(staging);
    assert.deepEqual(missingCaptures(staging, ['globe']), ['globe']);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

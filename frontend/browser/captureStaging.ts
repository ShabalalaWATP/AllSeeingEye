/**
 * Staging for the product asset capture (KAN-179). A run writes every image into a
 * scratch directory under the ignored output folder; the committed images and the
 * manifest change only once every target has been captured, so a failed or skipped
 * target can never silently drop an asset. Committed images are only ever replaced,
 * and removed only for the ids listed in RETIRED_IDS.
 *
 * Kept free of other local imports so `node --test browser/captureStaging.unit.ts`
 * can run its checks directly.
 */
import { copyFileSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/** Ids no longer captured whose committed images a complete run removes. */
export const RETIRED_IDS: readonly string[] = [];

export const STAGING_DIR = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../output/playwright/capture-staging',
);

const IMAGE_TYPES = ['png', 'webp'] as const;

/** Empties the staging directory at the start of a run. */
export function resetStaging(dir: string): void {
  rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
}

export function stagedImage(dir: string, id: string, type: 'png' | 'webp'): string {
  return resolve(dir, `${id}.${type}`);
}

/** The ids, in order, that lack either image in the staging directory. */
export function missingCaptures(dir: string, ids: readonly string[]): string[] {
  return ids.filter((id) => IMAGE_TYPES.some((type) => !existsSync(stagedImage(dir, id, type))));
}

/**
 * Copies every staged image over its committed copy, then removes the images of
 * retired ids. Refuses, changing nothing, unless every id was captured.
 */
export function promoteCaptures(
  staging: string,
  product: string,
  ids: readonly string[],
  retired: readonly string[] = RETIRED_IDS,
): void {
  const missing = missingCaptures(staging, ids);
  if (missing.length > 0) {
    throw new Error(`Not every target was captured: ${missing.join(', ')}.`);
  }
  mkdirSync(product, { recursive: true });
  for (const id of ids) {
    for (const type of IMAGE_TYPES) {
      copyFileSync(stagedImage(staging, id, type), stagedImage(product, id, type));
    }
  }
  for (const id of retired) {
    if (ids.includes(id)) continue;
    for (const type of IMAGE_TYPES) rmSync(stagedImage(product, id, type), { force: true });
  }
}

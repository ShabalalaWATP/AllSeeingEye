import { mkdirSync, readdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

import { CAPTURE_PATHS } from './capturePaths';

/** Starts each capture run clean, so the manifest lists only this run's images. */
export default function setup(): void {
  mkdirSync(CAPTURE_PATHS.productDir, { recursive: true });
  for (const file of readdirSync(CAPTURE_PATHS.productDir)) {
    if (/\.(png|webp)$/.test(file)) rmSync(resolve(CAPTURE_PATHS.productDir, file));
  }
  mkdirSync(dirname(CAPTURE_PATHS.skippedLog), { recursive: true });
  rmSync(CAPTURE_PATHS.skippedLog, { force: true });
}

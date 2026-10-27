import { mkdirSync, rmSync } from 'node:fs';
import { dirname } from 'node:path';

import { CAPTURE_PATHS } from './capturePaths';
import { resetStaging, STAGING_DIR } from './captureStaging';

/**
 * Starts each capture run with an empty staging directory. The committed images in
 * public/product are left alone until every target has been captured.
 */
export default function setup(): void {
  resetStaging(STAGING_DIR);
  mkdirSync(dirname(CAPTURE_PATHS.skippedLog), { recursive: true });
  rmSync(CAPTURE_PATHS.skippedLog, { force: true });
}

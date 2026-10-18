import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..');

/** Where the asset capture writes; shared by the global setup and the capture spec. */
export const CAPTURE_PATHS = {
  frontend,
  productDir: resolve(frontend, 'public/product'),
  skippedLog: resolve(frontend, '../output/playwright/capture-skipped.jsonl'),
};

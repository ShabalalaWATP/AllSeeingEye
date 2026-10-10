import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

// Keep browser binaries inside this worktree's ignored dependency installation.
// Use the same environment for installation, local runs and CI.
const result = spawnSync(
  process.execPath,
  [fileURLToPath(import.meta.resolve('@playwright/test/cli')), ...process.argv.slice(2)],
  { stdio: 'inherit', env: { ...process.env, PLAYWRIGHT_BROWSERS_PATH: '0' } },
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;

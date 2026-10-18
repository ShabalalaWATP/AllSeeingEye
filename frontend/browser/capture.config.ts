import { defineConfig, devices } from '@playwright/test';

import { CAPTURE_ORIGIN, CAPTURE_PORT } from './captureTargets';

/**
 * Product asset capture (KAN-179), separate from the regression lane. It drives the
 * development-only preview pages, which exist only under the Vite dev server, with
 * their synthetic fixtures. Every request to another origin is aborted and every API
 * call is answered locally, so the dev proxy to a backend is never used.
 *
 * Run with `pnpm capture:assets`. Set CAPTURE_BROWSER_CHANNEL (for example `chrome`
 * or `msedge`) to use an installed browser instead of `pnpm test:browser:install`.
 */
export default defineConfig({
  testDir: '.',
  testMatch: 'assets.capture.ts',
  globalSetup: './capture.setup.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  globalTimeout: 600_000,
  outputDir: '../../output/playwright/capture-results',
  reporter: [['list']],
  use: {
    baseURL: CAPTURE_ORIGIN,
    serviceWorkers: 'block',
    locale: 'en-GB',
    timezoneId: 'UTC',
    // A still story shows every scene in its final state, with no pinning.
    reducedMotion: 'reduce',
    colorScheme: 'dark',
    deviceScaleFactor: 1,
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    launchOptions: {
      // Software WebGL, so the real Evil Eye renders in a headless browser.
      args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
    },
  },
  projects: [
    {
      name: 'capture',
      use: {
        ...devices['Desktop Chrome'],
        ...(process.env.CAPTURE_BROWSER_CHANNEL
          ? { channel: process.env.CAPTURE_BROWSER_CHANNEL }
          : {}),
      },
    },
  ],
  webServer: {
    command: `pnpm exec vite --host 127.0.0.1 --port ${CAPTURE_PORT} --strictPort`,
    cwd: '..',
    url: CAPTURE_ORIGIN,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});

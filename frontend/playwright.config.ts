import { defineConfig, devices } from '@playwright/test';

import { BROWSER_ORIGIN } from './browser/origin';

/** A small production-build regression lane. Every test gets a fresh browser context. */
export default defineConfig({
  testDir: './browser',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  timeout: 30_000,
  globalTimeout: 180_000,
  expect: { timeout: 5_000 },
  outputDir: '../output/playwright/test-results',
  reporter: [
    ['list'],
    ['html', { outputFolder: '../output/playwright/report', open: 'never' }],
    ['json', { outputFile: '../output/playwright/results.json' }],
  ],
  use: {
    baseURL: BROWSER_ORIGIN,
    serviceWorkers: 'block',
    locale: 'en-GB',
    timezoneId: 'UTC',
    reducedMotion: 'reduce',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 5_000,
    navigationTimeout: 10_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'pnpm exec vite preview --config playwright-server.config.ts',
    url: BROWSER_ORIGIN,
    reuseExistingServer: false,
    timeout: 20_000,
  },
});

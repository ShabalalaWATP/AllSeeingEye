import { defineConfig, mergeConfig } from 'vitest/config';

import viteConfig from './vite.config';

// Coverage excludes third-party code (EvilEye), generated types, the entry point,
// test utilities and the WebGL engine, which only gets a mocked smoke test.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      environmentOptions: {
        jsdom: { url: 'http://localhost:3000/' },
      },
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
      restoreMocks: true,
      clearMocks: true,
      // Page tests render lazy routes through MSW round trips; on a busy machine the
      // default 5 s per test is too tight and produced false failures.
      testTimeout: 15_000,
      hookTimeout: 15_000,
      // Every page test boots the shell (rail, top bar, alert count) through MSW; with one
      // worker per core the first renders starve and time out, so half the cores is the cap.
      maxWorkers: '50%',
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html', 'lcov'],
        reportsDirectory: './coverage',
        include: ['src/**/*.{ts,tsx}'],
        exclude: [
          'src/components/brand/EvilEye.tsx',
          'src/lib/api/types.gen.ts',
          'src/main.tsx',
          'src/vite-env.d.ts',
          'src/test/**',
          'src/**/*.test.{ts,tsx}',
          'src/features/globe/engine/MapLibreEngine.ts',
        ],
        thresholds: {
          lines: 90,
          statements: 90,
          functions: 90,
          branches: 90,
        },
      },
    },
  }),
);

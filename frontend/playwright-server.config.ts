import { defineConfig } from 'vite';

import { BROWSER_PORT } from './browser/origin.ts';

// Do not inherit the development proxy: a missed fixture must never reach port 8001.
export default defineConfig({
  preview: { host: '127.0.0.1', port: BROWSER_PORT, strictPort: true, proxy: {} },
});

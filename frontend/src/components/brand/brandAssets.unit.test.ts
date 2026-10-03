import { describe, expect, it } from 'vitest';

import { files, read } from '@/test/themeContrast';

// The 512-pixel capture is about 290 KB; only the Evil Eye's own large fallback may request it.
const LARGE_CAPTURE_OWNER = 'components/brand/EvilEye.tsx';

describe('brand images', () => {
  it('keeps the 512-pixel capture out of small marks', () => {
    const offenders = files
      .filter((file) => file.endsWith('.tsx') && !file.endsWith('.test.tsx'))
      .filter((file) => file !== LARGE_CAPTURE_OWNER && read(file).includes('eye-512.png'));
    expect(offenders).toEqual([]);
  });
});

import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

import { files, read } from '@/test/themeContrast';

// The 512-pixel capture is about 290 KB; only the Evil Eye's own large fallback may request it.
const LARGE_CAPTURE_OWNER = 'components/brand/EvilEyeSurface.tsx';

describe('brand images', () => {
  it('ships the social image as the declared 512-pixel PNG capture', () => {
    const png = readFileSync('public/brand/eye-512.png');
    expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a');
    expect(png.readUInt32BE(16)).toBe(512);
    expect(png.readUInt32BE(20)).toBe(512);
  });
  it('keeps the 512-pixel capture out of small marks', () => {
    const offenders = files
      .filter((file) => file.endsWith('.tsx') && !file.endsWith('.test.tsx'))
      .filter((file) => file !== LARGE_CAPTURE_OWNER && read(file).includes('eye-512.png'));
    expect(offenders).toEqual([]);
  });
});

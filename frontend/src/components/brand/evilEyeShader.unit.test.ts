import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';

import { generateNoiseTexture } from './evilEyeShader';

// Recorded from the original complete RGBA buffers at 2e00cd2e, before the
// lattice optimisation. Odd sizes retain the fractional interpolation paths.
const ORIGINAL_TEXTURES = [
  [17, '5c707677f64d2b53d757f0433b32110f7d570b61550b3a9b3da692eca85f02ab'],
  [256, '9fe7220f5eaf4b56c11d9fadd18e100db37db8af4667f2de65a7e70a13e183ca'],
  [257, 'e53dfeab25d59e9766eb6260278b9cf85ece499a156655bc44e6ac1f415e4dee'],
] as const;

describe('original eye noise texture', () => {
  it.each(ORIGINAL_TEXTURES)('preserves every RGBA byte at size %i', (size, digest) => {
    const bytes = generateNoiseTexture(size);
    expect(bytes).toHaveLength(size * size * 4);
    expect(createHash('sha256').update(bytes).digest('hex')).toBe(digest);
  });
});

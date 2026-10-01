/**
 * theme.css resets `--color-*: initial`, so Tailwind's default palette does not exist and its
 * classes (`text-amber-300`, `bg-zinc-500`) compile to nothing. Status cues must use theme
 * tokens, which the contrast checks below measure in every palette.
 */
import { describe, expect, it } from 'vitest';

import { AA, SURFACES, contrast, files, palettes, read } from '@/test/themeContrast';

const DEFAULT_PALETTE =
  /\b(?:text|bg|border|ring|accent|fill|stroke|outline|decoration|divide|placeholder|caret|from|to|via)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\d{2,3}\b/g;

// Being changed in another open pull request; migrate it once that lands (KAN-62).
const PENDING = new Set(['components/maps/RfTerrainProfileChart.tsx']);

// The accent tokens that status text uses in place of the default palette.
const STATUS_TEXT = ['amber', 'critical', 'good', 'cyan'] as const;

describe('theme palette classes', () => {
  it('never uses a Tailwind default-palette colour class', () => {
    const offenders = files
      .filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file) && !PENDING.has(file))
      .flatMap((file) => [...read(file).matchAll(DEFAULT_PALETTE)].map((m) => `${file} ${m[0]}`));
    expect(offenders).toEqual([]);
  });

  it.each(Object.keys(palettes))('keeps status text tokens at AA in the %s palette', (name) => {
    const palette = palettes[name]!;
    const weak = STATUS_TEXT.flatMap((token) =>
      SURFACES.filter((surface) => contrast(palette[token]!, palette[surface]!) < AA).map(
        (surface) =>
          `${token} on ${surface} ${contrast(palette[token]!, palette[surface]!).toFixed(2)}`,
      ),
    );
    expect(weak).toEqual([]);
  });
});

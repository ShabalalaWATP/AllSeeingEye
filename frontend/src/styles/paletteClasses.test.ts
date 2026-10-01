/**
 * theme.css resets `--color-*: initial`, so Tailwind's default palette does not exist and its
 * classes (`text-amber-300`, `bg-zinc-500`) compile to nothing. Status cues must use theme
 * tokens, which the contrast checks below measure in every palette.
 *
 * Contrast is derived from how the source uses each accent and chart token: used as text, it
 * reaches AA (4.5:1, WCAG 1.4.3); as the focus ring, a focus outline, an opaque border or a
 * chart mark, it reaches the 3:1 non-text minimum (WCAG 1.4.11). Each check runs against the
 * ground and both surfaces in every palette, including the map's own. jsdom cannot lay out or
 * paint, so axe's `color-contrast` rule is off in the page checks (`src/test/axe.ts`); contrast
 * regressions fail here instead.
 */
import { describe, expect, it } from 'vitest';

import { CATEGORY_STYLES } from '@/lib/categories';
import {
  AA,
  NON_TEXT,
  SURFACES,
  contrast,
  files,
  palettes,
  read,
  themeCss,
} from '@/test/themeContrast';

const DEFAULT_PALETTE =
  /\b(?:text|bg|border|ring|accent|fill|stroke|outline|decoration|divide|placeholder|caret|from|to|via)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\d{2,3}\b/g;

// Neutral tokens are covered by the readability guards; the rest are accents and data colours.
const NEUTRAL = new Set([
  'ground',
  'surface',
  'surface-2',
  'line',
  'control-border',
  'text',
  'muted',
  'black',
  'white',
  'transparent',
]);
const ACCENTS = Object.keys(palettes.obsidian!).filter((token) => !NEUTRAL.has(token));

const sourceFiles = files.filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file));
const sources = sourceFiles.map((file) => read(file));
const stylesheets = files.filter((file) => file.endsWith('.css')).map((file) => read(file));

// The utility prefix each stylesheet property corresponds to.
const CSS_PREFIX: Record<string, string> = { color: 'text', border: 'border', outline: 'outline' };

/** The accent tokens the source paints with `prefixes`, opaque uses only unless `alpha`. */
function used(prefixes: readonly string[], alpha = false): Map<string, number> {
  const found = new Map<string, number>();
  const add = (prefix: string, token: string, opacity: number) => {
    if (!prefixes.includes(prefix) || !ACCENTS.includes(token)) return;
    if (opacity < 1 && !alpha) return;
    found.set(token, Math.min(found.get(token) ?? 1, opacity));
  };
  const utility = /\b([a-z]+)-([a-z0-9-]+?)(?:\/(\d+))?(?=[\s"'`}:]|$)/g;
  for (const source of sources) {
    for (const [, prefix, token, percent] of source.matchAll(utility)) {
      add(prefix!, token!, percent === undefined ? 1 : Number(percent) / 100);
    }
  }
  // Stylesheets paint with `var(--color-*)` in `color`, `border*` and `outline*` declarations.
  const declaration = /(?:^|[\s;{])(color|border|outline)(?:-[a-z-]+)?:([^;}]*)/g;
  for (const css of stylesheets) {
    for (const [, property, value] of css.matchAll(declaration)) {
      for (const [, token] of value!.matchAll(/var\(--color-([\w-]+)\)/g)) {
        add(CSS_PREFIX[property!]!, token!, 1);
      }
    }
  }
  return found;
}

/** Every token, surface and palette where `tokens` fall below `minimum`. */
function weak(tokens: Map<string, number>, minimum: number): string[] {
  const failures: string[] = [];
  for (const [name, palette] of Object.entries(palettes)) {
    for (const [token, alpha] of tokens) {
      for (const surface of SURFACES) {
        const ratio = contrast(palette[token]!, palette[surface]!, alpha);
        if (ratio < minimum) {
          const shown = alpha === 1 ? token : `${token}/${Math.round(alpha * 100)}`;
          failures.push(`${name}: ${shown} on ${surface} is ${ratio.toFixed(2)}:1`);
        }
      }
    }
  }
  return failures;
}

describe('theme palette classes', () => {
  it('never uses a Tailwind default-palette colour class', () => {
    const offenders = sourceFiles.flatMap((file, index) =>
      [...sources[index]!.matchAll(DEFAULT_PALETTE)].map((m) => `${file} ${m[0]}`),
    );
    expect(offenders).toEqual([]);
  });
});

describe('accent and chart token contrast', () => {
  it('finds the accents the source actually paints with', () => {
    expect(ACCENTS).toEqual(expect.arrayContaining(['ember', 'cyan', 'chart-1', 'chart-6']));
    expect([...used(['text'], true).keys()]).toEqual(
      expect.arrayContaining(['ember', 'cyan', 'amber', 'good', 'critical']),
    );
    expect([...used(['fill', 'stroke', 'bg']).keys()]).toEqual(
      expect.arrayContaining(['chart-1', 'chart-6']),
    );
  });

  it('keeps accent and chart text at AA in every palette', () => {
    expect(weak(used(['text'], true), AA)).toEqual([]);
  });

  it('keeps the focus ring and focus outlines at 3:1 in every palette', () => {
    const ring = /:focus-visible \{[^}]*outline:[^;]*var\(--color-([\w-]+)\)/.exec(themeCss)?.[1];
    expect(ring).toBe('ember');
    const focus = used(['outline', 'ring']);
    expect(focus.has(ring!)).toBe(true);
    expect(weak(focus, NON_TEXT)).toEqual([]);
  });

  it('keeps opaque accent borders at 3:1 in every palette', () => {
    expect(weak(used(['border']), NON_TEXT)).toEqual([]);
  });

  it('keeps chart marks at 3:1 in every palette', () => {
    const marks = new Map(
      [...used(['fill', 'stroke', 'bg'])].filter(([token]) => token.startsWith('chart-')),
    );
    expect(weak(marks, NON_TEXT)).toEqual([]);
  });

  // Category colours are map data colours: dots and fills on the dark map, never text.
  it('never paints text in a category colour', () => {
    const offenders = sourceFiles.filter((_, index) =>
      /\bcolor:\s*(?:CATEGORY_STYLES\b[^,}]*|\w+)\.css\b/.test(sources[index]!),
    );
    expect(offenders).toEqual([]);
  });

  it('keeps category dots at 3:1 on the map palette', () => {
    const map = palettes['map dashboard']!;
    const weakDots = Object.entries(CATEGORY_STYLES).flatMap(([category, style]) =>
      SURFACES.filter((surface) => contrast(style.css, map[surface]!) < NON_TEXT).map(
        (surface) => `${category} on ${surface}`,
      ),
    );
    expect(weakDots).toEqual([]);
  });

  it('reports a weakened token with its palette, surface and ratio', () => {
    const original = palettes.light!.ember!;
    palettes.light!.ember = '#f0c0a0';
    try {
      expect(weak(new Map([['ember', 1]]), NON_TEXT)).toContain(
        `light: ember on surface is ${contrast('#f0c0a0', palettes.light!.surface!).toFixed(2)}:1`,
      );
    } finally {
      palettes.light!.ember = original;
    }
  });
});

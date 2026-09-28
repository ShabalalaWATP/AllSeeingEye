/**
 * Readability guards measured from the real theme tokens: WCAG 2.x contrast for body and
 * muted text in every theme, no opacity-dimmed muted text below AA, and no informational
 * text under 11px. Decorative exceptions are listed with their reason.
 */
import { describe, expect, it } from 'vitest';

import { AA, SURFACES, contrast, files, palettes, read } from '@/test/themeContrast';

const sources = Object.fromEntries(
  files
    .filter((file) => file.endsWith('.tsx') && !file.endsWith('.test.tsx'))
    .map((file) => [file, read(file)]),
);
const stylesheets = Object.fromEntries(
  files.filter((file) => file.endsWith('.css')).map((file) => [file, read(file)]),
);

// Muted strokes on SVG diagrams are drawing lines, not text.
const DECORATIVE_DIMMED = new Set(['components/maps/RfGroundwaveEngineering.tsx']);
// The sign-in brand footer is aria-hidden decoration; the access footer is not rendered.
const DECORATIVE_SMALL_CSS = new Set(['.auth-brand-footer', '.auth-access-footer']);

describe('readable text', () => {
  it.each(Object.keys(palettes))('keeps body and muted text at AA in the %s palette', (name) => {
    const palette = palettes[name]!;
    for (const surface of SURFACES) {
      expect(contrast(palette.text!, palette[surface]!)).toBeGreaterThanOrEqual(7);
      expect(contrast(palette.muted!, palette[surface]!)).toBeGreaterThanOrEqual(AA);
    }
  });

  it('never dims muted text below AA on the page ground in any theme', () => {
    const failures: string[] = [];
    for (const [file, source] of Object.entries(sources)) {
      if (DECORATIVE_DIMMED.has(file)) continue;
      for (const match of source.matchAll(/text-muted\/(\d+)/g)) {
        const alpha = Number(match[1]) / 100;
        for (const [name, palette] of Object.entries(palettes)) {
          const ratio = contrast(palette.muted!, palette.ground!, alpha);
          if (ratio < AA) failures.push(`${file} ${match[0]} ${name} ${ratio.toFixed(2)}`);
        }
      }
    }
    expect(failures).toEqual([]);
  });

  it('keeps informational text at 11px or more', () => {
    const small: string[] = [];
    for (const [file, source] of Object.entries(sources)) {
      for (const match of source.matchAll(/text-\[(\d+(?:\.\d+)?)px\]/g)) {
        if (Number(match[1]) < 11) small.push(`${file} ${match[0]}`);
      }
    }
    for (const [file, css] of Object.entries(stylesheets)) {
      let selector = '';
      for (const line of css.split('\n')) {
        if (line.includes('{')) selector = line.trim().replace(/\s*\{$/, '');
        const size = /font(?:-size)?:\s*(\d*\.?\d+)(px|rem|em)\b/.exec(line);
        if (!size || DECORATIVE_SMALL_CSS.has(selector)) continue;
        const px = Number(size[1]) * (size[2] === 'px' ? 1 : 16);
        if (px < 10.99) small.push(`${file} ${selector} ${line.trim()}`);
      }
    }
    expect(small).toEqual([]);
  });

  it('measures contrast the way WCAG does over the whole source tree', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(300);
    expect(Object.keys(stylesheets).length).toBeGreaterThan(15);
    expect(Object.keys(palettes)).toHaveLength(9);
    expect(contrast('#ffffff', '#000000')).toBeCloseTo(21, 5);
    expect(contrast('#777777', '#ffffff')).toBeCloseTo(4.48, 2);
    expect(contrast('#ffffff', '#000000', 0.5)).toBeCloseTo(contrast('#808080', '#000000'), 1);
  });
});

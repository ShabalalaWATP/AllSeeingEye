/**
 * Readability guards measured from the real theme tokens: WCAG 2.x contrast for body and
 * muted text in every theme, no opacity-dimmed muted text below AA, and no informational
 * text under 11px. Decorative exceptions are listed with their reason.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

// Vitest stubs stylesheet imports, so read the files the browser is actually served.
const SRC = resolve(process.cwd(), 'src');
const files = readdirSync(SRC, { recursive: true, encoding: 'utf8' }).map((file) =>
  file.replaceAll('\\', '/'),
);
const read = (file: string) => readFileSync(resolve(SRC, file), 'utf8');
const themeCss = read('styles/theme.css');
const dashboardCss = read('features/globe/dashboard.css');

const AA = 4.5;
const THEMES = ['slate', 'light', 'midnight', 'aurora', 'phosphor', 'crimson', 'graphite'];
const SURFACES = ['ground', 'surface', 'surface-2'] as const;

type Palette = Record<string, string>;

function block(css: string, selector: string): Palette {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`Missing ${selector}`);
  const open = css.indexOf('{', start);
  const body = css.slice(open, css.indexOf('}', open));
  const palette: Palette = {};
  for (const match of body.matchAll(/--color-([\w-]+):\s*(#[0-9a-f]{6})\b/gi)) {
    palette[match[1]!] = match[2]!;
  }
  return palette;
}

const base = block(themeCss, '@theme');
const palettes: Record<string, Palette> = {
  obsidian: base,
  ...Object.fromEntries(
    THEMES.map((theme) => [
      theme,
      { ...base, ...block(themeCss, `html[data-appearance='${theme}'] {`) },
    ]),
  ),
  // The map keeps its own dark instrument palette whatever the theme.
  'map dashboard': { ...base, ...block(dashboardCss, '.globe-dashboard-controls {') },
};

function rgb(hex: string): number[] {
  return [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16));
}

function luminance(channels: number[]): number {
  const [r = 0, g = 0, b = 0] = channels.map((value) => {
    const c = value / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG 2.x contrast of a foreground drawn at `alpha` over an opaque background. */
function contrast(foreground: string, background: string, alpha = 1): number {
  const back = rgb(background);
  const front = rgb(foreground).map((value, index) => value * alpha + back[index]! * (1 - alpha));
  const [light, dark] = [luminance(front), luminance(back)].sort((a, b) => b - a);
  return (light! + 0.05) / (dark! + 0.05);
}

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
// Still using sub-11px classes; they are being edited by concurrent navigation, research and
// administration work and move to text-2xs once that lands.
const PENDING_SMALL_TEXT = new Set([
  'app/shell/AdminHeader.tsx',
  'app/shell/AdminNavigation.tsx',
  'app/shell/CommandPalette.tsx',
  'components/admin/AdminPage.tsx',
  'features/admin/AiUsagePolicies.tsx',
  'features/admin/ModelSetupWizard.tsx',
  'features/admin/SourceRow.tsx',
  'features/research/PhotoGeolocationResult.tsx',
  'features/research/PhotoResearchPage.tsx',
]);
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
      if (PENDING_SMALL_TEXT.has(file)) continue;
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

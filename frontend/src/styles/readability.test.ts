/**
 * Readability guards measured from the real theme tokens: WCAG 2.x contrast for body and
 * muted text in every theme, no opacity-dimmed muted text below AA, no informational
 * text under 11px, and form control borders at the 3:1 non-text minimum (WCAG 1.4.11).
 * Decorative exceptions are listed with their reason.
 */
import { describe, expect, it } from 'vitest';

import {
  AA,
  NON_TEXT,
  SURFACES,
  block,
  contrast,
  dashboardCss,
  files,
  palettes,
  read,
} from '@/test/themeContrast';
import type { Palette } from '@/test/themeContrast';

const sources = Object.fromEntries(
  files
    .filter((file) => file.endsWith('.tsx') && !file.endsWith('.test.tsx'))
    .map((file) => [file, read(file)]),
);
const stylesheets = Object.fromEntries(
  files.filter((file) => file.endsWith('.css')).map((file) => [file, read(file)]),
);

const authCss = read('features/auth/auth.css');
const mapToolCss = read('components/maps/mapTool.css');
const mapToolShellCss = read('features/globe/mapToolShell.css');

/** The value of `property` in the first rule whose selector starts with `selector`. */
function declaration(css: string, selector: string, property: string): string {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`Missing ${selector}`);
  const open = css.indexOf('{', start);
  const body = css.slice(open, css.indexOf('}', open));
  const match = new RegExp(`[{;\\s]${property}:\\s*([^;]+);`).exec(body);
  if (!match) throw new Error(`Missing ${property} in ${selector}`);
  return match[1]!.trim();
}

/**
 * The opaque colour a declaration paints: a `var(--color-*)` token from `palette`, or a hex
 * value. A translucent `#rrggbbaa` is flattened over white, the lightest backdrop and so the
 * worst case under a light border on a dark panel.
 */
function paint(value: string, palette: Palette): string {
  const token = /var\(--color-([\w-]+)\)/.exec(value);
  if (token) {
    const hex = palette[token[1]!];
    if (hex === undefined) throw new Error(`Unresolved ${value}`);
    return hex;
  }
  const hex = /#([0-9a-f]{6})([0-9a-f]{2})?\b/i.exec(value);
  if (!hex) throw new Error(`Unresolved ${value}`);
  const alpha = hex[2] === undefined ? 1 : parseInt(hex[2], 16) / 255;
  const channels = [0, 2, 4].map((index) =>
    Math.round(parseInt(hex[1]!.slice(index, index + 2), 16) * alpha + 255 * (1 - alpha)),
  );
  return `#${channels.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
}

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

describe('form control borders', () => {
  it.each(Object.keys(palettes))('reach 3:1 against every surface in the %s palette', (name) => {
    const palette = palettes[name]!;
    expect(palette).toHaveProperty('control-border', expect.stringMatching(/^#[0-9a-f]{6}$/i));
    for (const surface of SURFACES) {
      const ratio = contrast(palette['control-border']!, palette[surface]!);
      expect(ratio, surface).toBeGreaterThanOrEqual(NON_TEXT);
    }
  });

  it('keeps its own control border on the map whatever the theme', () => {
    expect(block(dashboardCss, '.globe-dashboard-controls {')['control-border']).toBeDefined();
  });

  it('draws shared form fields with the control border, not the divider line', () => {
    const field = read('components/ui/Field.tsx');
    expect(field).toContain('border border-control-border');
    expect(field).not.toContain('border-line');
  });

  it.each([
    'features/globe/context/contextPresentation.tsx',
    'features/admin/ModelAssignmentMatrixRow.tsx',
    'components/ui/LinkReveal.tsx',
    'features/globe/ConflictOverviewPanel.tsx',
  ])('draws the inputs in %s with the control border', (file) => {
    expect(read(file)).toContain('border border-control-border');
  });

  it('keeps sign-in input borders at 3:1 against the field and the panel', () => {
    // Sign-in renders outside the account shell, so it always uses the base theme.
    const palette = { ...palettes.obsidian!, ...block(authCss, '.auth-shell {') };
    const input = '.auth-form input,';
    const border = paint(declaration(authCss, input, 'border-color'), palette);
    const backgrounds = [
      paint(declaration(authCss, input, 'background'), palette),
      paint(declaration(authCss, '.auth-access {', 'background'), palette),
    ];
    for (const background of backgrounds) {
      expect(contrast(border, background), background).toBeGreaterThanOrEqual(NON_TEXT);
    }
  });

  it('keeps map tool input borders at 3:1 against the field and the tool panel', () => {
    const failures: string[] = [];
    for (const [name, palette] of Object.entries(palettes)) {
      const border = paint(declaration(mapToolCss, '.map-tool-input {', 'border'), palette);
      const backgrounds = [
        paint(declaration(mapToolCss, '.map-tool-input {', 'background'), palette),
      ];
      // Map tool panels float over the map, so only the dashboard palette sits behind them.
      if (name === 'map dashboard') {
        backgrounds.push(
          paint(declaration(mapToolShellCss, '.map-tool-panel {', 'background'), palette),
        );
      }
      for (const background of backgrounds) {
        const ratio = contrast(border, background);
        if (ratio < NON_TEXT)
          failures.push(`${name} ${border} on ${background} ${ratio.toFixed(2)}`);
      }
    }
    expect(failures).toEqual([]);
  });
});

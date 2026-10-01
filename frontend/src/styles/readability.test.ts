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

// Checkboxes, radios, sliders and file pickers are not outlined text fields.
const NOT_TEXT_CONTROL = /\btype="(?:checkbox|radio|range|file|hidden|color)"/;

/** The opening tag of every `<input>`, `<select>` and `<textarea>` that is a text control. */
function textControls(source: string): string[] {
  return openingTags(source, /<(?:input|select|textarea)\b/g).filter(
    (tag) => !NOT_TEXT_CONTROL.test(tag),
  );
}

/** The opening tag of every element a keyboard user can operate. */
function operableControls(source: string): string[] {
  return openingTags(source, /<(?:input|select|textarea|button|a|summary)\b/g).filter(
    (tag) => !/\btype="hidden"/.test(tag),
  );
}

/** The full opening tag of each JSX element matched by `start`, braces and quotes respected. */
function openingTags(source: string, start: RegExp): string[] {
  const tags: string[] = [];
  for (const match of source.matchAll(start)) {
    let index = match.index + match[0].length;
    let depth = 0;
    let quote = '';
    for (; index < source.length; index += 1) {
      const char = source[index]!;
      if (quote) {
        if (char === quote) quote = '';
      } else if (char === '"' || char === "'" || char === '`') quote = char;
      else if (char === '{') depth += 1;
      else if (char === '}') depth -= 1;
      else if (char === '>' && depth === 0) break;
    }
    tags.push(source.slice(match.index, index + 1));
  }
  return tags;
}

/** A tag's classes, following `className={name}` to a string constant in the same file. */
function classesOf(tag: string, source: string): string {
  const name = /className=\{(\w+)\}/.exec(tag)?.[1];
  if (name === undefined) return tag;
  for (const declaration of source.matchAll(/\bconst\s+(\w+)\s*=\s*([^;]+);/g)) {
    if (declaration[1] === name) return declaration[2]!;
  }
  return '';
}

const authCss = read('features/auth/auth.css');
const mapToolCss = read('components/maps/mapTool.css');
const mapToolShellCss = read('features/globe/mapToolShell.css');

/** The value of `property` in the first rule whose selector starts with `selector`. */
function declaration(css: string, selector: string, property: string): string {
  const start = css.indexOf(selector);
  if (start < 0) throw new Error(`Missing ${selector}`);
  const open = css.indexOf('{', start);
  const body = css.slice(open + 1, css.indexOf('}', open));
  const entry = body
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${property}:`));
  if (!entry) throw new Error(`Missing ${property} in ${selector}`);
  return entry.slice(property.length + 1).trim();
}

/**
 * The opaque colour a declaration paints: a `var(--color-*)` token from `palette`, or a hex
 * value. A translucent `#rrggbbaa` is flattened over white, the lightest backdrop and so the
 * worst case under a light border on a dark panel.
 */
function paint(value: string, palette: Palette): string {
  const token = /var\(--(?:color-)?([\w-]+)\)/.exec(value);
  if (token) {
    // Theme tokens are keyed without `--color-`; a feature's named colours keep `--`.
    const named = value.includes('var(--color-') ? palette[token[1]!] : palette[`--${token[1]!}`];
    if (named === undefined) throw new Error(`Unresolved ${value}`);
    return paint(named, palette);
  }
  const hex = /#([0-9a-f]{6})([0-9a-f]{2})?\b/i.exec(value);
  if (!hex) throw new Error(`Unresolved ${value}`);
  const alpha = hex[2] === undefined ? 1 : parseInt(hex[2], 16) / 255;
  const channels = [0, 2, 4].map((index) =>
    Math.round(parseInt(hex[1]!.slice(index, index + 2), 16) * alpha + 255 * (1 - alpha)),
  );
  return `#${channels.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
}

/** A feature's own named colours (`--auth-field: #101010`) in the rule matching `selector`. */
function namedColours(css: string, selector: string): Palette {
  const start = css.indexOf(selector);
  const body = css.slice(start, css.indexOf('}', start));
  return Object.fromEntries(
    [...body.matchAll(/(--(?!color-)[\w-]+):\s*(#[0-9a-f]{6,8})\b/gi)].map((m) => [m[1]!, m[2]!]),
  );
}

/**
 * Every declaration in the innermost rules of `css`, whitespace collapsed, so a `font`
 * shorthand written across several lines is read as one value.
 */
function declarations(css: string): { selector: string; property: string; value: string }[] {
  const found: { selector: string; property: string; value: string }[] = [];
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const rule of clean.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
    const selector = rule[1]!.trim().replace(/\s+/g, ' ');
    for (const part of rule[2]!.split(';')) {
      const colon = part.indexOf(':');
      if (colon < 0) continue;
      const property = part.slice(0, colon).trim();
      const value = part
        .slice(colon + 1)
        .trim()
        .replace(/\s+/g, ' ');
      found.push({ selector, property, value });
    }
  }
  return found;
}

/** The font size in pixels a `font` or `font-size` declaration sets, or null for none. */
function fontSizePx(property: string, value: string): number | null {
  if (property !== 'font' && property !== 'font-size') return null;
  const size = /(?:^|\s)(\d*\.?\d+)(px|rem|em)\b/.exec(value);
  if (!size) return null;
  return Number(size[1]) * (size[2] === 'px' ? 1 : 16);
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
      for (const { selector, property, value } of declarations(css)) {
        if (DECORATIVE_SMALL_CSS.has(selector)) continue;
        const px = fontSizePx(property, value);
        if (px !== null && px < 10.99) small.push(`${file} ${selector} ${property}: ${value}`);
      }
    }
    expect(small).toEqual([]);
  });

  it('reads font sizes from shorthand that spans several lines', () => {
    const css = '.label {\n  font:\n    9px "JetBrains Mono",\n    monospace;\n}';
    expect(declarations(css)).toEqual([
      { selector: '.label', property: 'font', value: '9px "JetBrains Mono", monospace' },
    ]);
    expect(fontSizePx('font', '600 12px/1.4 Inter, sans-serif')).toBe(12);
    expect(fontSizePx('font', 'inherit')).toBeNull();
    expect(fontSizePx('font-size', '0.5rem')).toBe(8);
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

  it('draws every text control with the control border, not the divider line', () => {
    const offenders = Object.entries(sources).flatMap(([file, source]) =>
      textControls(source)
        .filter((tag) => /\bborder-line\b/.test(classesOf(tag, source)))
        .map((tag) => `${file}: ${tag.slice(0, 60)}`),
    );
    expect(offenders).toEqual([]);
  });

  // `outline-none` sets outline-style: none, which forced-colours modes cannot repaint (WCAG 2.4.7).
  it('never removes the focus outline from a control a keyboard user can operate', () => {
    const offenders = Object.entries(sources).flatMap(([file, source]) =>
      operableControls(source)
        .filter((tag) => /\boutline-none\b/.test(classesOf(tag, source)))
        .map((tag) => `${file}: ${tag.slice(0, 60)}`),
    );
    expect(offenders).toEqual([]);
  });

  it('keeps sign-in input borders at 3:1 against the field and the panel', () => {
    // Sign-in renders outside the account shell, so it always uses the base theme.
    const palette = {
      ...palettes.obsidian!,
      ...block(authCss, '.auth-shell {'),
      ...namedColours(authCss, '.auth-shell {'),
    };
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

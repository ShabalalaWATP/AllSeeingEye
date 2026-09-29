/**
 * Theme palettes read from the stylesheets the browser is served, and WCAG 2.x contrast.
 * Test support only: it reads source files from disk and must never be imported by the app.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Vitest stubs stylesheet imports, so read the files the browser is actually served.
const SRC = resolve(process.cwd(), 'src');
export const files = readdirSync(SRC, { recursive: true, encoding: 'utf8' }).map((file) =>
  file.replaceAll('\\', '/'),
);
export const read = (file: string) => readFileSync(resolve(SRC, file), 'utf8');
export const themeCss = read('styles/theme.css');
export const dashboardCss = read('features/globe/dashboard.css');

export const AA = 4.5;
export const NON_TEXT = 3;
export const THEMES = ['slate', 'light', 'midnight', 'aurora', 'phosphor', 'crimson', 'graphite'];
export const SURFACES = ['ground', 'surface', 'surface-2'] as const;

export type Palette = Record<string, string>;

/** The `--color-*` hex tokens declared in the first rule matching `selector`. */
export function block(css: string, selector: string): Palette {
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

export const base = block(themeCss, '@theme');
/** Obsidian (the base theme), each named theme, and the map's own instrument palette. */
export const palettes: Record<string, Palette> = {
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
export function contrast(foreground: string, background: string, alpha = 1): number {
  const back = rgb(background);
  const front = rgb(foreground).map((value, index) => value * alpha + back[index]! * (1 - alpha));
  const [light, dark] = [luminance(front), luminance(back)].sort((a, b) => b - a);
  return (light! + 0.05) / (dark! + 0.05);
}

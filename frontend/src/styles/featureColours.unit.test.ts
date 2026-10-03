/**
 * Feature colours come from tokens (KAN-99). A stylesheet may write a hex colour only where
 * it names it, in a custom property such as `--paper-ink: #24211c`; every rule then paints
 * with `var(--...)`. Theme-dependent colours use the `--color-*` theme tokens, and the fixed
 * palettes (the paper report, the sign-in screen, the map instruments) are named once at the
 * top of their stylesheet. Components never write a hex colour into a class.
 */
import { describe, expect, it } from 'vitest';

import { files, read } from '@/test/themeContrast';

const HEX = /#[0-9a-f]{3,8}\b/i;

/** Each `property: value` declaration in `css`, comments removed and whitespace collapsed. */
function declarations(css: string): { property: string; value: string }[] {
  const found: { property: string; value: string }[] = [];
  const clean = css.replace(/\/\*[\s\S]*?\*\//g, '');
  for (const rule of clean.matchAll(/\{([^{}]*)\}/g)) {
    for (const part of rule[1]!.split(';')) {
      const colon = part.indexOf(':');
      if (colon < 0) continue;
      found.push({
        property: part.slice(0, colon).trim(),
        value: part
          .slice(colon + 1)
          .trim()
          .replace(/\s+/g, ' '),
      });
    }
  }
  return found;
}

describe('feature colours', () => {
  it('paints stylesheets with named colours only', () => {
    const offenders = files
      .filter((file) => file.endsWith('.css') && file !== 'styles/theme.css')
      .flatMap((file) =>
        declarations(read(file))
          .filter(({ property, value }) => !property.startsWith('--') && HEX.test(value))
          .map(({ property, value }) => `${file} ${property}: ${value}`),
      );
    expect(offenders).toEqual([]);
  });

  it('never writes a hex colour into a component class', () => {
    const offenders = files
      .filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file))
      .flatMap((file) =>
        [...read(file).matchAll(/\b[a-z-]+-\[#[0-9a-f]{3,8}\]/gi)].map((m) => `${file} ${m[0]}`),
      );
    expect(offenders).toEqual([]);
  });

  it('reads declarations the way the stylesheet does', () => {
    expect(declarations('.a {\n  --x: #fff;\n  border:\n    1px solid #000;\n}')).toEqual([
      { property: '--x', value: '#fff' },
      { property: 'border', value: '1px solid #000' },
    ]);
  });
});

/**
 * One type scale (KAN-99). theme.css resets Tailwind's font sizes and declares the scale as
 * `--text-*` tokens, so text scales with the reader's font size and every size has a name.
 * Arbitrary sizes such as `text-[11px]` and undeclared steps such as `text-5xl` are rejected:
 * the first ignores the reader's settings, the second compiles to nothing.
 */
import { describe, expect, it } from 'vitest';

import { files, read, themeCss } from '@/test/themeContrast';

const sources = Object.fromEntries(
  files
    .filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file))
    .map((file) => [file, read(file)]),
);

/** The font-size steps theme.css declares, in the order it declares them. */
function declaredScale(css: string): string[] {
  const theme = css.slice(css.indexOf('@theme {'), css.indexOf('\n}', css.indexOf('@theme {')));
  return [...theme.matchAll(/--text-([\w]+):\s*[\d.]+rem;/g)].map((match) => match[1]!);
}

// Tailwind's `text-` utilities that are not font sizes.
const NOT_A_SIZE =
  /^text-(?:left|right|center|justify|start|end|wrap|nowrap|balance|pretty|clip|ellipsis)$/;

/** Every `text-<step>` font-size utility in `source`, with responsive and state variants removed. */
function sizeUtilities(source: string): string[] {
  return [
    ...source.matchAll(/(?<![\w-])(?:[a-z0-9-]+:)*(text-(?:\d?xs|sm|base|lg|\d?xl))(?![\w/-])/g),
  ]
    .map((match) => match[1]!)
    .filter((utility) => !NOT_A_SIZE.test(utility));
}

// Deferred until the globe refactor (KAN-10) lands, so the two changes do not collide. The
// codemod is `text-[11px]` to `text-2xs`; delete this exemption once the folder is clean.
const PENDING_GLOBE = 'features/globe/';
const ARBITRARY_SIZE = /\btext-\[\d*\.?\d+(?:px|rem|em)\]/g;

describe('type scale', () => {
  it('declares the whole scale as theme tokens after resetting the defaults', () => {
    expect(themeCss).toContain('--text-*: initial;');
    expect(declaredScale(themeCss)).toEqual([
      '2xs',
      'xs',
      'sm',
      'base',
      'lg',
      'xl',
      '2xl',
      '3xl',
      '4xl',
      '6xl',
    ]);
  });

  it('uses only declared steps', () => {
    const scale = new Set(declaredScale(themeCss).map((step) => `text-${step}`));
    const offenders = Object.entries(sources).flatMap(([file, source]) =>
      sizeUtilities(source)
        .filter((utility) => !scale.has(utility))
        .map((utility) => `${file} ${utility}`),
    );
    expect(offenders).toEqual([]);
  });

  it('never sets an arbitrary font size', () => {
    const offenders = Object.entries(sources).flatMap(([file, source]) =>
      file.startsWith(PENDING_GLOBE)
        ? []
        : [...source.matchAll(ARBITRARY_SIZE)].map((match) => `${file} ${match[0]}`),
    );
    expect(offenders).toEqual([]);
  });

  it('keeps the globe exemption only while the globe still needs it', () => {
    const pending = Object.entries(sources).filter(
      ([file, source]) => file.startsWith(PENDING_GLOBE) && source.match(ARBITRARY_SIZE) !== null,
    );
    expect(pending.length, 'The globe is clean: delete PENDING_GLOBE').toBeGreaterThan(0);
  });

  it('finds the sizes it guards', () => {
    expect(sizeUtilities('a sm:text-[11px] md:text-xs text-left text-5xl text-text/80')).toEqual([
      'text-xs',
      'text-5xl',
    ]);
    expect(Object.keys(sources).length).toBeGreaterThan(300);
  });
});

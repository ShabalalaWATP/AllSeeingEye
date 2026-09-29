/**
 * Small informational labels (badges, chips and category labels) must reach AA against every
 * surface in all eight themes. Categorical data colours belong on dots, lines and fills; the
 * label text itself uses a theme text token. Measured from the real theme tokens.
 */
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import { BarList } from '@/components/charts/BarList';
import { ShareBar } from '@/components/charts/ShareBar';
import { StackedColumns } from '@/components/charts/StackedColumns';
import { EventRow } from '@/components/events/EventRow';
import { BasisBadge, type Basis } from '@/components/ui/BasisBadge';
import { EquipmentCard } from '@/features/ukraine/EquipmentCard';
import { CATEGORIES } from '@/lib/api/eventSchemas';
import { SIDE_LABELS } from '@/lib/api/ukraine';
import { CATEGORY_STYLES } from '@/lib/categories';
import { liveEvent } from '@/test/fixtures.events';
import { ukraineReference } from '@/test/fixtures.ukraineReference';
import {
  AA,
  NON_TEXT,
  SURFACES,
  contrast,
  files,
  palettes,
  read,
  type Palette,
} from '@/test/themeContrast';

// The eight application themes; the map keeps its own palette and none of these labels sit on it.
const THEME_PALETTES = Object.entries(palettes).filter(([name]) => name !== 'map dashboard');
// Utilities that share the `text-` prefix without setting a colour.
const NOT_COLOUR = new Set(
  '2xs xs sm base lg xl 2xl 3xl left center right start end wrap nowrap balance pretty ellipsis clip'.split(
    ' ',
  ),
);

interface Paint {
  colour: string;
  alpha: number;
}

function hex(channels: number[]): string {
  return `#${channels.map((value) => Math.round(value).toString(16).padStart(2, '0')).join('')}`;
}

/** `front` drawn at `alpha` over the opaque `back`, as the browser composites it. */
function over(front: string, back: string, alpha: number): string {
  const channel = (colour: string, index: number) =>
    parseInt(colour.slice(1 + index * 2, 3 + index * 2), 16);
  return hex([0, 1, 2].map((i) => channel(front, i) * alpha + channel(back, i) * (1 - alpha)));
}

/** The theme colour a utility prefix (`text` or `bg`) sets on the element, if any. */
function utility(element: HTMLElement, prefix: 'text' | 'bg', palette: Palette): Paint | null {
  const found = [...element.classList].flatMap((name) => {
    const match = /^(text|bg)-([a-z0-9-]+)(?:\/(\d+))?$/.exec(name);
    return match && match[1] === prefix && !NOT_COLOUR.has(match[2]!) ? [match] : [];
  });
  if (found.length > 1) throw new Error(`Several ${prefix} colours on "${element.className}"`);
  const [match] = found;
  if (!match) return null;
  const colour = palette[match[2]!];
  if (!colour) throw new Error(`${match[0]} is not a theme colour`);
  return { colour, alpha: match[3] ? Number(match[3]) / 100 : 1 };
}

/** The label's text colour: an inline literal, or the theme token its class names. */
function textPaint(element: HTMLElement, palette: Palette): Paint {
  const inline = /rgb\((\d+), (\d+), (\d+)\)/.exec(element.style.color);
  if (inline) return { colour: hex(inline.slice(1).map(Number)), alpha: 1 };
  const paint = utility(element, 'text', palette);
  if (!paint) throw new Error(`"${element.className}" sets no text colour of its own`);
  return paint;
}

/** Every theme and surface where the label's text falls below AA, or why it cannot be measured. */
function belowAa(name: string, element: HTMLElement): string[] {
  const failures: string[] = [];
  try {
    for (const [theme, palette] of THEME_PALETTES) {
      for (const surface of SURFACES) {
        let back = palette[surface]!;
        const fill = utility(element, 'bg', palette);
        if (fill) back = over(fill.colour, back, fill.alpha);
        const text = textPaint(element, palette);
        const ratio = contrast(text.colour, back, text.alpha);
        if (ratio < AA) failures.push(`${name} ${theme} ${surface} ${ratio.toFixed(2)}`);
      }
    }
  } catch (error) {
    failures.push(`${name}: ${(error as Error).message}`);
  }
  return failures;
}

function dotOf(label: HTMLElement): HTMLElement | null {
  return label.querySelector<HTMLElement>(':scope > [aria-hidden="true"]');
}

const BASES: Basis[] = ['claimed', 'assessed', 'visually_confirmed', 'documented', 'reported'];
const BADGE_TEXT: Record<Basis, string> = {
  claimed: 'Claimed',
  assessed: 'Assessed',
  visually_confirmed: 'Visually confirmed',
  documented: 'Documented',
  reported: 'Reported',
};

describe('label contrast in every theme', () => {
  it('draws each event category label in a theme text colour beside its map colour dot', () => {
    render(
      <MemoryRouter>
        <ul>
          {CATEGORIES.map((category) => (
            <EventRow
              key={category}
              event={liveEvent({ id: category, category, title: `Report ${category}` })}
            />
          ))}
        </ul>
      </MemoryRouter>,
    );
    const labels = CATEGORIES.map((category) => screen.getByText(CATEGORY_STYLES[category].label));
    expect(CATEGORIES.flatMap((category, index) => belowAa(category, labels[index]!))).toEqual([]);
    CATEGORIES.forEach((category, index) => {
      expect(dotOf(labels[index]!)).toHaveStyle({ backgroundColor: CATEGORY_STYLES[category].css });
    });
  });

  it('keeps every basis badge at AA', () => {
    render(
      <>
        {BASES.map((basis) => (
          <BasisBadge key={basis} basis={basis} />
        ))}
      </>,
    );
    const failures = BASES.flatMap((basis) => {
      const text = BADGE_TEXT[basis];
      return belowAa(text, screen.getByText(text));
    });
    expect(failures).toEqual([]);
  });

  it('keeps the chart colour of data-backed badges on a dot, not on the words', () => {
    render(
      <>
        <BasisBadge basis="visually_confirmed" />
        <BasisBadge basis="documented" />
      </>,
    );
    expect(dotOf(screen.getByText('Visually confirmed'))).toHaveClass('bg-chart-3');
    expect(dotOf(screen.getByText('Documented'))).toHaveClass('bg-chart-5');
  });

  it('keeps both side chips on equipment cards at AA', () => {
    const entries = (['ru', 'ua'] as const).map((side) => {
      const entry = ukraineReference.equipment.find((item) => item.side === side)!;
      return { ...entry, image_id: null, origin: 'Domestic production' };
    });
    render(
      <ul>
        {entries.map((entry) => (
          <EquipmentCard key={entry.id} entry={entry} reference={ukraineReference} showSide />
        ))}
      </ul>,
    );
    const chips = entries.map((entry) => screen.getByText(SIDE_LABELS[entry.side]));
    expect(entries.flatMap((entry, index) => belowAa(`${entry.side} chip`, chips[index]!))).toEqual(
      [],
    );
    expect(dotOf(chips[0]!)).toHaveClass('bg-chart-2');
    expect(dotOf(chips[1]!)).toHaveClass('bg-chart-1');
  });

  it('never draws text in a categorical chart colour anywhere in the app', () => {
    const offenders = files
      .filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file))
      .flatMap((file) =>
        [...read(file).matchAll(/\btext-chart-\d\b/g)].map((match) => `${file} ${match[0]}`),
      );
    expect(offenders).toEqual([]);
  });

  it('never colours label text with a category or timeline phase data colour', () => {
    const offenders = files
      .filter((file) => file.endsWith('.tsx') && !file.endsWith('.test.tsx'))
      .filter((file) => /[{,]\s*color:\s*[\w.[\]]*\.(?:css|colour)\b/.test(read(file)));
    expect(offenders).toEqual([]);
  });

  it('measures blended chip backgrounds the way the browser composites them', () => {
    expect(over('#ffffff', '#000000', 0.5)).toBe('#808080');
    expect(over('#eb6834', '#ffffff', 1)).toBe('#eb6834');
    expect(THEME_PALETTES).toHaveLength(8);
  });
});

describe('chart colour is never the only reading', () => {
  it('keeps every chart series at 3:1 against each Daylight surface', () => {
    const light = palettes.light!;
    const weak = [1, 2, 3, 4, 5, 6].flatMap((slot) =>
      SURFACES.filter(
        (surface) => contrast(light[`chart-${slot}`]!, light[surface]!) < NON_TEXT,
      ).map((surface) => `chart-${slot} on ${surface}`),
    );
    expect(weak).toEqual([]);
  });

  it('states that the table view is the reference reading for stacked columns', () => {
    render(
      <StackedColumns
        days={['2026-09-11', '2026-09-12']}
        series={[{ key: 'claims', label: 'Claims', slot: 4, values: [1, 2] }]}
        label="Daily claims"
      />,
    );
    const figure = screen.getByRole('figure');
    expect(within(figure).getByText(/table view is the reference reading/i)).toBeVisible();
  });

  it('prints every value beside its mark in share bars and bar lists', () => {
    render(
      <>
        <ShareBar
          label="Losses by status"
          parts={[
            { key: 'destroyed', label: 'Destroyed', value: 6, slot: 2 },
            { key: 'damaged', label: 'Damaged', value: 2, slot: 4 },
            { key: 'abandoned', label: 'Abandoned', value: 1, slot: 5 },
            { key: 'captured', label: 'Captured', value: 1, slot: 3 },
          ]}
        />
        <BarList
          label="Actors"
          slot={5}
          rows={[
            { key: 'a', label: 'Actor A', value: 7 },
            { key: 'b', label: 'Actor B', value: 3 },
          ]}
        />
      </>,
    );
    for (const text of ['6 · 60%', '2 · 20%', '1 · 10%', 'Destroyed', 'Captured']) {
      expect(screen.getAllByText(text)[0]).toBeVisible();
    }
    const bars = screen.getByRole('list', { name: 'Actors' });
    expect(within(bars).getByText('7')).toBeVisible();
    expect(within(bars).getByText('3')).toBeVisible();
  });
});

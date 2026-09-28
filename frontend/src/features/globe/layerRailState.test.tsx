import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { useEventsStore } from '@/stores/events';
import { NON_TEXT, contrast, dashboardCss, palettes } from '@/test/themeContrast';

import { MapLayerRail } from './MapLayerRail';

const INDICATOR = ".map-icon-button[role='switch'][aria-checked='true']::before";

/** The declarations of the first rule whose selector list contains `selector`. */
function rule(selector: string): string {
  const start = dashboardCss.indexOf(selector);
  if (start < 0) throw new Error(`Missing ${selector}`);
  const open = dashboardCss.indexOf('{', start);
  return dashboardCss.slice(open + 1, dashboardCss.indexOf('}', open));
}

/** One declaration's value, with dashboard custom properties resolved to hex. */
function value(body: string, property: string): string {
  const match = new RegExp(`(?:^|[;\\s])${property}:\\s*([^;]+);`).exec(body);
  if (!match) throw new Error(`Missing ${property}`);
  const raw = match[1]!.trim();
  const token = /^var\(--color-([\w-]+)\)$/.exec(raw);
  return token ? palettes['map dashboard']![token[1]!]! : raw;
}

/** An `#rrggbb` or `#rrggbbaa` colour composited over an opaque backdrop. */
function over(colour: string, backdrop: string): string {
  const alpha = colour.length === 9 ? parseInt(colour.slice(7), 16) / 255 : 1;
  const channel = (hex: string, index: number) => parseInt(hex.slice(index, index + 2), 16);
  return `#${[1, 3, 5]
    .map((index) =>
      Math.round(channel(colour, index) * alpha + channel(backdrop, index) * (1 - alpha))
        .toString(16)
        .padStart(2, '0'),
    )
    .join('')}`;
}

describe('layer switch on state', () => {
  it('adds a shape cue to on switches that stands 3:1 clear of the switch background', () => {
    const indicator = rule(INDICATOR);
    expect(value(indicator, 'content')).toBe("''");
    const mark = value(indicator, 'background');
    const rail = value(rule('.map-layer-rail,'), 'background');
    const wash = value(rule(".map-icon-button[aria-checked='true'],"), 'background');
    // The rail is translucent, so check it over the darkest and lightest map imagery.
    for (const imagery of ['#000000', '#ffffff']) {
      const off = over(rail, imagery);
      const on = over(wash, off);
      expect(contrast(mark, off)).toBeGreaterThanOrEqual(NON_TEXT);
      expect(contrast(mark, on)).toBeGreaterThanOrEqual(NON_TEXT);
    }
  });

  it('draws the indicator only for on states, never for off switches', () => {
    const selectors = dashboardCss
      .split('{')
      .slice(0, -1)
      .flatMap((chunk) => chunk.slice(chunk.lastIndexOf('}') + 1).split(','))
      .map((selector) => selector.trim())
      .filter((selector) => selector.includes('.map-icon-button') && selector.includes('::before'));
    expect(selectors).toContain(INDICATOR.trim());
    for (const selector of selectors) {
      expect(selector).toMatch(/\[(aria-checked|data-on)='true'\]::before$/);
    }
  });

  it('exposes state through aria-checked without renaming the switch', async () => {
    const user = userEvent.setup();
    useEventsStore.setState({ hidden: ['space'] });
    render(
      <MapLayerRail
        events={[]}
        counts={{ space: 3, conflict: 2 }}
        visibility={{ aircraft: true, vessels: true, firms: true }}
        onToggle={vi.fn()}
      />,
    );
    const space = screen.getByRole('switch', { name: 'Space 3' });
    const conflict = screen.getByRole('switch', { name: 'Conflict & unrest 2' });
    expect(space).toHaveAttribute('aria-checked', 'false');
    expect(conflict).toHaveAttribute('aria-checked', 'true');
    await user.click(space);
    await user.click(conflict);
    expect(space).toHaveAttribute('aria-checked', 'true');
    expect(space).toHaveAccessibleName('Space 3');
    expect(conflict).toHaveAttribute('aria-checked', 'false');
    expect(conflict).toHaveAccessibleName('Conflict & unrest 2');
  });
});

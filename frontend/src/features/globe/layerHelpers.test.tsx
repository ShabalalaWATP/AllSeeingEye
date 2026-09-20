import { render, renderHook, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { RadarAttackSnapshot } from '@/lib/api/cyber';
import { clearAssistantMapFocus, locateAssistantPoint } from '@/lib/assistantMapContext';
import { countries } from '@/test/fixtures';
import { liveEvent } from '@/test/fixtures.events';
import { publicFigure } from '@/test/fixtures.figures';

import { NetworkCountryInspector } from './NetworkCountryInspector';
import { RadarAttackInspector } from './RadarAttackInspector';
import { buildFigureLayers } from './figures/figureLayers';
import { useFigureSelection } from './figures/useFigureSelection';
import type { FigureState } from './figures/useFigures';
import { buildApproximateLayer } from './layers/approximate';
import { buildSelectionLayer } from './layers/selection';

interface Accessors {
  data: readonly unknown[];
  billboard: boolean;
  getPosition: (item: unknown) => number[];
  getRadius: (item: unknown) => number;
  getLineColor: (item: unknown) => number[];
  getLineWidth: (item: unknown) => number;
  getFillColor: (item: unknown) => number[];
  getSize: (item: unknown) => number;
  getIcon: (item: unknown) => { url: string; mask: boolean };
  getAngle: number;
  onClick: (info: { object?: unknown; x?: number; y?: number }) => boolean;
}

const props = (layer: { props: unknown }) => layer.props as Accessors;

describe('globe layer helpers', () => {
  it('draws the selection halo at the event or nowhere', () => {
    const located = props(buildSelectionLayer(liveEvent()));
    expect(located.getPosition(liveEvent())).toEqual([10, 50]);
    expect(located.getPosition(liveEvent({ point: null }))).toEqual([NaN, NaN]);
  });

  it('marks approximate events with rings that follow selection and category', () => {
    const onPick = vi.fn();
    expect(buildApproximateLayer([], onPick, null)).toBeNull();
    const conflict = liveEvent({ id: 'c1', category: 'conflict', subtype: 'battle' });
    const quake = liveEvent({ id: 'q1' });
    const layer = props(buildApproximateLayer([conflict, quake], onPick, 'c1')!);
    expect(layer.getRadius(conflict)).toBe(14);
    expect(layer.getRadius(quake)).toBe(10);
    expect(layer.getLineColor(conflict)).toEqual([255, 255, 255, 255]);
    expect(layer.getLineColor(quake).at(-1)).toBe(220);
    expect(layer.getFillColor(quake).at(-1)).toBe(24);
    expect(layer.getPosition(liveEvent({ point: null }))).toEqual([NaN, NaN]);
    expect(layer.onClick({ object: quake, x: 3, y: 4 })).toBe(true);
    expect(onPick).toHaveBeenLastCalledWith(quake, [3, 4]);
    layer.onClick({});
    expect(onPick).toHaveBeenLastCalledWith(null);
  });

  it('builds figure rings, portraits and fallbacks with selection and projection', () => {
    const onSelect = vi.fn();
    const withPortrait = publicFigure();
    const bare = publicFigure({ id: 'bare', portrait: null, wikidata_id: 'Q2' });
    // Selection starts first in roster order but must render above its neighbours.
    const layers = buildFigureLayers([bare, withPortrait], onSelect, 'bare', true);
    expect(layers.map((layer) => layer.id)).toEqual([
      'public-figure-rings',
      'public-figure-portraits',
      'public-figure-selected-rings',
      'public-figure-selected-fallbacks',
    ]);
    const rings = props(layers[0]!);
    const selectedRings = props(layers[2]!);
    expect(rings.data).toEqual([withPortrait]);
    expect(selectedRings.data).toEqual([bare]);
    expect(selectedRings.getLineWidth(bare)).toBe(3);
    expect(rings.getLineWidth(withPortrait)).toBe(2);
    expect(selectedRings.getRadius(bare)).toBeGreaterThan(rings.getRadius(withPortrait));
    expect(selectedRings.getPosition(bare)).toEqual([36.23, 49.99]);
    expect(selectedRings.onClick({ object: bare })).toBe(true);
    expect(onSelect).toHaveBeenCalledWith(bare);
    const portraits = props(layers[1]!);
    expect(portraits.data).toEqual([withPortrait]);
    expect(portraits.getIcon(withPortrait).url.startsWith('data:image/png')).toBe(true);
    expect(portraits.getAngle).toBe(180);
    expect(portraits.billboard).toBe(false);
    portraits.onClick({});
    const fallbacks = props(layers[3]!);
    expect(fallbacks.data).toEqual([bare]);
    expect(fallbacks.getIcon(bare).mask).toBe(true);
    expect(fallbacks.getAngle).toBe(180);
    expect(fallbacks.getSize(bare)).toBeGreaterThan(portraits.getSize(withPortrait));
    fallbacks.onClick({ object: bare });
    expect(onSelect).toHaveBeenCalledTimes(2);
    const flat = buildFigureLayers([withPortrait], onSelect, null, false);
    expect(flat).toHaveLength(2);
    expect(props(flat[1]!).getAngle).toBe(0);
    expect(props(flat[1]!).billboard).toBe(true);

    const portraitSelected = buildFigureLayers([withPortrait, bare], onSelect, withPortrait.id);
    expect(portraitSelected.map((layer) => layer.id)).toEqual([
      'public-figure-rings',
      'public-figure-fallbacks',
      'public-figure-selected-rings',
      'public-figure-selected-portraits',
    ]);
    expect(props(portraitSelected[1]!).data).toEqual([bare]);
    expect(props(portraitSelected[3]!).data).toEqual([withPortrait]);
    expect(props(portraitSelected[3]!).getSize(withPortrait)).toBeGreaterThan(
      props(portraitSelected[1]!).getSize(bare),
    );
  });

  it('selects and flies to figures unless a tool is picking', () => {
    const select = vi.fn();
    const close = vi.fn();
    const flyTo = vi.fn();
    const engine = { flyTo } as unknown as Parameters<typeof useFigureSelection>[3];
    const figures = { visible: [publicFigure()], selected: null, select } as unknown as FigureState;
    const { result, rerender } = renderHook(
      ({ picking }) => useFigureSelection(figures, picking, close, engine, 'globe'),
      { initialProps: { picking: false } },
    );
    result.current.focusFigure(publicFigure());
    expect(close).toHaveBeenCalledTimes(1);
    expect(select).toHaveBeenCalledTimes(1);
    expect(flyTo).toHaveBeenCalledWith({ center: [36.23, 49.99], zoom: 8 });
    result.current.focusFigure(
      publicFigure({ placement: { ...publicFigure().placement, basis: 'seat' } }),
    );
    expect(flyTo).toHaveBeenLastCalledWith({ center: [36.23, 49.99], zoom: 5 });
    rerender({ picking: true });
    result.current.focusFigure(publicFigure());
    expect(select).toHaveBeenCalledTimes(2);
    expect(flyTo).toHaveBeenCalledTimes(2);
    expect(result.current.figureLayers.length).toBeGreaterThan(0);
  });
});

describe('country inspectors', () => {
  const country = countries[0]!;

  it('lists network records with links, caps at 25 and closes on Escape', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    const events = Array.from({ length: 27 }, (_, index) =>
      liveEvent({
        id: `n${index}`,
        title: `Outage ${index}`,
        url: index ? null : 'https://x.test',
      }),
    );
    render(<NetworkCountryInspector group={{ country, events }} onClose={onClose} />);
    expect(screen.getByRole('link', { name: 'Open source' })).toHaveAttribute(
      'href',
      'https://x.test',
    );
    expect(screen.getByText('Showing 25 of 27 records.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Close network country details' })).toHaveFocus();
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole('button', { name: 'Close network country details' }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  it('shows one connectivity record without a link', () => {
    render(
      <NetworkCountryInspector
        group={{ country, events: [liveEvent({ url: null })] }}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText(/1 provider-reported connectivity record\./)).toBeInTheDocument();
    expect(screen.queryByRole('link')).toBeNull();
  });

  it('renders radar shares, periods, stale notice and source link', () => {
    const snapshot: RadarAttackSnapshot = {
      status: 'stale',
      fetched_at: '2026-09-13T00:00:00Z',
      layers: [
        {
          layer: 'layer3',
          period_from: '2026-09-06T00:00:00Z',
          period_to: '2026-09-13T00:00:00Z',
          updated_at: null,
          unit: 'bytes',
          countries: [],
        },
        {
          layer: 'layer7',
          period_from: '2026-09-06T00:00:00Z',
          period_to: '2026-09-13T00:00:00Z',
          updated_at: null,
          unit: 'requests',
          countries: [],
        },
      ],
      source_url: 'https://radar.cloudflare.com/',
    };
    render(
      <RadarAttackInspector
        row={{ country, layer3: 12.345, layer7: null }}
        snapshot={snapshot}
        onClose={vi.fn()}
      />,
    );
    expect(screen.getByText('12.3%')).toBeInTheDocument();
    expect(screen.getByText('Not in top 10')).toBeInTheDocument();
    expect(screen.getByText(/L3\/4:/)).toBeInTheDocument();
    expect(screen.getByText(/L7:/)).toBeInTheDocument();
    expect(screen.getByText(/Previously collected data/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Cloudflare Radar source' })).toBeInTheDocument();
  });
});

describe('inspector focus handling', () => {
  it('returns focus to the opener on close and ignores a handled Escape', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<button type="button">opener</button>);
    const opener = screen.getByRole('button', { name: 'opener' });
    opener.focus();
    const { unmount } = render(
      <RadarAttackInspector
        row={{ country: countries[0]!, layer3: null, layer7: 4 }}
        snapshot={{
          status: 'ready',
          fetched_at: null,
          layers: [],
          source_url: 'https://radar.cloudflare.com/',
        }}
        onClose={onClose}
      />,
    );
    expect(screen.getByRole('button', { name: 'Close Cloudflare traffic details' })).toHaveFocus();
    const handled = new KeyboardEvent('keydown', { key: 'Escape', cancelable: true });
    handled.preventDefault();
    window.dispatchEvent(handled);
    expect(onClose).not.toHaveBeenCalled();
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
    unmount();
    expect(opener).toHaveFocus();
  });
});

describe('assistant point locator', () => {
  it('ignores impossible coordinates and queues valid ones when no map is registered', () => {
    clearAssistantMapFocus();
    expect(() => locateAssistantPoint({ lon: 200, lat: 0 })).not.toThrow();
    expect(() => locateAssistantPoint({ lon: 0, lat: Number.NaN })).not.toThrow();
    expect(() => locateAssistantPoint({ lon: 30.5, lat: 50.4 })).not.toThrow();
    clearAssistantMapFocus();
  });
});

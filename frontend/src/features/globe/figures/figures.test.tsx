import { act, render, renderHook, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { figureBoard, publicFigure } from '@/test/fixtures.figures';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import { FigureInspector } from './FigureInspector';
import { FigurePanel } from './FigurePanel';
import { buildFigureLayers } from './figureLayers';
import { useFigures, type FigureState } from './useFigures';

function state(overrides: Partial<FigureState> = {}): FigureState {
  return {
    enabled: true,
    setEnabled: vi.fn(),
    board: figureBoard,
    loading: false,
    error: null,
    query: '',
    setQuery: vi.fn(),
    reportedOnly: false,
    setReportedOnly: vi.fn(),
    countries: new Set<string>(),
    countryOptions: [
      { code: 'GB', count: 1 },
      { code: 'UA', count: 1 },
      { code: 'ORG', count: 1 },
    ],
    toggleCountry: vi.fn(),
    clearCountries: vi.fn(),
    visible: figureBoard.figures,
    selected: null,
    select: vi.fn(),
    close: vi.fn(),
    refresh: vi.fn(),
    ...overrides,
  };
}

describe('public figures layer', () => {
  it('stays off until a signed-in user turns it on, then loads and filters the roster', async () => {
    applySession('user');
    const { result } = renderHook(() => useFigures());
    expect(result.current.enabled).toBe(false);
    expect(result.current.visible).toEqual([]);
    act(() => result.current.setEnabled(true));
    await waitFor(() => expect(result.current.board).not.toBeNull());
    expect(result.current.visible).toHaveLength(3);
    act(() => result.current.setReportedOnly(true));
    expect(result.current.visible.map((figure) => figure.id)).toEqual(['ua-head-of-state', 'nato']);
    act(() => result.current.setQuery('rutte'));
    expect(result.current.visible.map((figure) => figure.id)).toEqual(['nato']);
    act(() => result.current.setQuery(''));
    act(() => result.current.setReportedOnly(false));
    expect(result.current.countryOptions.map((option) => option.code)).toEqual(['GB', 'UA', 'ORG']);
    act(() => result.current.toggleCountry('GB'));
    act(() => result.current.toggleCountry('ORG'));
    expect(result.current.visible.map((figure) => figure.id)).toEqual([
      'gb-head-of-government',
      'nato',
    ]);
    act(() => result.current.toggleCountry('GB'));
    expect(result.current.visible.map((figure) => figure.id)).toEqual(['nato']);
    act(() => result.current.clearCountries());
    expect(result.current.visible).toHaveLength(3);
    act(() => result.current.select(result.current.visible[0] ?? null));
    expect(result.current.selected?.name).toBe('Volodymyr Zelenskyy');
    act(() => result.current.setEnabled(false));
    expect(result.current.visible).toEqual([]);
    expect(result.current.selected).toBeNull();
  });

  it('reports a load failure without exposing the response', async () => {
    applySession('user');
    server.use(http.get('/api/figures', () => HttpResponse.json({ detail: 'x' }, { status: 500 })));
    const { result } = renderHook(() => useFigures());
    act(() => result.current.setEnabled(true));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toBe('Public figures could not be loaded. Retry to reconnect.');
    expect(result.current.visible).toEqual([]);
  });

  it('never fetches for an anonymous identity', async () => {
    applySession('anonymous');
    const seen = vi.fn();
    server.use(
      http.get('/api/figures', () => {
        seen();
        return HttpResponse.json(figureBoard);
      }),
    );
    const { result } = renderHook(() => useFigures());
    act(() => result.current.setEnabled(true));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(seen).not.toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
  });

  it('rings each marker by its placement basis and keeps fallbacks separate', () => {
    const layers = buildFigureLayers(figureBoard.figures, vi.fn(), 'nato', true);
    expect(layers.map((layer) => layer.id)).toEqual([
      'public-figure-rings',
      'public-figure-portraits',
      'public-figure-fallbacks',
    ]);
    const rings = layers[0]?.props as unknown as {
      getLineColor: (figure: (typeof figureBoard.figures)[number]) => number[];
      getRadius: (figure: (typeof figureBoard.figures)[number]) => number;
    };
    const [reported, seat, nato] = figureBoard.figures;
    expect(rings.getLineColor(reported!)).toEqual([98, 222, 190, 255]);
    expect(rings.getLineColor(seat!)).toEqual([150, 160, 175, 210]);
    expect(rings.getRadius(nato!)).toBeGreaterThan(rings.getRadius(reported!));
    const portraits = layers[1]?.props as unknown as {
      data: unknown[];
      getIcon: (figure: (typeof figureBoard.figures)[number]) => { url: string; mask: boolean };
    };
    expect(portraits.data).toHaveLength(2);
    expect(portraits.getIcon(reported!).url.startsWith('data:image/png;base64,')).toBe(true);
    expect(portraits.getIcon(reported!).mask).toBe(false);
    expect(buildFigureLayers([], vi.fn(), null)).toEqual([]);
  });

  it('lists figures with their basis and forwards selection from the panel', async () => {
    const figures = state();
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<FigurePanel figures={figures} onSelect={onSelect} />);
    expect(screen.getByRole('switch', { name: 'Show public figures' })).toBeChecked();
    expect(
      screen.getByText(/3 shown, 2 placed by reporting, from 240 reports in 72 h/),
    ).toBeVisible();
    const list = screen.getByRole('list', { name: 'Figures on the map' });
    const row = within(list).getByRole('button', { name: /Andy Burnham/ });
    expect(within(row).getByText('Seat of office')).toBeVisible();
    expect(list.querySelectorAll('img')).toHaveLength(2);
    await user.click(row);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'gb-head-of-government' }));
    await user.click(screen.getByRole('checkbox', { name: 'Only reported placements' }));
    expect(figures.setReportedOnly).toHaveBeenCalledWith(true);
    await user.type(screen.getByRole('searchbox', { name: 'Find a figure' }), 'ru');
    expect(figures.setQuery).toHaveBeenCalled();
    const countries = screen.getByRole('group', { name: 'Countries' });
    expect(within(countries).getByRole('button', { name: 'All' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await user.click(within(countries).getByRole('button', { name: /^GB/ }));
    expect(figures.toggleCountry).toHaveBeenCalledWith('GB');
    expect(within(countries).getByRole('button', { name: /^Orgs/ })).toHaveAttribute(
      'title',
      'Organisations',
    );
    await user.click(within(countries).getByRole('button', { name: 'All' }));
    expect(figures.clearCountries).toHaveBeenCalled();
  });

  it('hides the roster and shows the doctrine note while the layer is off', () => {
    render(<FigurePanel figures={state({ enabled: false, visible: [], board: null })} />);
    expect(screen.getByRole('switch', { name: 'Show public figures' })).not.toBeChecked();
    expect(screen.queryByRole('list', { name: 'Figures on the map' })).not.toBeInTheDocument();
    expect(screen.getByText(/Nothing here is a confirmed position/)).toBeVisible();
  });

  it('explains the placement basis, lists reporting and credits the portrait', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<FigureInspector figure={publicFigure()} onClose={onClose} />);
    const aside = screen.getByRole('complementary', { name: 'Public figure details' });
    expect(within(aside).getByRole('heading', { name: 'Volodymyr Zelenskyy' })).toBeVisible();
    expect(within(aside).getByText('Reported location')).toBeVisible();
    expect(within(aside).getByText(/not confirmed presence/)).toBeVisible();
    const reporting = within(aside).getByRole('region', { name: 'Recent reporting' });
    expect(within(reporting).getByRole('link', { name: /Zelenskyy visits/ })).toHaveAttribute(
      'rel',
      'noreferrer',
    );
    expect(within(aside).getByRole('link', { name: 'Wikimedia Commons' })).toHaveAttribute(
      'href',
      'https://commons.wikimedia.org/wiki/File:Example.jpg',
    );
    expect(document.activeElement).toBe(
      within(aside).getByRole('button', { name: 'Close public figure details' }),
    );
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });

  it('states that absent reporting is not a location when a figure sits at the seat', () => {
    const seat = figureBoard.figures[1]!;
    render(<FigureInspector figure={seat} onClose={vi.fn()} />);
    expect(screen.getByText(/not evidence of location/)).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
  });
});

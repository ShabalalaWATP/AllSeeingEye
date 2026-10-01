import { act, fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { liveEvent } from '@/test/fixtures';
import { GeographicPrecisionPanel } from './GeographicPrecisionPanel';
import { EventInspector } from './EventInspector';
import { buildEventLayers } from './layers/registry';
import { isMappedEvent } from './geographicPrecision';
import { SETTLE_MS } from '@/lib/hooks/useSettledAnnouncement';

it.each([0, 6])('separates approximate locations from exact clustering at zoom %s', (zoom) => {
  const exact = ['a', 'b', 'c'].map((id) => liveEvent({ id, point: { lon: 1, lat: 1 } }));
  const city = liveEvent({
    id: 'city',
    geo_confidence: 'city',
    point: { lon: 1, lat: 1 },
    category: 'aviation',
  });
  const country = liveEvent({ id: 'country', geo_confidence: 'country' });
  const unknown = liveEvent({ id: 'unknown', geo_confidence: 'none' });
  const onPick = vi.fn();
  const layers = buildEventLayers([...exact, city, country, unknown], [], onPick, 'city', {
    zoom,
    onCluster: vi.fn(),
  });
  const approximate = layers.find((layer) => layer.id === 'approximate-events')!;
  expect(approximate.props.data).toEqual([city]);
  expect(approximate.props).toMatchObject({ filled: true, stroked: true, radiusUnits: 'pixels' });
  const allData = layers.flatMap((layer) => Array.from(layer.props.data as unknown[]));
  expect(allData).not.toContain(country);
  expect(allData).not.toContain(unknown);
  if (zoom === 0)
    expect(layers.find((layer) => layer.id === 'clusters')!.props.data).toMatchObject([
      { count: 3 },
    ]);
  expect(layers.some((layer) => layer.id === 'event-icons')).toBe(false);
});

it('keeps every unplotted item selectable through pages and respects category filters', async () => {
  const records = Array.from({ length: 21 }, (_, i) =>
    liveEvent({ id: String(i), title: `Unknown record ${i}`, point: null }),
  );
  const onSelect = vi.fn();
  const { rerender } = render(
    <GeographicPrecisionPanel
      events={records}
      hidden={[]}
      filter="all"
      onFilterChange={vi.fn()}
      onSelect={onSelect}
    />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByText('How locations are classified'));
  await user.click(screen.getByText('Not plotted (21)'));
  await user.click(screen.getByRole('button', { name: 'Next' }));
  await user.click(screen.getByRole('button', { name: /Unknown record 20/ }));
  expect(onSelect).toHaveBeenCalledWith(records[20]);
  rerender(
    <GeographicPrecisionPanel
      events={records}
      hidden={['disaster']}
      filter="all"
      onFilterChange={vi.fn()}
      onSelect={onSelect}
    />,
  );
  expect(screen.getByText('Not plotted (0)')).toBeVisible();
  expect(screen.queryByRole('button', { name: /Unknown record/ })).not.toBeInTheDocument();
});

it('does not present legacy country centroid coordinates as an incident position', () => {
  render(
    <MemoryRouter>
      <EventInspector event={liveEvent({ geo_confidence: 'country' })} onClose={vi.fn()} />
    </MemoryRouter>,
  );
  expect(screen.getByText('Country only, no incident position')).toBeVisible();
  expect(screen.queryByText(/50.000/)).not.toBeInTheDocument();
});

it('rejects invalid supplied geometry without relocating the event', () => {
  expect(isMappedEvent(liveEvent({ point: { lon: 181, lat: 1 } }))).toBe(false);
  expect(isMappedEvent(liveEvent({ point: { lon: 1, lat: NaN } }))).toBe(false);
  expect(isMappedEvent(liveEvent({ point: { lon: 180, lat: 90 } }))).toBe(true);
});

describe('location quality list announcements', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  const records = (count: number) =>
    Array.from({ length: count }, (_, i) =>
      liveEvent({ id: `r${String(i)}`, title: `Loaded record ${String(i)}`, point: null }),
    );
  const panel = (count: number) => (
    <GeographicPrecisionPanel
      events={records(count)}
      hidden={[]}
      filter="all"
      onFilterChange={vi.fn()}
      onSelect={vi.fn()}
    />
  );
  const settle = () => act(() => vi.advanceTimersByTimeAsync(SETTLE_MS));

  function announcements(): string[] {
    const region = screen.getByRole('status');
    const seen: string[] = [];
    new MutationObserver(() => {
      if (region.textContent) seen.push(region.textContent);
    }).observe(region, { childList: true, characterData: true, subtree: true });
    return seen;
  }

  it('keeps streamed count changes out of the live region', async () => {
    const view = render(panel(25));
    const seen = announcements();
    expect(screen.getByText('25 matching loaded records · page 1 of 2')).toBeInTheDocument();
    for (const count of [30, 45, 70]) {
      view.rerender(panel(count));
      await settle();
    }
    expect(screen.getByText('70 matching loaded records · page 1 of 4')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('');
    expect(seen).toEqual([]);
  });

  it('announces the settled result of a search, filter or page change once', async () => {
    const view = render(panel(45));
    const seen = announcements();
    const search = screen.getByLabelText('Search loaded records');
    for (const text of ['L', 'Lo', 'Loaded record 1'])
      fireEvent.change(search, { target: { value: text } });
    expect(seen).toEqual([]);
    await settle();
    expect(seen).toEqual(['11 matching loaded records, page 1 of 1.']);
    view.rerender(panel(60));
    await settle();
    expect(seen).toHaveLength(1);
    fireEvent.change(search, { target: { value: '' } });
    await settle();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    await settle();
    expect(seen).toEqual([
      '11 matching loaded records, page 1 of 1.',
      '60 matching loaded records, page 1 of 3.',
      '60 matching loaded records, page 2 of 3.',
    ]);
    fireEvent.change(screen.getByLabelText('Show on map or globe'), {
      target: { value: 'reported' },
    });
    await settle();
    // The filter is owned by the parent here; the page resets and an identical result still speaks.
    expect(seen.at(-1)).toBe('60 matching loaded records, page 1 of 3.');
    expect(seen).toHaveLength(4);
  });
});

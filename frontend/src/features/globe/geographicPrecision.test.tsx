import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router';
import { liveEvent } from '@/test/fixtures';
import { GeographicPrecisionPanel } from './GeographicPrecisionPanel';
import { EventInspector } from './EventInspector';
import { buildEventLayers } from './layers/registry';
import { isMappedEvent } from './geographicPrecision';

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
    <GeographicPrecisionPanel events={records} hidden={[]} onSelect={onSelect} />,
  );
  const user = userEvent.setup();
  await user.click(screen.getByText('Not plotted (21)'));
  await user.click(screen.getByRole('button', { name: 'Next' }));
  await user.click(screen.getByRole('button', { name: /Unknown record 20/ }));
  expect(onSelect).toHaveBeenCalledWith(records[20]);
  rerender(<GeographicPrecisionPanel events={records} hidden={['disaster']} onSelect={onSelect} />);
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

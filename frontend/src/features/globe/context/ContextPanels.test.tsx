import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import * as api from '@/lib/api/events';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { applySession } from '@/test/render';
import { liveEvent } from '@/test/fixtures.events';
import { SpaceWeatherPanel } from './SpaceWeatherPanel';
import { ConnectivityPanel } from './ConnectivityPanel';
import { NavigationWarningsPanel } from './NavigationWarningsPanel';
import { attribute, utcDate } from './contextPresentation';

afterEach(() => vi.restoreAllMocks());
function serve(events: LiveEvent[]) {
  applySession('user');
  return vi
    .spyOn(api, 'fetchEvents')
    .mockImplementation((query) =>
      Promise.resolve(events.filter((event) => query?.sources?.includes(event.source_id))),
    );
}

it('shows reported NOAA scales and separate Kp without inventing local conditions', async () => {
  const events = [
    liveEvent({
      id: 'scales',
      source_id: 'noaa_swpc_scales',
      attributes: { r: '1', s: null, g: '2', stamp: '2026-09-10 12:30:00' },
      point: null,
    }),
    liveEvent({
      id: 'kp',
      source_id: 'swpc_kp',
      attributes: { kp: 1.5, time_tag: '2026-09-10T09:00:00' },
      point: null,
    }),
    liveEvent({
      id: 'bulletin',
      source_id: 'noaa_swpc_alerts',
      title: 'CANCEL: storm warning',
      point: null,
    }),
  ];
  const fetch = serve(events);
  const onSelect = vi.fn();
  render(<SpaceWeatherPanel country="GB" onSelect={onSelect} />);
  await screen.findByText('R1');
  expect(screen.getByText('G2')).toBeVisible();
  expect(screen.getByText('Unknown')).toBeVisible();
  expect(screen.getByText('1.50')).toBeVisible();
  expect(screen.getByText(/Scales issued: 2026-09-10 12:30 UTC/)).toBeVisible();
  expect(screen.getByText(/GB nation filter does not apply/)).toBeVisible();
  expect(fetch.mock.calls.every(([query]) => !query?.bbox && !query?.country)).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'View details' }));
  expect(onSelect).toHaveBeenCalledWith(events[2]);
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'no match' } });
  expect(screen.getByText('No matching bulletins in this snapshot.')).toBeVisible();
});

it('bounds connectivity rows, searches raw signals, preserves zero and rejects unsafe links', async () => {
  const events = Array.from({ length: 40 }, (_, index) =>
    liveEvent({
      id: `ioda-${index}`,
      source_id: 'ioda_outages',
      title: `Signal ${index}`,
      point: null,
      url: index === 0 ? 'javascript:alert(1)' : 'https://example.com/signal',
      attributes: {
        entity_type: 'country',
        entity_code: 'TN',
        datasource: index === 0 ? 'bgp' : 'ping',
        level: 'critical',
        value: 0,
        history_value: 100,
      },
    }),
  );
  const fetch = serve(events);
  const onSelect = vi.fn();
  render(<ConnectivityPanel country="TN" onSelect={onSelect} />);
  await screen.findByText('Signal 0');
  expect(screen.getAllByRole('listitem')).toHaveLength(25);
  expect(screen.getByText(/Recovery messages are not retained/)).toBeVisible();
  expect(fetch.mock.calls[0]![0]).toEqual({ sources: ['ioda_outages'], country: 'TN', limit: 100 });
  fireEvent.change(screen.getByRole('combobox'), { target: { value: 'bgp' } });
  expect(screen.getAllByRole('listitem')).toHaveLength(1);
  expect(screen.getByText('0 / 100')).toBeVisible();
  expect(screen.queryByRole('link', { name: 'Open source' })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'View details' }));
  expect(onSelect).toHaveBeenCalledWith(events[0]);
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'missing' } });
  expect(screen.getByText('No matching connectivity signals in this snapshot.')).toBeVisible();
});

it('filters NGA areas and keyword topics, locates only reported positions and keeps unlocated warnings', async () => {
  const events = [
    liveEvent({
      id: 'nav1',
      source_id: 'nga_navarea',
      title: 'GNSS warning',
      attributes: { nav_area: '4', authority: 'NGA', kind: 'gnss', positions: 3, status: 'active' },
    }),
    liveEvent({
      id: 'nav2',
      source_id: 'nga_navarea',
      title: 'Exercise warning',
      point: null,
      attributes: {
        nav_area: 'P',
        authority: 'Coastguard',
        kind: 'military_exercise',
        positions: 0,
      },
    }),
  ];
  const fetch = serve(events);
  const onSelect = vi.fn();
  render(<NavigationWarningsPanel country="GB" onSelect={onSelect} />);
  await screen.findByText('GNSS warning');
  expect(fetch.mock.calls[0]![0]).toEqual({ sources: ['nga_navarea'], limit: 100 });
  expect(screen.getByText(/GB nation filter does not apply/)).toBeVisible();
  expect(
    screen.getByText(/Topics are keyword matches, not official classifications/),
  ).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Locate first position' }));
  expect(onSelect).toHaveBeenLastCalledWith(events[0]);
  fireEvent.click(screen.getByRole('button', { name: 'View details' }));
  expect(onSelect).toHaveBeenLastCalledWith(events[1]);
  fireEvent.change(screen.getByRole('combobox', { name: 'NAVAREA' }), { target: { value: 'P' } });
  expect(screen.queryByText('GNSS warning')).not.toBeInTheDocument();
  fireEvent.change(screen.getByRole('combobox', { name: 'Topic match' }), {
    target: { value: 'gnss' },
  });
  expect(screen.getByText('No matching navigation warnings in this snapshot.')).toBeVisible();
});

it('offers explicit retry after an unavailable snapshot and reports empty conditions honestly', async () => {
  applySession('user');
  const fetch = vi
    .spyOn(api, 'fetchEvents')
    .mockRejectedValueOnce(new Error('offline'))
    .mockResolvedValue([]);
  render(<ConnectivityPanel />);
  await screen.findByRole('alert');
  fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
  await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(screen.getByText(/empty list does not establish normal conditions/)).toBeVisible();
});

it('does not convert malformed or missing dates and scalar values into observations', () => {
  expect(utcDate(null)).toBe('Not reported');
  expect(utcDate('2026-99-99T00:00:00')).toBe('Not reported');
  expect(utcDate('2026-09-10T09:00:00+01:00')).toBe('2026-09-10 08:00 UTC');
  expect(attribute(liveEvent({ attributes: { value: false } }), 'value')).toBe('Not reported');
  expect(attribute(liveEvent({ attributes: { value: '' } }), 'value')).toBe('Not reported');
});

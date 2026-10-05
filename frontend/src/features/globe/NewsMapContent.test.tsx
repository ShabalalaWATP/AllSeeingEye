import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { liveEvent } from '@/test/fixtures';
import { applySession } from '@/test/render';
import { server } from '@/test/server';
import { ControlPanel, GlobeControls } from './GlobeControls';
import { NewsMapContent } from './NewsMapContent';
import * as precision from './geographicPrecision';
import { useNewsFilters } from './newsFilters';

const city = liveEvent({ id: 'city', category: 'news', geo_confidence: 'city' });
const country = liveEvent({
  id: 'country',
  category: 'news',
  geo_confidence: 'country',
  country_iso: 'GB',
});
const initial = [city, country, { ...country, id: 'same-country' }, liveEvent()];

function Fixture({
  events,
  loading = false,
  error = null,
  nation = null,
}: {
  events: readonly LiveEvent[];
  loading?: boolean;
  error?: unknown;
  nation?: string | null;
}) {
  const filters = useNewsFilters(events, true);
  return (
    <MemoryRouter>
      <GlobeControls layers={null}>
        <ControlPanel label="News briefing" icon="news">
          <NewsMapContent
            filters={filters}
            country={nation}
            windowHours={24}
            onSelect={vi.fn()}
            mapEvents={events}
            loading={loading}
            error={error}
          />
        </ControlPanel>
      </GlobeControls>
    </MemoryRouter>
  );
}

beforeEach(() => {
  applySession('user');
  server.use(http.get('/api/events', () => HttpResponse.json({ items: [], count: 0 })));
});

it('defers map summary work until opening and reads the latest already-filtered scope', async () => {
  const mapped = vi.spyOn(precision, 'isMappedEvent');
  const view = render(<Fixture events={initial} />);
  expect(mapped).not.toHaveBeenCalled();
  const corrected = { ...city, geo_confidence: 'country' as const, country_iso: 'FR' };
  view.rerender(<Fixture events={[corrected, country]} />);
  expect(mapped).not.toHaveBeenCalled();
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(screen.getByText(/0 located reports · 2 country references/)).toBeVisible();
  expect(mapped).toHaveBeenCalled();
  view.rerender(<Fixture events={[country]} nation="GB" />);
  expect(screen.getByText(/0 located reports · 1 country references/)).toBeVisible();
  expect(screen.getByText(/Nation: GB/)).toBeVisible();
  view.rerender(<Fixture events={[]} nation="GB" />);
  expect(screen.getByText(/0 located reports · 0 country references/)).toBeVisible();
  await user.keyboard('{Escape}');
  mapped.mockClear();
  view.rerender(<Fixture events={initial} />);
  expect(mapped).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(screen.getByText(/1 located reports · 1 country references/)).toBeVisible();
});

it('updates loading, failures and in-place row corrections without stale summary values', async () => {
  const corrected = { ...city };
  const events = [corrected];
  const view = render(<Fixture events={events} loading />);
  await userEvent.click(screen.getByRole('button', { name: 'News briefing' }));
  expect(screen.getByText(/Loading news map locations/)).toBeVisible();
  view.rerender(<Fixture events={events} error={new Error('Map snapshot unavailable')} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Something went wrong. Please try again.');
  expect(screen.getByRole('alert')).not.toHaveTextContent('Map snapshot unavailable');
  corrected.geo_confidence = 'country';
  corrected.country_iso = 'GB';
  view.rerender(<Fixture events={events} />);
  expect(screen.getByText(/0 located reports · 1 country references/)).toBeVisible();
});

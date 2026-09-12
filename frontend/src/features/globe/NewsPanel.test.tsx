import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { LiveEvent } from '@/lib/api/eventSchemas';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, liveEvent, plainUser, tokenFor } from '@/test/fixtures';
import { server } from '@/test/server';
import { NewsPanel } from './NewsPanel';
import { useNewsFilters } from './newsFilters';

function article(id: string, overrides: Partial<LiveEvent> = {}) {
  return liveEvent({
    id,
    category: 'news',
    subtype: 'headline',
    source_id: 'bbc_world',
    title: `Headline ${id}`,
    summary: null,
    url: `https://example.com/${id}`,
    point: null,
    country_iso: null,
    geo_confidence: 'none',
    reliability: 'F',
    credibility: 6,
    grade: 'F6',
    grade_rationale: 'Headline only.',
    ...overrides,
  });
}

function serve(items: LiveEvent[]) {
  server.use(http.get('/api/events', () => HttpResponse.json({ items, count: items.length })));
}

function Harness({
  country = null,
  hours = 24,
  enabled = false,
  onSelect = vi.fn(),
}: {
  country?: string | null;
  hours?: number | null;
  enabled?: boolean;
  onSelect?: (event: LiveEvent) => void;
}) {
  const filters = useNewsFilters([], enabled);
  return (
    <MemoryRouter>
      <NewsPanel filters={filters} country={country} windowHours={hours} onSelect={onSelect} />
    </MemoryRouter>
  );
}

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

const headings = () =>
  within(screen.getByRole('list', { name: 'News stories' })).queryAllByRole('heading', {
    level: 3,
  });
beforeEach(() => useAuthStore.getState().setSession(tokenFor(plainUser)));
afterEach(() => vi.restoreAllMocks());

it('keeps unlocated and country-only evidence readable with the map master off', async () => {
  const unlocated = article('unlocated', { published_at: null });
  const country = article('country', {
    country_iso: 'GB',
    geo_confidence: 'country',
    point: { lon: -2.9, lat: 54.3 },
  });
  const city = article('city', {
    country_iso: 'GB',
    geo_confidence: 'city',
    point: { lon: -0.12, lat: 51.5 },
  });
  serve([unlocated, country, city]);
  const onSelect = vi.fn();
  render(<Harness onSelect={onSelect} />);
  await screen.findByRole('heading', { name: 'Headline unlocated' });
  expect(screen.getByText(/News map layer is off/)).toBeInTheDocument();
  expect(screen.getByText(/Publication date unknown/)).toBeInTheDocument();
  expect(screen.getByText('Country only, no incident position')).toBeInTheDocument();
  expect(screen.getByText('Approximate city location')).toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: 'Inspect evidence' })).toHaveLength(2);
  const row = screen.getByRole('heading', { name: 'Headline unlocated' }).closest('li')!;
  fireEvent.click(within(row).getByRole('button', { name: 'Inspect evidence' }));
  expect(onSelect).toHaveBeenLastCalledWith(unlocated);
  expect(onSelect.mock.lastCall?.[0]).toMatchObject({
    point: null,
    country_iso: null,
    geo_confidence: 'none',
  });
  fireEvent.click(screen.getByRole('button', { name: 'Locate and inspect' }));
  expect(onSelect).toHaveBeenLastCalledWith(city);
  fireEvent.click(within(row).getByText('Source assessment · F6'));
  expect(within(row).getByText(/F or 6 means unassessed, not false/)).toBeVisible();
});

it('shows related publications as one story without presenting them as independent confirmation', async () => {
  const first = article('first', { story_id: 'same', source_id: 'bbc_world' });
  const lead = article('latest', {
    story_id: 'same',
    source_id: 'guardian_world',
    published_at: '2026-09-06T00:00:00Z',
  });
  serve([first, lead, article('separate')]);
  render(<Harness />);
  await screen.findByRole('heading', { name: 'Headline latest' });
  expect(headings()).toHaveLength(2);
  expect(screen.getByText(/2 matching stories from 2 source feeds/)).toBeInTheDocument();
  expect(screen.getByText(/grouped, not counted as independent confirmation/)).toBeInTheDocument();
  expect(screen.getByText(/2 related reports/)).toBeInTheDocument();
  const row = screen.getByRole('heading', { name: 'Headline latest' }).closest('li')!;
  fireEvent.click(within(row).getByText('Source assessment · F6'));
  const related = within(row).getByText('bbc world: Headline first').closest('li')!;
  expect(within(related).getByRole('link', { name: 'Read source' })).toHaveAttribute(
    'href',
    first.url,
  );
  expect(within(row).getByRole('link', { name: 'Research story' }).getAttribute('href')).toContain(
    'question=Assess',
  );
});

it.each([null, 'javascript:alert(1)', 'https://name:password@example.com/news'])(
  'preserves headline text without creating an unsafe link for URL %s',
  async (url) => {
    serve([
      article('plain', { url, story_id: 'same' }),
      article('related', { url, story_id: 'same', published_at: '2026-09-04T00:00:00Z' }),
    ]);
    render(<Harness />);
    const headline = await screen.findByRole('heading', { name: 'Headline plain' });
    const row = headline.closest('li')!;
    fireEvent.click(within(row).getByText('Source assessment · F6'));
    expect(within(row).getByText('bbc world: Headline related')).toBeVisible();
    expect(within(row).queryByRole('link', { name: 'Read source' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Inspect evidence' })).toBeEnabled();
  },
);

it('combines publisher, text and subject choices, and clearing restores readable default news', async () => {
  serve([
    article('port', { title: 'Port talks resume' }),
    article('rain', { source_id: 'guardian_world', title: 'Rain forecast' }),
    article('policy', { category: 'political', title: 'Budget policy agreed' }),
  ]);
  render(<Harness />);
  await screen.findByRole('heading', { name: 'Port talks resume' });
  expect(headings()).toHaveLength(2);
  fireEvent.change(screen.getByLabelText('Publisher'), { target: { value: 'guardian_world' } });
  expect(headings()).toHaveLength(1);
  expect(screen.getByRole('heading', { name: 'Rain forecast' })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Search headlines'), { target: { value: 'PORT' } });
  expect(screen.getByText(/No headlines match/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Clear news filters' }));
  expect(headings()).toHaveLength(2);
  fireEvent.click(screen.getByText('News subjects'));
  fireEvent.click(screen.getByRole('checkbox', { name: 'General news' }));
  expect(headings()).toHaveLength(0);
  fireEvent.click(screen.getByRole('checkbox', { name: 'Politics and policy' }));
  expect(headings()).toHaveLength(1);
  expect(screen.getByRole('heading', { name: 'Budget policy agreed' })).toBeInTheDocument();
  expect(screen.getByText(/News map layer is off/)).toBeInTheDocument();
});

it('bounds snapshots to 300 records and reveals headlines in batches of 15', async () => {
  serve(Array.from({ length: 305 }, (_, index) => article(String(index + 1))));
  render(<Harness />);
  await screen.findByRole('heading', { name: 'Headline 1' });
  expect(headings()).toHaveLength(15);
  expect(screen.getByText(/300 matching stories/)).toBeInTheDocument();
  expect(screen.getByText(/snapshot reached its limit/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Show more headlines' }));
  expect(headings()).toHaveLength(30);
  fireEvent.change(screen.getByLabelText('Search headlines'), {
    target: { value: 'Headline 305' },
  });
  expect(headings()).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: 'Clear news filters' }));
  expect(headings()).toHaveLength(15);
});

it('passes the selected nation and publication interval to the API and hides the old scope immediately', async () => {
  vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-09-13T12:00:00Z'));
  const next = deferred();
  const requests: URL[] = [];
  server.use(
    http.get('/api/events', async ({ request }) => {
      requests.push(new URL(request.url));
      if (requests.length > 1) await next.promise;
      return HttpResponse.json({
        items: [article(requests.length === 1 ? 'GB' : 'world')],
        count: 1,
      });
    }),
  );
  const view = render(<Harness country="GB" hours={48} />);
  await screen.findByRole('heading', { name: 'Headline GB' });
  expect(Object.fromEntries(requests[0]!.searchParams)).toEqual({
    categories: 'news,political,humanitarian,economic,social',
    limit: '300',
    country: 'GB',
    since: '2026-09-11T12:00:00.000Z',
  });
  view.rerender(<Harness country={null} hours={48} />);
  expect(screen.queryByRole('heading', { name: 'Headline GB' })).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toHaveTextContent('Loading retained news');
  await waitFor(() => expect(requests).toHaveLength(2));
  expect(Object.fromEntries(requests[1]!.searchParams)).toEqual({
    categories: 'news,political,humanitarian,economic,social',
    limit: '300',
    since: '2026-09-11T12:00:00.000Z',
  });
  await act(async () => {
    next.resolve();
    await next.promise;
  });
  await screen.findByRole('heading', { name: 'Headline world' });
  view.rerender(<Harness country={null} hours={null} />);
  expect(screen.queryByRole('heading', { name: 'Headline world' })).not.toBeInTheDocument();
  await screen.findByRole('heading', { name: 'Headline world' });
  expect(Object.fromEntries(requests[2]!.searchParams)).toEqual({
    categories: 'news,political,humanitarian,economic,social',
    limit: '300',
  });
});

it.each(['access', 'identity'] as const)(
  'immediately removes already displayed headlines after an %s change',
  async (change) => {
    const pending = deferred();
    let calls = 0;
    server.use(
      http.get('/api/events', async () => {
        calls += 1;
        if (calls === 1) return HttpResponse.json({ items: [article('previous')], count: 1 });
        await pending.promise;
        return HttpResponse.json({ items: [], count: 0 });
      }),
    );
    render(<Harness />);
    await screen.findByRole('heading', { name: 'Headline previous' });
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    expect(screen.queryByRole('list', { name: 'News stories' })).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Loading retained news');
    await act(async () => {
      pending.resolve();
      await pending.promise;
    });
    await screen.findByText(/No headlines match/);
    expect(screen.queryByText('Headline previous')).not.toBeInTheDocument();
  },
);

it.each(['access', 'identity'] as const)(
  'hides previous headlines on %s changes and rejects late refresh results',
  async (change) => {
    const late = deferred();
    const finished = deferred();
    const requests: Request[] = [];
    server.use(
      http.get('/api/events', async ({ request }) => {
        requests.push(request);
        if (requests.length === 2) {
          await late.promise;
          finished.resolve();
          return HttpResponse.json({ items: [article('stale')], count: 1 });
        }
        if (requests.length > 2)
          return HttpResponse.json(
            { error: { code: 'forbidden', message: 'News access removed.', fields: {} } },
            { status: 403 },
          );
        return HttpResponse.json({ items: [article('previous')], count: 1 });
      }),
    );
    render(<Harness />);
    await screen.findByRole('heading', { name: 'Headline previous' });
    fireEvent.click(screen.getByRole('button', { name: 'Refresh headlines' }));
    await waitFor(() => expect(requests).toHaveLength(2));
    act(() => {
      if (change === 'access') invalidateWorkspaceAccess();
      else useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    expect(screen.queryByRole('list', { name: 'News stories' })).not.toBeInTheDocument();
    expect(requests[1]!.signal.aborted).toBe(true);
    expect(await screen.findByRole('alert')).toHaveTextContent('News access removed.');
    await act(async () => {
      late.resolve();
      await finished.promise;
    });
    expect(screen.queryByRole('list', { name: 'News stories' })).not.toBeInTheDocument();
    expect(screen.queryByText('Headline stale')).not.toBeInTheDocument();
    expect(requests).toHaveLength(3);
  },
);

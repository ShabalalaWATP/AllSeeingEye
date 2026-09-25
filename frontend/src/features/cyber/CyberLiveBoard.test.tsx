import { screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { parseCyberDays } from '@/lib/api/cyber';
import { cyberBoard } from '@/test/fixtures';
import { cyberActors, cyberBriefing, cyberSnapshot } from '@/test/fixtures.cyber';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
  server.use(
    http.get('/api/cyber', ({ request }) =>
      HttpResponse.json(
        cyberSnapshot(parseCyberDays(new URL(request.url).searchParams.get('days'))),
      ),
    ),
    http.get('/api/cyber/actors', () => HttpResponse.json(cyberActors)),
    http.post('/api/cyber/briefing', ({ request }) =>
      HttpResponse.json(
        cyberBriefing(parseCyberDays(new URL(request.url).searchParams.get('days'))),
      ),
    ),
  );
});

function liveSection() {
  return screen.getByRole('region', { name: 'Outages and ransomware claims now' });
}

describe('cyber live board', () => {
  it('shows the fixed-window outage and ransomware tallies inside the cyber workspace', async () => {
    renderApp('/cyber', 'user');
    const figures = await screen.findByRole('list', { name: 'Live cyber figures' });
    expect(within(figures).getByText('Outage alerts, last 24 hours')).toBeVisible();
    expect(within(figures).getByText('Ransomware claims, last 7 days')).toBeVisible();
    const section = within(liveSection());
    expect(
      within(section.getByRole('list', { name: 'Outage alerts by nation' })).getByText('Tunisia'),
    ).toBeVisible();
    expect(
      within(section.getByRole('list', { name: 'Ransomware claims by group' })).getByText('akira'),
    ).toBeVisible();
    expect(
      within(section.getByRole('list', { name: 'Ransomware claims by nation' })).getByText(
        'United States',
      ),
    ).toBeVisible();
    // The old tracker board duplicated the exploited-vulnerability list; it stays in one place.
    expect(section.queryByText(/CVE-2026-0001/)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Live board' })).toHaveAttribute('href', '#cyber-live');
  });

  it('states empty windows and unnamed groups or places plainly', async () => {
    server.use(
      http.get('/api/trackers/cyber', () =>
        HttpResponse.json({
          ...cyberBoard,
          outages_24h: 0,
          outages_by_country: [],
          ransomware_by_group: [{ key: '', count: 2, max_severity: null }],
          ransomware_by_country: [{ key: '', count: 2, max_severity: null }],
        }),
      ),
    );
    renderApp('/cyber', 'user');
    await screen.findByRole('list', { name: 'Live cyber figures' });
    const section = within(liveSection());
    expect(section.getByText('No outage alerts in the last 24 hours.')).toBeVisible();
    expect(section.getByText('Group not stated')).toBeVisible();
    expect(section.getByText('Location not established')).toBeVisible();
  });

  it('reports a failed board and recovers on retry', async () => {
    let calls = 0;
    server.use(
      http.get('/api/trackers/cyber', () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(
              { error: { code: 'unavailable', message: 'Live board unavailable.' } },
              { status: 503 },
            )
          : HttpResponse.json(cyberBoard);
      }),
    );
    const { user } = renderApp('/cyber', 'user');
    const retry = await screen.findByRole('button', { name: 'Retry live board' });
    await user.click(retry);
    expect(await screen.findByRole('list', { name: 'Live cyber figures' })).toBeVisible();
    expect(calls).toBe(2);
  });

  it('says the board is loading while the request is outstanding', async () => {
    server.use(
      http.get('/api/trackers/cyber', async () => {
        await delay('infinite');
        return HttpResponse.json(cyberBoard);
      }),
    );
    renderApp('/cyber', 'user');
    expect(await screen.findByText('Loading the live cyber board')).toBeVisible();
  });

  it('redirects the retired tracker board to the cyber workspace, keeping the query', async () => {
    const { router } = renderApp('/trackers/cyber?days=7', 'user');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/cyber');
    });
    expect(router.state.location.search).toBe('?days=7');
    expect(await screen.findByRole('list', { name: 'Live cyber figures' })).toBeVisible();
  });
});

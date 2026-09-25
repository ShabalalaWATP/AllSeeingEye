import { screen, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { areaIndicator, briefSummary, watchHandlers } from '@/test/handlers.watches';
import { plan } from '@/test/fixtures.direction';
import { annotationMonitor } from '@/test/fixtures.monitors';
import { schedule } from '@/test/fixtures.schedules';
import { indicator } from '@/test/fixtures.warning';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function card(title: string) {
  return within(screen.getByRole('region', { name: title }));
}

describe('watches hub', () => {
  it('summarises every kind of watch with links to each item and its full page', async () => {
    server.use(...watchHandlers);
    renderApp('/watches', 'user');
    expect(await screen.findByRole('heading', { name: 'Watches', level: 1 })).toBeVisible();
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Watches' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    const subscriptions = card('Subscriptions');
    expect(await subscriptions.findByRole('link', { name: schedule.name })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
    expect(subscriptions.getByText('1 total')).toBeVisible();
    expect(subscriptions.getByText(/Personal · next run/)).toBeVisible();
    expect(subscriptions.getByRole('link', { name: 'Open subscriptions' })).toHaveAttribute(
      'href',
      '/subscriptions',
    );

    const rules = card('Alert rules');
    expect(await rules.findByRole('link', { name: indicator.name })).toHaveAttribute(
      'href',
      '/warning',
    );
    expect(rules.getByText('Personal · 2 or more in 6 h')).toBeVisible();
    expect(rules.queryByText(areaIndicator.name)).not.toBeInTheDocument();

    const areas = card('Area watches');
    expect(areas.getByRole('link', { name: areaIndicator.name })).toHaveAttribute(
      'href',
      '/warning',
    );
    expect(areas.getByText('Personal · map rectangle')).toBeVisible();

    expect(await card('Collection plans').findByRole('link', { name: plan.name })).toHaveAttribute(
      'href',
      `/direction/plans/${plan.id}`,
    );
    expect(
      await card('Research briefs').findByRole('link', { name: briefSummary.title }),
    ).toHaveAttribute('href', `/research?brief=${briefSummary.id}&revision=4`);
    const monitors = card('Annotation monitors');
    expect(await monitors.findByRole('link', { name: annotationMonitor.name })).toHaveAttribute(
      'href',
      `/annotation-monitors/${annotationMonitor.id}`,
    );
    expect(monitors.getByText('Personal · active')).toBeVisible();
    expect(monitors.getByRole('link', { name: 'Open annotation monitors' })).toHaveAttribute(
      'href',
      '/annotation-monitors',
    );
  });

  it('says plainly when there is nothing to watch yet', async () => {
    server.use(
      http.get('/api/schedules', () => HttpResponse.json({ items: [] })),
      http.get('/api/warning/indicators', () => HttpResponse.json({ items: [] })),
      http.get('/api/direction/plans', () => HttpResponse.json({ items: [] })),
      http.get('/api/research/briefs', () =>
        HttpResponse.json({ items: [], limit: 50, offset: 0 }),
      ),
      http.get('/api/annotation-monitors', () =>
        HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 }),
      ),
    );
    renderApp('/watches', 'user');
    expect(await screen.findByText('No subscriptions yet.')).toBeVisible();
    expect(await screen.findByText('No alert rules yet.')).toBeVisible();
    expect(screen.getByText(/No area watches yet/)).toBeVisible();
    expect(await screen.findByText('No collection plans yet.')).toBeVisible();
    expect(await screen.findByText('No saved briefs yet.')).toBeVisible();
    expect(await screen.findByText('No annotation monitors yet.')).toBeVisible();
    expect(card('Subscriptions').getByText('0 total')).toBeVisible();
  });

  it('keeps other cards working when one list fails, and retries it', async () => {
    let calls = 0;
    server.use(
      ...watchHandlers,
      http.get('/api/schedules', () => {
        calls += 1;
        return calls === 1
          ? apiError(503, 'unavailable', 'Subscriptions are unavailable.')
          : HttpResponse.json({ items: [schedule] });
      }),
    );
    const { user } = renderApp('/watches', 'user');
    await screen.findByRole('heading', { name: 'Watches', level: 1 });
    const subscriptions = card('Subscriptions');
    expect(await subscriptions.findByText(/Subscriptions are unavailable/)).toBeVisible();
    expect(await card('Collection plans').findByRole('link', { name: plan.name })).toBeVisible();
    await user.click(subscriptions.getByRole('button', { name: 'Retry subscriptions' }));
    expect(await subscriptions.findByRole('link', { name: schedule.name })).toBeVisible();
    expect(calls).toBe(2);
  });

  it('shows loading states and marks a full page of briefs as possibly more', async () => {
    const briefs = Array.from({ length: 50 }, (_, index) => ({
      ...briefSummary,
      id: `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
      title: `Brief ${String(index)}`,
      revised_at: `2026-09-${String(10 + (index % 10)).padStart(2, '0')}T10:00:00Z`,
    }));
    // The first matching handler wins, so these overrides come before the shared ones.
    server.use(
      http.get('/api/research/briefs', () =>
        HttpResponse.json({ items: briefs, limit: 50, offset: 0 }),
      ),
      http.get('/api/annotation-monitors', async () => {
        await delay('infinite');
        return HttpResponse.json({ items: [], total: 0, offset: 0, limit: 20 });
      }),
      ...watchHandlers,
    );
    renderApp('/watches', 'user');
    expect(await screen.findByText('Loading annotation monitors')).toBeVisible();
    const brief = card('Research briefs');
    expect(await brief.findByText('50+ total')).toBeVisible();
    expect(
      within(brief.getByRole('list', { name: 'Latest research briefs' })).getAllByRole('listitem'),
    ).toHaveLength(3);
  });
});

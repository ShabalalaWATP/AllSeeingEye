import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('research workspace navigation', () => {
  it('redirects old photo links to the standalone geolocation workspace', async () => {
    const { router } = renderApp('/research/photo', 'user');
    await screen.findByRole('heading', { name: 'Geolocation' });
    expect(router.state.location.pathname).toBe('/geolocation');
    expect(screen.queryByRole('navigation', { name: 'Research tools' })).not.toBeInTheDocument();
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Geolocation' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(primary).getByRole('link', { name: 'Research' })).not.toHaveAttribute(
      'aria-current',
    );
  });
  it('gives reusable plans their own rail entry and exposes the next research tools', async () => {
    renderApp('/direction', 'user');
    await screen.findByRole('heading', { name: 'Plans & areas' });
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Plans & areas' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(primary).getByRole('link', { name: 'Research' })).not.toHaveAttribute(
      'aria-current',
    );
    const tools = screen.getByRole('navigation', { name: 'Research tools' });
    expect(within(tools).getByRole('link', { name: 'Saved reports' })).toHaveAttribute(
      'href',
      '/reports',
    );
    expect(within(tools).queryByRole('link', { name: /Geolocat/ })).not.toBeInTheDocument();
    expect(within(primary).getByRole('link', { name: 'Geolocation' })).toHaveAttribute(
      'href',
      '/geolocation',
    );
    expect(within(tools).queryByRole('link', { name: 'Recurring' })).not.toBeInTheDocument();
    expect(within(primary).getByRole('link', { name: 'Subscriptions' })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
    expect(within(tools).getByRole('link', { name: 'Daily briefing' })).toHaveAttribute(
      'href',
      '/trackers',
    );
  });

  it('does not load feed boards or create a competing generation form when browsing saved reports', async () => {
    const boardRequest = vi.fn(() => HttpResponse.json({ items: [] }));
    server.use(
      http.get('/api/trackers/conflicts', boardRequest),
      http.get('/api/trackers/disasters', boardRequest),
    );
    renderApp('/reports', 'user');
    await screen.findByRole('table', { name: 'Reports' });
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Saved reports' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.queryByRole('form', { name: 'Generate a report' })).not.toBeInTheDocument();
    expect(boardRequest).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: 'Research progress' })).toHaveAttribute(
      'href',
      '/research/jobs',
    );
    expect(screen.getByRole('link', { name: 'Manage subscriptions' })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
  });

  it('preserves old subscription links while displaying the shorter destination name', async () => {
    const { router } = renderApp('/research/recurring?scope=personal', 'user');
    await screen.findByRole('heading', { name: 'Subscriptions', level: 1 });
    expect(router.state.location.pathname).toBe('/subscriptions');
    expect(router.state.location.search).toBe('?scope=personal');
    expect(screen.queryByRole('navigation', { name: 'Research tools' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Subscriptions' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });
});

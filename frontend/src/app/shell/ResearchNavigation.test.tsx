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
  it('lists plans with the other standing watches and drops research tabs from the page', async () => {
    renderApp('/direction', 'user');
    await screen.findByRole('heading', { name: 'Plans and areas' });
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Plans and areas' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(primary).getByRole('link', { name: 'Watches' })).not.toHaveAttribute(
      'aria-current',
    );
    // Plans are not research, so New research and Saved research tabs do not appear here.
    expect(screen.queryByRole('navigation', { name: 'Research tools' })).not.toBeInTheDocument();
    expect(within(primary).getByRole('link', { name: 'Geolocation' })).toHaveAttribute(
      'href',
      '/geolocation',
    );
    expect(within(primary).getByRole('link', { name: 'Subscriptions' })).toHaveAttribute(
      'href',
      '/subscriptions',
    );
  });

  it('marks only the most specific rail entry as current', async () => {
    renderApp('/research/jobs', 'user');
    await screen.findByRole('heading', { name: 'Research progress', level: 1 });
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Research progress' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(primary).getByRole('link', { name: 'Research' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('does not load feed boards or create a competing generation form when browsing saved reports', async () => {
    const boardRequest = vi.fn(() => HttpResponse.json({ items: [] }));
    server.use(
      http.get('/api/trackers/conflicts', boardRequest),
      http.get('/api/trackers/disasters', boardRequest),
    );
    renderApp('/research/saved', 'user');
    await screen.findByRole('table', { name: 'Saved research' });
    // Research owns its saved answers now, so the rail still points at Research.
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Research' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    const tabs = screen.getByRole('navigation', { name: 'Research' });
    expect(within(tabs).getByRole('link', { name: 'Saved research' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.queryByRole('form', { name: 'Generate a report' })).not.toBeInTheDocument();
    expect(boardRequest).not.toHaveBeenCalled();
    expect(
      within(screen.getByRole('main')).getByRole('link', { name: 'Research progress' }),
    ).toHaveAttribute('href', '/research/jobs');
  });

  it('preserves old subscription links while displaying the shorter destination name', async () => {
    const { router } = renderApp('/research/recurring?scope=personal', 'user');
    await screen.findByRole('heading', { name: 'Subscriptions', level: 1 });
    expect(router.state.location.pathname).toBe('/subscriptions');
    expect(router.state.location.search).toBe('?scope=personal');
    expect(screen.queryByRole('navigation', { name: 'Research tools' })).not.toBeInTheDocument();
    // The rail entry and the section's own first tab both name this destination.
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Subscriptions' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    const tabs = screen.getByRole('navigation', { name: 'Subscriptions' });
    expect(within(tabs).getByRole('link', { name: 'Saved updates' })).toHaveAttribute(
      'href',
      '/subscriptions/saved',
    );
  });
});

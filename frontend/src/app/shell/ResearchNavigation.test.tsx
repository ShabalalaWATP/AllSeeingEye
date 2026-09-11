import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('research workspace navigation', () => {
  it('keeps reusable plans under Research and exposes the next research tools', async () => {
    renderApp('/direction', 'user');
    await screen.findByRole('heading', { name: 'Plans & areas' });
    const primary = screen.getByRole('navigation', { name: 'Primary' });
    expect(within(primary).getByRole('link', { name: 'Research' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    const tools = screen.getByRole('navigation', { name: 'Research tools' });
    expect(within(tools).getByRole('link', { name: 'Jobs' })).toHaveAttribute(
      'href',
      '/research/jobs',
    );
    expect(within(tools).getByRole('link', { name: 'Geolocate a photo' })).toHaveAttribute(
      'href',
      '/research/photo',
    );
    expect(within(tools).getByRole('link', { name: 'Recurring' })).toHaveAttribute(
      'href',
      '/research/recurring',
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
    expect(screen.queryByRole('form', { name: 'Generate a report' })).not.toBeInTheDocument();
    expect(boardRequest).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: 'Manage recurring research' })).toHaveAttribute(
      'href',
      '/research/recurring',
    );
  });
});

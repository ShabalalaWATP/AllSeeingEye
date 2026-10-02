import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { server } from '@/test/server';
import { PrivateFeedSettings } from './PrivateFeedSettings';

describe('private feed settings', () => {
  it('requires explicit opt-in, displays a token once and supports revocation', async () => {
    let enabled = false;
    let titles = false;
    server.use(
      http.get('/api/me/notifications/feed', () =>
        HttpResponse.json({
          enabled,
          include_titles: titles,
          created_at: null,
        }),
      ),
      http.post('/api/me/notifications/feed', async ({ request }) => {
        const body = (await request.json()) as { include_titles: boolean };
        enabled = true;
        titles = body.include_titles;
        return HttpResponse.json({
          token: 'test-feed-token',
          feed_url: 'https://app.test/api/notifications/feed.atom',
          username: 'feed',
        });
      }),
      http.delete('/api/me/notifications/feed', () => {
        enabled = false;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = userEvent.setup();
    render(<PrivateFeedSettings />);
    expect(await screen.findByText('Feed disabled')).toBeVisible();
    expect(screen.queryByLabelText('Feed password')).not.toBeInTheDocument();
    await user.click(screen.getByLabelText(/Include alert and subscription titles/));
    await user.click(screen.getByRole('button', { name: 'Enable feed' }));
    expect(await screen.findByLabelText('Feed password')).toHaveValue('test-feed-token');
    expect(titles).toBe(true);
    await user.click(screen.getByRole('button', { name: 'Hide token' }));
    expect(screen.queryByLabelText('Feed password')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Revoke feed token' }));
    expect(await screen.findByText('Feed disabled')).toBeVisible();
  });

  it('shows load errors without a working enable control', async () => {
    server.use(
      http.get('/api/me/notifications/feed', () => new HttpResponse(null, { status: 503 })),
    );
    render(<PrivateFeedSettings />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Feed settings could not be loaded');
    expect(screen.queryByRole('button', { name: 'Enable feed' })).not.toBeInTheDocument();
  });
});

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { installDialogStub } from '@/test/dialogStub';
import { server } from '@/test/server';
import { PrivateFeedSettings } from './PrivateFeedSettings';

installDialogStub();

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
    expect(screen.getByLabelText(/when the token is replaced/)).toBeChecked();

    await user.click(screen.getByRole('button', { name: 'Replace feed token' }));
    const replace = await screen.findByRole('alertdialog', {
      name: 'Replace the private feed token?',
    });
    expect(replace).toHaveTextContent('The old token stops working immediately');
    expect(replace).toHaveTextContent('Titles will be included');
    await user.click(within(replace).getByRole('button', { name: 'Replace token' }));
    expect(await screen.findByLabelText('Feed password')).toHaveValue('test-feed-token');
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Revoke feed token' }));
    const revoke = await screen.findByRole('alertdialog', {
      name: 'Revoke the private feed token?',
    });
    expect(revoke).toHaveTextContent('stops working immediately');
    await user.click(within(revoke).getByRole('button', { name: 'Cancel' }));
    expect(screen.getByText('Feed enabled')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Revoke feed token' }));
    await user.click(
      within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Revoke token' }),
    );
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

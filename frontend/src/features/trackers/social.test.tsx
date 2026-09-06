import { act, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { delay, http, HttpResponse } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { SocialBoard, SocialKeyword } from '@/lib/api/social';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { roster, team } from '@/test/fixtures.teams';
import { applySession } from '@/test/render';
import { server } from '@/test/server';

import SocialPage from './SocialPage';
import { describeSocialActivity } from './useSocialBoard';

const empty: SocialBoard = {
  total: 0,
  located: 0,
  platforms: [],
  hashtags: [],
  keywords: [],
  posts: [],
  window_start: '2026-09-04T12:00:00Z',
  window_end: '2026-09-05T12:00:00Z',
  keyword_hour: '2026-09-05T11:00:00Z',
};

const keyword: SocialKeyword = {
  term: 'ukraine',
  count: 4,
  baseline: 2,
  baseline_hours: 8,
  ratio: 2,
  burst: true,
};

function renderBoard() {
  applySession('user');
  const router = createMemoryRouter(
    [
      { path: '/trackers/social', element: <SocialPage /> },
      { path: '/', element: <p>Globe canvas</p> },
    ],
    { initialEntries: ['/trackers/social'] },
  );
  return { ...render(<RouterProvider router={router} />), user: userEvent.setup() };
}

describe('social listening', () => {
  it('hides private collection keywords while a revoked workspace is rechecked', async () => {
    let revoked = false;
    let rosterReads = 0;
    let release!: () => void;
    const response = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get('/api/teams', () => HttpResponse.json({ items: revoked ? [] : [team] })),
      http.get('/api/teams/:id', () => {
        rosterReads += 1;
        return HttpResponse.json(roster);
      }),
      http.get('/api/trackers/social', async () => {
        if (revoked) {
          await response;
          return HttpResponse.json(empty);
        }
        return HttpResponse.json({
          ...empty,
          keywords: [{ ...keyword, term: 'private team term' }],
        });
      }),
    );
    renderBoard();
    expect(await screen.findByText('private team term')).toBeInTheDocument();
    await waitFor(() => expect(rosterReads).toBe(1));
    await act(async () => {
      await Promise.resolve();
    });
    revoked = true;
    act(() => {
      window.dispatchEvent(new Event('focus'));
    });
    await waitFor(() => expect(screen.queryByText('private team term')).not.toBeInTheDocument());
    expect(screen.getByRole('status')).toHaveTextContent('Loading social listening');
    await act(async () => {
      release();
      await response;
    });
    expect(
      await screen.findByText('No configured keywords are being sampled.'),
    ).toBeInTheDocument();
  });

  it('shows loading and empty states', async () => {
    server.use(
      http.get('/api/trackers/social', async () => {
        await delay(20);
        return HttpResponse.json(empty);
      }),
    );
    renderBoard();
    expect(screen.getByRole('status')).toHaveTextContent('Loading social listening');
    expect(await screen.findByText('No social posts in the retained day.')).toBeInTheDocument();
    expect(screen.getByText('No hashtags in retained posts.')).toBeInTheDocument();
    expect(screen.getByText('No configured keywords are being sampled.')).toBeInTheDocument();
    expect(screen.getByText('No recent posts to display.')).toBeInTheDocument();
  });

  it('shows safe errors and can retry', async () => {
    server.use(
      http.get('/api/trackers/social', () =>
        HttpResponse.json(
          { error: { code: 'unavailable', message: 'Social board unavailable.', fields: {} } },
          { status: 503 },
        ),
      ),
    );
    const { user } = renderBoard();
    expect(await screen.findByRole('alert')).toHaveTextContent('Social board unavailable.');
    server.use(http.get('/api/trackers/social', () => HttpResponse.json(empty)));
    await user.click(screen.getByRole('button', { name: 'Refresh' }));
    expect(await screen.findByText('No recent posts to display.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows platform totals, hashtags, baseline states and translated posts', async () => {
    const data: SocialBoard = {
      ...empty,
      total: 2,
      located: 1,
      platforms: [{ platform: 'mastodon', instance: 'mastodon.social', count: 2, located: 1 }],
      hashtags: [{ tag: 'ukraine', count: 2 }],
      keywords: [
        keyword,
        {
          ...keyword,
          term: 'taiwan',
          baseline: null,
          ratio: null,
          burst: false,
          baseline_hours: 0,
        },
      ],
      posts: [
        liveEvent({
          id: 'post',
          category: 'social',
          title: 'Original title',
          title_en: 'Translated post',
        }),
      ],
    };
    server.use(http.get('/api/trackers/social', () => HttpResponse.json(data)));
    renderBoard();
    const platforms = await screen.findByRole('table', { name: 'Posts by platform and instance' });
    expect(within(platforms).getByText('mastodon.social')).toBeInTheDocument();
    expect(screen.getByText('#ukraine')).toBeInTheDocument();
    expect(screen.getByText('Burst: 2.0× baseline')).toBeInTheDocument();
    expect(screen.getByText('No baseline yet')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Translated post' })).toHaveAttribute(
      'href',
      'https://example.com/e1',
    );
  });

  it.each([true, false])('opens the existing social globe layer, hidden=%s', async (hidden) => {
    server.use(http.get('/api/trackers/social', () => HttpResponse.json(empty)));
    useEventsStore.setState({
      hidden: hidden ? ['social', 'aviation'] : ['aviation'],
      country: 'UA',
      windowHours: 1,
    });
    const { user } = renderBoard();
    await user.click(screen.getByRole('button', { name: 'Show social layer on globe' }));
    expect(await screen.findByText('Globe canvas')).toBeInTheDocument();
    expect(useEventsStore.getState().hidden).toEqual(['aviation']);
    expect(useEventsStore.getState().country).toBeNull();
    expect(useEventsStore.getState().windowHours).toBe(24);
  });

  it('distinguishes insufficient history, quiet hours and newly active terms', () => {
    expect(describeSocialActivity({ ...keyword, baseline_hours: 2 })).toBe('Building baseline');
    expect(describeSocialActivity({ ...keyword, burst: false })).toBe('No burst');
    expect(describeSocialActivity({ ...keyword, baseline: 0, ratio: null })).toBe(
      'Burst: new activity',
    );
  });
});

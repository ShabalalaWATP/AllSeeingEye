import { act, screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { User } from '@/lib/api/schemas';
import type { CatalogueSource } from '@/lib/api/sourceContext';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { sourceContext } from '@/test/fixtures.researchMetadata';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const waiting: CatalogueSource = {
  ...sourceContext,
  id: 'quiet_feed',
  name: 'Quiet feed',
  connection: { ...sourceContext.connection, state: 'idle', health: null },
};
const unverifiedKey: CatalogueSource = {
  ...sourceContext,
  id: 'keyed_feed',
  name: 'Keyed feed',
  requires_key: true,
  connection: {
    ...sourceContext.connection,
    state: 'key_unverified',
    health: null,
    requirement: {
      kind: 'api_key',
      satisfied: true,
      origin: 'environment',
      setting: 'ASE_KEYED_FEED_KEY',
      note: 'Key set on the server.',
      optional: false,
    },
  },
};
const unassessed: CatalogueSource = {
  ...sourceContext,
  id: 'new_feed',
  name: 'New feed',
  reliability: 'C',
  rating: {
    ...sourceContext.rating,
    status: 'unassessed',
    assessed_grade: null,
    basis: 'No editorial review has been recorded for this source.',
    limitations: ['The configured letter is a collection default, not a judgement.'],
  },
};

const MANAGER: User = {
  ...plainUser,
  id: '33333333-3333-4333-8333-333333333333',
  role: 'manager',
};

function serve(items: CatalogueSource[]) {
  server.use(http.get('/api/sources', () => HttpResponse.json({ items })));
}

beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe('signed-in source catalogue', () => {
  it.each(['user', 'manager', 'admin'] as const)(
    'opens at /sources for a %s and filters without administrative controls',
    async (role) => {
      serve([sourceContext, unassessed]);
      const { router, user } = renderApp('/sources', role === 'admin' ? 'admin' : 'user');
      if (role === 'manager') act(() => useAuthStore.getState().setSession(tokenFor(MANAGER)));
      expect(await screen.findByRole('heading', { name: 'BBC World' })).toBeVisible();
      expect(router.state.location.pathname).toBe('/sources');
      const page = within(screen.getByRole('region', { name: 'Source catalogue' }));
      await user.selectOptions(page.getByLabelText('Topic'), 'news');
      expect(router.state.location.search).toBe('?topic=news');
      await user.click(page.getByRole('button', { name: 'Clear filters' }));
      expect(router.state.location.search).toBe('');
      expect(page.queryByRole('link', { name: /source controls/i })).toBeNull();
      expect(
        page.queryByRole('button', { name: /switch (on|off)|reset|test|enable|disable|save/i }),
      ).toBeNull();
      expect(page.queryByRole('textbox', { name: /key|password|secret/i })).toBeNull();
    },
  );

  it('sends a signed-out visitor through sign-in and back to the catalogue', async () => {
    const { router } = renderApp('/sources?family=feed', 'anonymous');
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/login');
    expect(router.state.location.state).toEqual({ from: '/sources?family=feed' });
  });

  it('keeps the administrator catalogue, which links to the source controls', async () => {
    serve([sourceContext]);
    const { router } = renderApp('/admin/catalogue', 'admin');
    expect(await screen.findByRole('heading', { name: 'BBC World' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/admin/catalogue');
    expect(screen.getByRole('link', { name: 'Open source controls' })).toHaveAttribute(
      'href',
      '/admin/sources',
    );
  });

  it('shows each grade with its recorded basis and never as an assessed grade when unassessed', async () => {
    serve([sourceContext, unassessed]);
    const { user } = renderApp('/sources', 'user');
    await screen.findByRole('heading', { name: 'New feed' });
    await user.click(screen.getByText('Source rating basis · Unassessed'));
    expect(
      screen.getByText('No editorial review has been recorded for this source.'),
    ).toBeVisible();
    expect(
      screen.getByText('The configured letter is a collection default, not a judgement.'),
    ).toBeVisible();
    expect(
      screen.getByText(/Configured reliability C, not an editorial assessment/),
    ).toBeInTheDocument();
    await user.click(screen.getByText('Source rating basis · Editorial B'));
    expect(screen.getByText('Individual claims require separate assessment.')).toBeVisible();
  });

  it('counts sources without a confirmed collection apart from live ones', async () => {
    serve([sourceContext, waiting, unverifiedKey]);
    const { user } = renderApp('/sources', 'user');
    await screen.findByRole('heading', { name: 'Quiet feed' });
    const totals = within(screen.getByRole('list', { name: 'Totals by state' }));
    expect(totals.getByRole('button', { name: /Live or available\s?1/ })).toBeVisible();
    expect(totals.getByRole('button', { name: /Not yet confirmed\s?2/ })).toBeVisible();
    await user.selectOptions(screen.getByLabelText('Connection'), 'unconfirmed');
    expect(screen.getByRole('heading', { name: 'Keyed feed' })).toBeVisible();
    expect(screen.queryByRole('heading', { name: 'BBC World' })).not.toBeInTheDocument();
  });

  it('keeps loading, empty, no-match and failure distinct, with a keyboard retry', async () => {
    let requests = 0;
    server.use(
      http.get('/api/sources', async () => {
        requests += 1;
        if (requests === 1) {
          await delay(50);
          return HttpResponse.json(
            { error: { code: 'unavailable', message: 'Catalogue unavailable.' } },
            { status: 503 },
          );
        }
        return HttpResponse.json({ items: requests === 2 ? [] : [sourceContext] });
      }),
    );
    const { user } = renderApp('/sources?q=nothing-matches', 'user');
    expect(await screen.findByText('Loading source catalogue')).toBeInTheDocument();
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Catalogue unavailable.');
    expect(screen.queryByText('No sources are registered.')).toBeNull();
    const retry = within(alert).getByRole('button', { name: 'Retry sources' });
    retry.focus();
    await user.keyboard('{Enter}');
    expect(await screen.findByText('No sources are registered.')).toBeVisible();
    expect(screen.queryByText('No sources match your search.')).toBeNull();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('offers a clear-filters action where nothing matches', async () => {
    serve([sourceContext]);
    const { user, router } = renderApp('/sources?q=nothing-matches', 'user');
    const empty = await screen.findByText('No sources match your search.');
    const panel = empty.parentElement!;
    within(panel).getByRole('button', { name: 'Clear all filters' }).focus();
    await user.keyboard('{Enter}');
    expect(router.state.location.search).toBe('');
    expect(screen.getByRole('heading', { name: 'BBC World' })).toBeVisible();
  });

  it('clears the account-scoped catalogue as soon as access changes', async () => {
    let requests = 0;
    server.use(
      http.get('/api/sources', async () => {
        requests += 1;
        if (requests > 1) await delay('infinite');
        return HttpResponse.json({ items: [sourceContext] });
      }),
    );
    const { router } = renderApp('/sources', 'user');
    await screen.findByRole('heading', { name: 'BBC World' });
    act(() => invalidateWorkspaceAccess());
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'BBC World' })).toBeNull());
    expect(screen.getByText('Loading source catalogue')).toBeInTheDocument();
    act(() => useAuthStore.getState().clearSession());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(screen.queryByText('BBC World')).toBeNull();
  });
});

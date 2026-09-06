import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { selectIsAdmin, useAuthStore } from '@/stores/auth';
import { useGlobeStore } from '@/stores/globe';
import { adminUser, tokenFor } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('dedicated administration area', () => {
  it('shows a settings directory without mounting research navigation, alerts or shortcuts', async () => {
    let researchCalls = 0;
    server.use(
      http.get('/api/warning/*', () => {
        researchCalls += 1;
        return HttpResponse.json({ items: [] });
      }),
    );
    const { user, router } = renderApp('/admin', 'admin');
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    const nav = screen.getByRole('navigation', { name: 'Administration' });
    expect(within(nav).getByRole('link', { name: 'Overview' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    for (const label of [
      'Account requests',
      'Users',
      'Teams',
      'AI connections',
      'Sources',
      'Audit log',
      'Security',
    ]) {
      expect(within(nav).getByRole('link', { name: label })).toBeInTheDocument();
      expect(
        within(screen.getByRole('main')).getByRole('link', { name: new RegExp(`^${label}`) }),
      ).toBeInTheDocument();
    }
    expect(screen.queryByRole('navigation', { name: 'Primary' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /^Alerts/ })).not.toBeInTheDocument();
    await user.keyboard('mgo');
    expect(router.state.location.pathname).toBe('/admin');
    expect(useGlobeStore.getState().mode).toBe('globe');
    expect(useGlobeStore.getState().opsRoom).toBe(false);
    expect(researchCalls).toBe(0);
    await user.tab();
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('main')).toHaveFocus();
    await user.click(screen.getByRole('link', { name: 'Return to research' }));
    expect(router.state.location.pathname).toBe('/');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
  });

  it('keeps team administration inside its shell and permits logout', async () => {
    const { user, router } = renderApp('/admin/teams', 'admin');
    await screen.findByRole('heading', { name: 'Teams', level: 1 });
    const nav = screen.getByRole('navigation', { name: 'Administration' });
    expect(within(nav).getByRole('link', { name: 'Teams' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(within(nav).getByRole('link', { name: 'Overview' })).not.toHaveAttribute('aria-current');
    await user.click(screen.getByRole('button', { name: 'Logout' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(screen.queryByRole('navigation', { name: 'Administration' })).not.toBeInTheDocument();
  });

  it.each(['/admin', '/admin/teams', '/admin/users', '/admin/llm'])(
    'blocks users and managers before mounting %s',
    async (path) => {
      let calls = 0;
      server.use(
        http.get('/api/admin/*', () => {
          calls += 1;
          return HttpResponse.json({ items: [] });
        }),
      );
      const { unmount } = renderApp(path, 'user');
      expect(await screen.findByRole('status')).toHaveTextContent('Admin access required');
      expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
      unmount();
      useAuthStore.getState().setSession(tokenFor({ ...adminUser, role: 'manager' }));
      renderApp(path, 'unknown');
      expect(await screen.findByRole('status')).toHaveTextContent('Admin access required');
      expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
      expect(calls).toBe(0);
    },
  );

  it.each([{ role: 'manager' as const }, { is_active: false }])(
    'unmounts the admin workspace when current access changes: %j',
    async (change) => {
      renderApp('/admin', 'admin');
      await screen.findByRole('heading', { name: 'Administration', level: 1 });
      act(() => {
        useAuthStore.getState().setSession(tokenFor({ ...adminUser, ...change }));
      });
      expect(screen.getByRole('status')).toHaveTextContent('Admin access required');
      expect(screen.queryByRole('heading', { name: 'Administration' })).not.toBeInTheDocument();
      expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    },
  );

  it('requires authenticated and active admin state even if a cached user remains', () => {
    useAuthStore.getState().setSession(tokenFor(adminUser));
    const state = useAuthStore.getState();
    expect(selectIsAdmin(state)).toBe(true);
    expect(selectIsAdmin({ ...state, status: 'anonymous' })).toBe(false);
    expect(selectIsAdmin({ ...state, status: 'unknown' })).toBe(false);
    expect(selectIsAdmin({ ...state, user: { ...adminUser, is_active: false } })).toBe(false);
  });
});

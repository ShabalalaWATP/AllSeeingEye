import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { defaultProfile } from '@/test/handlers.profile';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('personal settings', () => {
  it.each(['user', 'admin'] as const)(
    'gives %s personal settings and linked resources',
    async (session) => {
      renderApp('/settings', session);
      expect(await screen.findByRole('heading', { name: 'Settings' })).toBeVisible();
      expect(await screen.findByRole('radio', { name: /^Obsidian/ })).toBeChecked();
      expect(screen.getAllByRole('radio')).toHaveLength(8);
      expect(screen.getByRole('radio', { name: /^Midnight/ })).not.toBeChecked();
      // The rail also links to alerts, so scope these to the page itself. The source
      // catalogue is not here: it is an administrator's page.
      const page = within(screen.getByRole('main'));
      expect(page.queryByRole('link', { name: /Sources and connections/ })).toBeNull();
      expect(page.getByRole('link', { name: /Alerts & rules/ })).toHaveAttribute(
        'href',
        '/warning',
      );
      expect(page.getByRole('link', { name: 'Profile & teams' })).toHaveAttribute(
        'href',
        '/account',
      );
      expect(screen.getByRole('button', { name: 'Save appearance' })).toBeDisabled();
      expect(document.documentElement).toHaveAttribute('data-appearance', 'obsidian');
    },
  );

  it('requires a signed-in user', async () => {
    const { router } = renderApp('/settings', 'anonymous');
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/login');
    expect(document.documentElement).not.toHaveAttribute('data-appearance');
  });

  it('saves only personal appearance and applies reduced motion to the animated eye', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.patch('/api/me/profile', async ({ request }) => {
        const body = await request.json();
        bodies.push(body);
        return HttpResponse.json({ ...defaultProfile, ...(body as object) });
      }),
    );
    const { user } = renderApp('/settings', 'user');
    await user.click(await screen.findByRole('radio', { name: /^Slate/ }));
    await user.click(screen.getByRole('checkbox', { name: /^Reduce motion/ }));
    expect(document.documentElement).toHaveAttribute('data-appearance', 'obsidian');
    await user.click(screen.getByRole('button', { name: 'Save appearance' }));
    expect(await screen.findByText('Your appearance has been saved.')).toBeVisible();
    expect(bodies).toEqual([{ appearance_theme: 'slate', reduced_motion: true }]);
    expect(document.documentElement).toHaveAttribute('data-appearance', 'slate');
    expect(document.documentElement).toHaveAttribute('data-reduced-motion', 'true');
    expect(screen.getAllByTestId('evil-eye').every((eye) => eye.dataset.flameSpeed === '0')).toBe(
      true,
    );
    expect(useAuthStore.getState().user?.role).toBe('user');
  });

  it('keeps the saved theme on failure, resets drafts and can retry', async () => {
    server.use(
      http.patch('/api/me/profile', () =>
        HttpResponse.json(
          { error: { code: 'invalid_request', message: 'Appearance save unavailable.' } },
          { status: 422 },
        ),
      ),
    );
    const { user } = renderApp('/settings', 'user');
    await user.click(await screen.findByRole('radio', { name: /^Daylight/ }));
    await user.click(screen.getByRole('button', { name: 'Reset changes' }));
    expect(screen.getByRole('radio', { name: /^Obsidian/ })).toBeChecked();
    await user.click(screen.getByRole('radio', { name: /^Daylight/ }));
    await user.click(screen.getByRole('button', { name: 'Save appearance' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Appearance save unavailable.');
    expect(document.documentElement).toHaveAttribute('data-appearance', 'obsidian');
    expect(screen.getByRole('radio', { name: /^Daylight/ })).toBeChecked();
    server.use(
      http.patch('/api/me/profile', () =>
        HttpResponse.json({ ...defaultProfile, appearance_theme: 'light' }),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Save appearance' }));
    expect(await screen.findByText('Your appearance has been saved.')).toBeVisible();
    expect(document.documentElement).toHaveAttribute('data-appearance', 'light');
  });

  it('allows retrying a failed profile load', async () => {
    server.use(
      http.get('/api/me/profile', () =>
        HttpResponse.json(
          { error: { code: 'unavailable', message: 'Settings unavailable.' } },
          { status: 503 },
        ),
      ),
    );
    const { user } = renderApp('/settings', 'user');
    expect(await screen.findByRole('alert')).toHaveTextContent('Settings unavailable.');
    server.use(http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)));
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('radio', { name: /^Obsidian/ })).toBeChecked();
  });

  it('saves timezone and dates without changing profile identity or appearance', async () => {
    let body: unknown;
    server.use(
      http.patch('/api/me/profile', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ ...defaultProfile, ...(body as object) });
      }),
    );
    const { user } = renderApp('/settings?section=region', 'user');
    await user.selectOptions(await screen.findByLabelText('Timezone'), 'Europe/London');
    await user.selectOptions(screen.getByLabelText('Date format'), 'iso');
    expect(screen.queryByLabelText('Display name')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('Your preferences have been saved.')).toBeVisible();
    expect(body).toEqual({ timezone: 'Europe/London', date_format: 'iso' });
  });

  it('clears appearance on account switch and ignores a late save from the previous account', async () => {
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = 0;
    server.use(
      http.get('/api/me/profile', () =>
        HttpResponse.json({ ...defaultProfile, appearance_theme: 'slate' }),
      ),
      http.patch('/api/me/profile', async () => {
        started += 1;
        await pending;
        return HttpResponse.json({
          ...defaultProfile,
          appearance_theme: 'light',
          reduced_motion: true,
        });
      }),
    );
    const { user } = renderApp('/settings', 'user');
    await user.click(await screen.findByRole('radio', { name: /^Daylight/ }));
    await user.click(screen.getByRole('button', { name: 'Save appearance' }));
    fireEvent.submit(screen.getByRole('form', { name: 'Appearance preferences' }));
    await waitFor(() => expect(started).toBe(1));
    expect(screen.getByRole('radio', { name: /^Slate/ })).toBeDisabled();
    server.use(http.get('/api/me/profile', () => HttpResponse.json(defaultProfile)));
    act(() =>
      useAuthStore
        .getState()
        .setSession(tokenFor({ ...plainUser, id: '99999999-9999-4999-8999-999999999999' })),
    );
    expect(document.documentElement).toHaveAttribute('data-appearance', 'obsidian');
    await act(async () => {
      release();
      await pending;
    });
    await waitFor(() => expect(screen.getByRole('radio', { name: /^Obsidian/ })).toBeChecked());
    expect(document.documentElement).toHaveAttribute('data-reduced-motion', 'false');
    act(() => useAuthStore.getState().clearSession());
    expect(document.documentElement).not.toHaveAttribute('data-appearance');
  });

  it('keeps profile navigation focused and preserves old preference links', async () => {
    const { router } = renderApp('/account?section=reports', 'user');
    expect(await screen.findByRole('heading', { name: 'Report preferences' })).toBeVisible();
    expect(router.state.location.pathname).toBe('/settings');
    await act(() => router.navigate('/account'));
    const navigation = await screen.findByRole('navigation', { name: 'Account settings' });
    expect(
      within(navigation).queryByRole('link', { name: /Research defaults/ }),
    ).not.toBeInTheDocument();
    expect(within(navigation).getByRole('link', { name: 'View your teams' })).toHaveAttribute(
      'href',
      '/teams',
    );
  });
});

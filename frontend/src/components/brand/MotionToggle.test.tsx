import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { initialAuthState, useAuthStore } from '@/stores/auth';
import { mockMatchMedia } from '@/test/env';
import { adminUser, ADMIN_TOKEN, tokenFor, USER_TOKEN } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { defaultProfile } from '@/test/handlers.profile';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function findRail() {
  const rail = (await screen.findByRole('navigation', { name: 'Primary' })).closest('aside');
  if (rail === null) throw new Error('rail missing');
  return rail;
}

function railControl(rail: HTMLElement) {
  return within(rail).getByRole('button', { name: 'Pause animation' });
}

function railEye(rail: HTMLElement) {
  return within(rail).getByTestId('evil-eye');
}

/** Each account keeps its own saved motion preference on the server. */
function accountProfiles(saved: Record<string, boolean>) {
  const writes: unknown[] = [];
  server.use(
    http.get('/api/me/profile', ({ request }) => {
      const token = request.headers.get('Authorization')?.replace('Bearer ', '') ?? '';
      return HttpResponse.json({ ...defaultProfile, reduced_motion: saved[token] ?? false });
    }),
    http.patch('/api/me/profile', async ({ request }) => {
      const body = (await request.json()) as { reduced_motion: boolean };
      writes.push(body);
      const token = request.headers.get('Authorization')?.replace('Bearer ', '') ?? '';
      saved[token] = body.reduced_motion;
      return HttpResponse.json({ ...defaultProfile, reduced_motion: body.reduced_motion });
    }),
  );
  return writes;
}

describe('rail animation control', () => {
  it('saves a pause to the account and restores it after a reload', async () => {
    const writes = accountProfiles({});
    const first = renderApp('/research', 'user');
    const rail = await findRail();
    const control = railControl(rail);
    expect(control).toHaveAttribute('aria-pressed', 'false');
    expect(railEye(rail)).toHaveAttribute('data-paused', 'false');

    control.focus();
    await first.user.keyboard('{Enter}');
    expect(control).toHaveAttribute('aria-pressed', 'true');
    expect(railEye(rail)).toHaveAttribute('data-paused', 'true');
    expect(within(rail).getByRole('link', { name: 'Research' })).toBeVisible();
    await waitFor(() => {
      expect(writes).toEqual([{ reduced_motion: true }]);
    });
    expect(localStorage.getItem('ase.brand-motion')).toBeNull();
    first.unmount();

    useAuthStore.setState(initialAuthState);
    renderApp('/research', 'user');
    const reloaded = await findRail();
    await screen.findByRole('button', { name: 'Pause animation', pressed: true });
    expect(railEye(reloaded)).toHaveAttribute('data-paused', 'true');
  });

  it('stays paused for the session and offers a retry when saving fails', async () => {
    const writes = accountProfiles({});
    server.use(
      http.patch(
        '/api/me/profile',
        () => apiError(503, 'unavailable', 'Preferences are unavailable.'),
        { once: true },
      ),
    );
    const { user } = renderApp('/research', 'user');
    const rail = await findRail();
    await user.click(railControl(rail));

    const alert = await within(rail).findByRole('alert');
    expect(alert).toHaveTextContent(/not saved/i);
    expect(within(rail).queryByText(/^saved/i)).not.toBeInTheDocument();
    expect(railControl(rail)).toHaveAttribute('aria-pressed', 'true');
    expect(railEye(rail)).toHaveAttribute('data-paused', 'true');

    await user.click(within(rail).getByRole('button', { name: 'Retry saving animation choice' }));
    await waitFor(() => {
      expect(within(rail).queryByRole('alert')).not.toBeInTheDocument();
    });
    expect(writes).toEqual([{ reduced_motion: true }]);
    expect(railEye(rail)).toHaveAttribute('data-paused', 'true');
  });

  it('never applies one account preference to the next account', async () => {
    accountProfiles({ [USER_TOKEN]: true, [ADMIN_TOKEN]: false });
    const { router } = renderApp('/research', 'user');
    await screen.findByRole('button', { name: 'Pause animation', pressed: true });

    act(() => {
      useAuthStore.getState().clearSession();
    });
    await act(async () => {
      await router.navigate('/login');
    });
    const signIn = screen.getByRole('button', { name: 'Pause animation' });
    expect(signIn).toHaveAttribute('aria-pressed', 'false');
    expect(within(screen.getByTestId('auth-backdrop')).getByTestId('evil-eye')).toHaveAttribute(
      'data-paused',
      'false',
    );

    act(() => {
      useAuthStore.getState().setSession(tokenFor(adminUser));
    });
    await act(async () => {
      await router.navigate('/research');
    });
    const rail = await findRail();
    expect(railControl(rail)).toHaveAttribute('aria-pressed', 'false');
    expect(railEye(rail)).toHaveAttribute('data-paused', 'false');
  });

  it('keeps the eye still under the device setting and says why', async () => {
    mockMatchMedia(true);
    const writes = accountProfiles({});
    const { user } = renderApp('/research', 'user');
    const rail = await findRail();
    const control = railControl(rail);
    expect(control).toHaveAttribute('aria-pressed', 'true');
    expect(control).toHaveAccessibleDescription(/device is set to reduce motion/i);
    await user.click(control);
    expect(control).toHaveAttribute('aria-pressed', 'true');
    expect(railEye(rail)).toHaveAttribute('data-flame-speed', '0');
    expect(writes).toEqual([]);
  });
});

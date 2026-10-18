import { screen, waitFor } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { setCsrfCookie } from '@/test/env';
import { CSRF_VALUE } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

/**
 * The server refuses an administrator session that has not completed multi-factor
 * verification: /api/me answers 401 and the refresh family is rejected too. The new
 * workspace switch must not bypass the gate; it still ends at sign-in, remembering where.
 */
function refuseUnverifiedAdministrator() {
  setCsrfCookie(CSRF_VALUE);
  server.use(
    http.get('/api/me', () => apiError(401, 'unauthenticated', 'Sign in required.')),
    http.post('/api/auth/refresh', () => apiError(401, 'invalid_refresh', 'Expired.')),
  );
}

describe('administrator without a verified MFA session', () => {
  it('is redirected to sign-in from a deep link before any admin page mounts', async () => {
    refuseUnverifiedAdministrator();
    const { router } = renderApp('/admin/users', 'admin');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(router.state.location.state).toMatchObject({ from: '/admin/users' });
    expect(useAuthStore.getState().status).toBe('anonymous');
    expect(screen.queryByRole('navigation', { name: 'Administration' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Go to research workspace' }),
    ).not.toBeInTheDocument();
  });

  it('is redirected the same way after using the Administration switch', async () => {
    const { user, router } = renderApp('/research/saved', 'admin');
    await screen.findByRole('heading', { name: 'Saved research', level: 1 });
    refuseUnverifiedAdministrator();
    await user.click(screen.getByRole('link', { name: 'Go to Administration' }));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(router.state.location.state).toMatchObject({ from: '/admin' });
    expect(screen.queryByRole('navigation', { name: 'Administration' })).not.toBeInTheDocument();
  });
});

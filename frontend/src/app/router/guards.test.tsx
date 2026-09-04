import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { ADMIN_PASSWORD, adminUser } from '@/test/fixtures';
import { renderApp } from '@/test/render';

describe('route guards', () => {
  it('waits for the bootstrap, then sends anonymous visitors to login with the intended path', async () => {
    const { router } = renderApp('/admin/users');
    expect(screen.getByRole('status')).toHaveTextContent('Checking your session');

    await useAuthStore.getState().bootstrap();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });
    expect(router.state.location.state).toEqual({ from: '/admin/users' });
    // The login page is a lazy chunk, so it may arrive a tick after the redirect.
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('returns to the intended path after login', async () => {
    const { router, user } = renderApp('/admin/users?tab=all', 'anonymous');
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/login');
    });

    await user.type(screen.getByLabelText('Email'), adminUser.email);
    await user.type(screen.getByLabelText('Password'), ADMIN_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/admin/users');
    });
    expect(router.state.location.search).toBe('?tab=all');
    expect(await screen.findByRole('heading', { name: 'Users' })).toBeInTheDocument();
  });

  it('blocks non-admin users from admin pages', async () => {
    renderApp('/admin/audit', 'user');
    expect(await screen.findByText('Admin access required')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Audit log' })).not.toBeInTheDocument();
  });

  it('renders the 404 page for unknown paths', () => {
    renderApp('/nowhere/at/all', 'anonymous');
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to the globe' })).toHaveAttribute('href', '/');
  });

  it('serves the development brand capture page at 512 pixels', async () => {
    renderApp('/brand/capture', 'anonymous');
    const frame = await screen.findByTestId('brand-capture');
    expect(frame).toHaveStyle({ width: '512px', height: '512px' });
    expect(frame).toHaveAccessibleName('The All Seeing Eye');
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-background', '#07070b');
  });
});

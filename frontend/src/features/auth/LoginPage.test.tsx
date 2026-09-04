import { screen } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { USER_PASSWORD, plainUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';

describe('LoginPage', () => {
  it('signs in and lands on the globe', async () => {
    const { user, router } = renderApp('/login', 'anonymous');
    expect(screen.getByTestId('auth-backdrop')).toContainElement(screen.getByTestId('evil-eye'));
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-pupil-follow', '1');

    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('group', { name: 'View mode' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('shows the generic failure message from the API and stays on the page', async () => {
    const { user, router } = renderApp('/login', 'anonymous');
    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), 'wrong-password-value');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
    expect(router.state.location.pathname).toBe('/login');
    expect(useAuthStore.getState().status).toBe('anonymous');
  });

  it('explains rate limiting using Retry-After', async () => {
    server.use(
      http.post('/api/auth/login', () =>
        apiError(429, 'rate_limited', 'Too many.', undefined, { 'Retry-After': '60' }),
      ),
    );
    const { user } = renderApp('/login', 'anonymous');
    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many attempts. Try again in 60 seconds.',
    );
  });

  it('links to account requests and password recovery', () => {
    renderApp('/login', 'anonymous');
    expect(screen.getByRole('link', { name: 'Request an account' })).toHaveAttribute(
      'href',
      '/request-account',
    );
    expect(screen.getByRole('link', { name: 'Forgotten password' })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
  });

  it('sends an already authenticated visitor to the globe', async () => {
    const { router } = renderApp('/login', 'user');
    expect(await screen.findByRole('group', { name: 'View mode' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
  });
});

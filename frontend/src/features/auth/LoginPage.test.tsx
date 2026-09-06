import { act, fireEvent, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { ADMIN_PASSWORD, adminUser, USER_PASSWORD, plainUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import { mockMatchMedia, setVisibility } from '@/test/env';

describe('LoginPage', () => {
  it('includes an optional authenticator code in login', async () => {
    let payload: unknown;
    server.use(
      http.post('/api/auth/login', async ({ request }) => {
        payload = await request.json();
        return HttpResponse.json(tokenFor(plainUser));
      }),
    );
    const { user } = renderApp('/login', 'anonymous');
    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
    await user.click(screen.getByText('Use an authenticator code'));
    await user.type(screen.getByLabelText('Authenticator code'), '123456');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('group', { name: 'View mode' })).toBeInTheDocument();
    expect(payload).toEqual({
      email: plainUser.email,
      password: USER_PASSWORD,
      totp_code: '123456',
    });
  });

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

  it('lands an administrator in the dedicated administration area', async () => {
    const { user, router } = renderApp('/login', 'anonymous');
    await user.type(screen.getByLabelText('Email'), adminUser.email);
    await user.type(screen.getByLabelText('Password'), ADMIN_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(
      await screen.findByRole('heading', { name: 'Administration', level: 1 }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/admin');
  });

  it('sends an authenticated administrator to their workspace', async () => {
    const { router } = renderApp('/login', 'admin');
    await screen.findByRole('heading', { name: 'Administration', level: 1 });
    expect(router.state.location.pathname).toBe('/admin');
  });

  it('reopens the code disclosure when a hidden incomplete code fails validation', async () => {
    const { user } = renderApp('/login', 'anonymous');
    await user.click(screen.getByText('Use an authenticator code'));
    const code = screen.getByLabelText('Authenticator code');
    await user.type(code, '123');
    await user.click(screen.getByText('Use an authenticator code'));
    expect(code.closest('details')).not.toHaveAttribute('open');
    fireEvent.invalid(code);
    expect(code.closest('details')).toHaveAttribute('open');
    expect(code).toBeVisible();
  });

  it('reveals the entered password without submitting and restores its masking', async () => {
    const { user } = renderApp('/login', 'anonymous');
    const password = screen.getByLabelText('Password');
    await user.type(password, 'Example password');
    await user.click(screen.getByRole('button', { name: 'Show password' }));
    expect(password).toHaveAttribute('type', 'text');
    expect(password).toHaveValue('Example password');
    expect(useAuthStore.getState().status).toBe('anonymous');
    await user.click(screen.getByRole('button', { name: 'Hide password' }));
    expect(password).toHaveAttribute('type', 'password');
  });

  it('shows a caps-lock cue while typing and clears it after leaving the password', async () => {
    const { user } = renderApp('/login', 'anonymous');
    const password = screen.getByLabelText('Password');
    await user.click(password);
    fireEvent.keyDown(password, { key: 'A', modifierCapsLock: true });
    expect(screen.getByRole('status')).toHaveTextContent('Caps Lock is on.');
    fireEvent.keyUp(password, { key: 'CapsLock', modifierCapsLock: false });
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    fireEvent.keyDown(password, { key: 'A', modifierCapsLock: true });
    await user.tab();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it('prevents credential edits and duplicate submission while signing in', async () => {
    let release: (() => void) | undefined;
    let requests = 0;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post('/api/auth/login', async () => {
        requests += 1;
        await pending;
        return apiError(401, 'invalid_credentials', 'Incorrect email or password.');
      }),
    );
    const { user } = renderApp('/login', 'anonymous');
    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('button', { name: 'Signing in…' })).toBeDisabled();
    expect(screen.getByLabelText('Email')).toBeDisabled();
    expect(screen.getByLabelText('Password')).toBeDisabled();
    const form = screen.getByLabelText('Email').closest('form');
    if (form === null) throw new Error('Expected the login form');
    fireEvent.submit(form);
    expect(requests).toBe(1);
    release?.();
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
    expect(screen.getByLabelText('Password')).toBeEnabled();
  });

  it('stops the brand motion when hidden and honours reduced motion', () => {
    mockMatchMedia(true);
    renderApp('/login', 'anonymous');
    const eye = screen.getByTestId('evil-eye');
    expect(eye).toHaveAttribute('data-flame-speed', '0');
    expect(eye).toHaveAttribute('data-pupil-follow', '0');
    expect(eye).toHaveAttribute('data-max-fps', '1');
    act(() => {
      setVisibility('hidden');
    });
    expect(eye).toHaveAttribute('data-paused', 'true');
    act(() => {
      setVisibility('visible');
    });
    expect(eye).toHaveAttribute('data-paused', 'false');
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

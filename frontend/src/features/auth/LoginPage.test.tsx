import { act, fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { ADMIN_PASSWORD, adminUser, USER_PASSWORD, plainUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import { mockMatchMedia, setVisibility } from '@/test/env';

describe('LoginPage', () => {
  it('signs in and lands on the globe', async () => {
    const { user, router } = renderApp('/login', 'anonymous');
    expect(screen.getByTestId('auth-backdrop')).toContainElement(screen.getByTestId('evil-eye'));
    expect(screen.getByTestId('evil-eye')).toHaveAttribute('data-pupil-follow', '1');

    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    // Authentication should not depend on the separately tested globe's lazy import.
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
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

  it('reveals the entered password without submitting and restores its masking', async () => {
    const { user } = renderApp('/login', 'anonymous');
    const password = screen.getByLabelText('Password');
    await user.type(password, 'Example password');
    const toggle = screen.getByRole('button', { name: 'Show password' });
    // The name carries the state, so the toggle must not also expose a pressed state.
    expect(toggle).not.toHaveAttribute('aria-pressed');
    await user.click(toggle);
    expect(password).toHaveAttribute('type', 'text');
    expect(password).toHaveValue('Example password');
    expect(useAuthStore.getState().status).toBe('anonymous');
    expect(toggle).toHaveAccessibleName('Hide password');
    expect(toggle).not.toHaveAttribute('aria-pressed');
    await user.click(toggle);
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

  it('keeps focus on the sign-in button and prevents duplicate submission', async () => {
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
    const button = screen.getByRole('button', { name: 'Sign in' });
    try {
      await user.click(button);
      expect(await screen.findByRole('button', { name: 'Signing in…' })).toBe(button);
      expect(button).toHaveAttribute('aria-disabled', 'true');
      expect(button).toHaveFocus();
      expect(screen.getByLabelText('Email')).toBeEnabled();
      expect(screen.getByLabelText('Password')).toBeEnabled();
      expect(screen.getByRole('button', { name: 'Show password' })).toBeEnabled();
      // The pending UI renders before MSW necessarily receives the first request.
      await waitFor(() => expect(requests).toBe(1));
      const form = button.closest('form');
      if (form === null) throw new Error('Expected the login form');
      fireEvent.submit(form);
      await user.click(button);
      await user.keyboard('{Enter}');
      expect(requests).toBe(1);
    } finally {
      release?.();
    }
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
    expect(screen.getByRole('button', { name: 'Sign in' })).toBe(button);
    expect(button).not.toHaveAttribute('aria-disabled');
    expect(button).toHaveFocus();
  });

  it('keeps focus in the password field when signing in with Enter', async () => {
    let release: (() => void) | undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post('/api/auth/login', async () => {
        await pending;
        return apiError(401, 'invalid_credentials', 'Incorrect email or password.');
      }),
    );
    const { user } = renderApp('/login', 'anonymous');
    await user.type(screen.getByLabelText('Email'), plainUser.email);
    const password = screen.getByLabelText('Password');
    try {
      await user.type(password, `${USER_PASSWORD}{Enter}`);
      expect(await screen.findByRole('button', { name: 'Signing in…' })).toBeInTheDocument();
      expect(password).toHaveFocus();
    } finally {
      release?.();
    }
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
    expect(password).toHaveFocus();
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

  it('keeps account navigation available across signup and recovery', async () => {
    const { user } = renderApp('/login', 'anonymous');
    const navigation = () => within(screen.getByRole('navigation', { name: 'Account access' }));
    expect(navigation().getByRole('link', { name: 'Sign in' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    await user.click(navigation().getByRole('link', { name: 'Sign up' }));
    expect(await screen.findByRole('heading', { name: 'Request an account' })).toBeInTheDocument();
    expect(screen.getByText(/An administrator reviews every request/)).toBeInTheDocument();
    expect(navigation().getByRole('link', { name: 'Sign up' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(navigation().queryByRole('link', { name: 'Recovery' })).not.toBeInTheDocument();
    await user.click(navigation().getByRole('link', { name: 'Sign in' }));
    await user.click(await screen.findByRole('link', { name: 'Forgotten password' }));
    expect(await screen.findByRole('heading', { name: 'Forgotten password' })).toBeInTheDocument();
    await user.click(navigation().getByRole('link', { name: 'Sign in' }));
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('sends an already authenticated visitor to the globe', async () => {
    const { router } = renderApp('/login', 'user');
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
  });
});

import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { mockMatchMedia } from '@/test/env';
import { plainUser, USER_PASSWORD } from '@/test/fixtures';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

function signInEye() {
  return within(screen.getByTestId('auth-backdrop')).getByTestId('evil-eye');
}

function pauseControl() {
  return screen.getByRole('button', { name: 'Pause animation' });
}

describe('sign-in animation control', () => {
  it('is reachable by keyboard and pauses the eye without disabling the form', async () => {
    const { user } = renderApp('/login', 'anonymous');
    const control = pauseControl();
    expect(control).toHaveAttribute('aria-pressed', 'false');
    expect(signInEye()).toHaveAttribute('data-paused', 'false');

    await user.tab();
    expect(control).toHaveFocus();
    await user.keyboard('{Enter}');
    expect(control).toHaveAttribute('aria-pressed', 'true');
    expect(pauseControl()).toBe(control);
    expect(signInEye()).toHaveAttribute('data-paused', 'true');
    expect(screen.getByLabelText('Email')).toBeEnabled();
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeVisible();

    await user.keyboard(' ');
    expect(control).toHaveAttribute('aria-pressed', 'false');
    expect(signInEye()).toHaveAttribute('data-paused', 'false');
  });

  it('keeps the pre-sign-in choice across a reload with only the motion value stored', async () => {
    const first = renderApp('/login', 'anonymous');
    await first.user.click(pauseControl());
    first.unmount();
    expect(Object.keys(localStorage)).toEqual(['ase.brand-motion']);
    expect(localStorage.getItem('ase.brand-motion')).toBe('paused');

    renderApp('/login', 'anonymous');
    expect(pauseControl()).toHaveAttribute('aria-pressed', 'true');
    expect(signInEye()).toHaveAttribute('data-paused', 'true');
  });

  it('carries a pre-sign-in pause through sign-in without writing the account', async () => {
    const writes: unknown[] = [];
    server.use(
      http.patch('/api/me/profile', async ({ request }) => {
        writes.push(await request.json());
        return HttpResponse.json({});
      }),
    );
    const { user } = renderApp('/login', 'anonymous');
    await user.click(pauseControl());
    await user.type(screen.getByLabelText('Email'), plainUser.email);
    await user.type(screen.getByLabelText('Password'), USER_PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    const rail = (await screen.findByRole('navigation', { name: 'Primary' })).closest('aside');
    if (rail === null) throw new Error('rail missing');
    expect(within(rail).getByTestId('evil-eye')).toHaveAttribute('data-paused', 'true');
    expect(within(rail).getByRole('button', { name: 'Pause animation' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(writes).toEqual([]);
  });

  it('explains that the device setting keeps motion off', () => {
    mockMatchMedia(true);
    renderApp('/login', 'anonymous');
    const control = pauseControl();
    expect(control).toHaveAttribute('aria-pressed', 'true');
    expect(control).toHaveAttribute('aria-disabled', 'true');
    expect(control).toHaveAccessibleDescription(/device is set to reduce motion/i);
    expect(signInEye()).toHaveAttribute('data-flame-speed', '0');
    expect(signInEye()).toHaveAttribute('data-pupil-follow', '0');
  });

  it('does not let resume override the device setting', async () => {
    mockMatchMedia(true);
    const { user } = renderApp('/login', 'anonymous');
    await user.click(pauseControl());
    expect(pauseControl()).toHaveAttribute('aria-pressed', 'true');
    expect(signInEye()).toHaveAttribute('data-flame-speed', '0');
    expect(localStorage.getItem('ase.brand-motion')).toBeNull();
  });
});

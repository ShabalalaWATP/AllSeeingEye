import { act, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderApp } from '@/test/render';

function announced(): string {
  const regions = document.querySelectorAll('[aria-live="polite"][aria-atomic="true"]');
  return Array.from(regions, (region) => region.textContent).join(' ');
}

describe('public page titles and announcements', () => {
  it.each([
    ['/login', 'Sign in', 'Sign in'],
    ['/request-account', 'Request an account', 'Request an account'],
    ['/forgot-password', 'Forgotten password', 'Forgotten password'],
    ['/set-password?token=abc', 'Set your password', 'Set your password'],
    ['/set-password', 'Link incomplete', 'Set your password'],
  ])('names %s in the document title', async (path, heading, title) => {
    renderApp(path, 'anonymous');
    await screen.findByRole('heading', { name: heading, level: 1 });
    expect(document.title).toBe(`${title} · The All Seeing Eye`);
    // The first page of a visit is named but neither announced nor focused.
    expect(announced()).toBe('');
    expect(document.body).toHaveFocus();
  });

  it('announces and focuses each public page the reader moves to', async () => {
    const { user, router } = renderApp('/login', 'anonymous');
    await screen.findByRole('heading', { name: 'Sign in', level: 1 });
    const access = screen.getByRole('navigation', { name: 'Account access' });
    await user.click(within(access).getByRole('link', { name: 'Sign up' }));
    const request = await screen.findByRole('heading', { name: 'Request an account', level: 1 });
    await waitFor(() => {
      expect(request).toHaveFocus();
    });
    expect(document.title).toBe('Request an account · The All Seeing Eye');
    expect(announced()).toBe('Navigated to Request an account');

    await user.click(within(access).getByRole('link', { name: 'Sign in' }));
    await user.click(await screen.findByRole('link', { name: 'Forgotten password' }));
    expect(router.state.location.pathname).toBe('/forgot-password');
    await waitFor(() => {
      expect(announced()).toBe('Navigated to Forgotten password');
    });
    expect(document.title).toBe('Forgotten password · The All Seeing Eye');
  });

  it('announces a sign-in redirect without moving focus', async () => {
    const { router } = renderApp('/watches', 'anonymous');
    await screen.findByRole('heading', { name: 'Sign in', level: 1 });
    expect(router.state.location.pathname).toBe('/login');
    await waitFor(() => {
      expect(announced()).toBe('Navigated to Sign in');
    });
    expect(document.title).toBe('Sign in · The All Seeing Eye');
    expect(document.body).toHaveFocus();
  });

  it('names the not-found page and announces arriving there', async () => {
    const { router, unmount } = renderApp('/login', 'anonymous');
    await screen.findByRole('heading', { name: 'Sign in', level: 1 });
    await act(() => router.navigate('/nowhere'));
    const heading = await screen.findByRole('heading', { name: 'Page not found', level: 1 });
    expect(document.title).toBe('Page not found · The All Seeing Eye');
    await waitFor(() => {
      expect(heading).toHaveFocus();
    });
    expect(announced()).toBe('Navigated to Page not found');
    unmount();
    expect(document.title).toBe('The All Seeing Eye');
  });

  it('names a directly opened unknown address', async () => {
    renderApp('/definitely/not/here', 'user');
    await screen.findByRole('heading', { name: 'Page not found', level: 1 });
    expect(document.title).toBe('Page not found · The All Seeing Eye');
    expect(announced()).toBe('');
  });
});

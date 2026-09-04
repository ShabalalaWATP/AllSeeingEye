import { screen, waitFor } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { BAD_TOKEN, GOOD_TOKEN, WEAK_PASSWORD, WEAK_PASSWORD_REASON } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const STRONG = 'a-long-and-unusual-passphrase';

async function submitPassword(
  user: ReturnType<typeof renderApp>['user'],
  password: string,
  confirmation = password,
) {
  await user.type(screen.getByLabelText('New password'), password);
  await user.type(screen.getByLabelText('Confirm password'), confirmation);
  await user.click(screen.getByRole('button', { name: 'Set password' }));
}

describe('SetPasswordPage', () => {
  it('explains the policy, sets the password and offers sign in', async () => {
    let body: unknown = null;
    server.use(
      http.post('/api/auth/set-password', async ({ request }) => {
        body = await request.json();
        return new Response(null, { status: 204 });
      }),
    );
    const { user } = renderApp(`/set-password?token=${GOOD_TOKEN}`, 'anonymous');
    expect(screen.getByText(/Use 12 to 128 characters/)).toBeInTheDocument();
    await submitPassword(user, STRONG);
    expect(await screen.findByRole('status')).toHaveTextContent('Your password has been set.');
    expect(body).toEqual({ token: GOOD_TOKEN, new_password: STRONG });
    expect(screen.getByRole('link', { name: 'Go to sign in' })).toHaveAttribute('href', '/login');
  });

  it('shows the invalid token message with a way to get a new link', async () => {
    const { user } = renderApp(`/set-password?token=${BAD_TOKEN}`, 'anonymous');
    await submitPassword(user, STRONG);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This link is invalid, has expired or has already been used.',
    );
    expect(screen.getByRole('link', { name: 'Request a new link' })).toHaveAttribute(
      'href',
      '/forgot-password',
    );
    expect(screen.getByRole('button', { name: 'Set password' })).toBeDisabled();
  });

  it('shows the weak password reason against the field', async () => {
    const { user } = renderApp(`/set-password?token=${GOOD_TOKEN}`, 'anonymous');
    await submitPassword(user, WEAK_PASSWORD);
    expect(await screen.findByRole('alert')).toHaveTextContent(WEAK_PASSWORD_REASON);
    expect(screen.getByLabelText('New password')).toHaveAttribute('aria-invalid', 'true');
  });

  it('checks length and confirmation before calling the API', async () => {
    let called = false;
    server.use(
      http.post('/api/auth/set-password', () => {
        called = true;
        return new Response(null, { status: 204 });
      }),
    );
    const { user } = renderApp(`/set-password?token=${GOOD_TOKEN}`, 'anonymous');
    await submitPassword(user, 'short');
    expect(screen.getByRole('alert')).toHaveTextContent('at least 12 characters');
    await user.clear(screen.getByLabelText('New password'));
    await user.clear(screen.getByLabelText('Confirm password'));
    await submitPassword(user, STRONG, `${STRONG}-x`);
    expect(screen.getByRole('alert')).toHaveTextContent('The two passwords do not match.');
    expect(called).toBe(false);
  });

  it('shows other API failures generally', async () => {
    server.use(http.post('/api/auth/set-password', () => apiError(429, 'rate_limited', 'x')));
    const { user } = renderApp(`/set-password?token=${GOOD_TOKEN}`, 'anonymous');
    await submitPassword(user, STRONG);
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts.');
  });

  it('handles a link without a token', () => {
    renderApp('/set-password', 'anonymous');
    expect(screen.getByRole('alert')).toHaveTextContent('This link is missing its token.');
  });

  it('redirects the activation and reset paths, keeping the query string', async () => {
    const activate = renderApp(`/activate?token=${GOOD_TOKEN}`, 'anonymous');
    await waitFor(() => {
      expect(activate.router.state.location.pathname).toBe('/set-password');
    });
    expect(activate.router.state.location.search).toBe(`?token=${GOOD_TOKEN}`);
    expect(screen.getByRole('heading', { name: 'Set your password' })).toBeInTheDocument();
    activate.unmount();

    const reset = renderApp('/reset-password?token=abc', 'anonymous');
    await waitFor(() => {
      expect(reset.router.state.location.pathname).toBe('/set-password');
    });
    expect(reset.router.state.location.search).toBe('?token=abc');
  });
});

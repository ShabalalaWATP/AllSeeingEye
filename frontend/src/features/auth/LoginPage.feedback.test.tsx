import { fireEvent, render, screen } from '@testing-library/react';
import { http } from 'msw';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { USER_PASSWORD, plainUser } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';
import { LoginPage } from './LoginPage';

function renderLogin(state: unknown = null) {
  useAuthStore.getState().clearSession();
  const router = createMemoryRouter([{ path: '/login', element: <LoginPage /> }], {
    initialEntries: [{ pathname: '/login', state }],
  });
  render(<RouterProvider router={router} />);
  return router;
}

it('confirms a completed password change carried by the navigation state', () => {
  renderLogin({ passwordChanged: true });
  expect(screen.getByRole('status')).toHaveTextContent(
    'Your password has changed. Sign in with your new password.',
  );
  expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
});

it.each([null, 'passwordChanged', {}, { passwordChanged: false }, { passwordChanged: 'true' }])(
  'does not claim a password change from unconfirmed navigation state %j',
  (state) => {
    renderLogin(state);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  },
);

it('shows a rejected sign-in message and stays anonymous on the login page', async () => {
  const router = renderLogin();
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: plainUser.email } });
  fireEvent.change(screen.getByLabelText('Password'), {
    target: { value: 'wrong-password-value' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');
  expect(router.state.location.pathname).toBe('/login');
  expect(useAuthStore.getState().status).toBe('anonymous');
});

it('explains rate limiting using Retry-After without repeating the sign-in request', async () => {
  let requests = 0;
  server.use(
    http.post('/api/auth/login', () => {
      requests += 1;
      return apiError(429, 'rate_limited', 'Too many.', undefined, { 'Retry-After': '60' });
    }),
  );
  renderLogin();
  // This assertion exercises server feedback; input/keyboard interaction is covered separately.
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: plainUser.email } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: USER_PASSWORD } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Too many attempts. Try again in 60 seconds.',
  );
  expect(screen.getByRole('button', { name: 'Sign in' })).toBeEnabled();
  expect(useAuthStore.getState().status).toBe('anonymous');
  expect(requests).toBe(1);
});

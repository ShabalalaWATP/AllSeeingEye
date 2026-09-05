import { screen } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function fillAndSubmit(user: ReturnType<typeof renderApp>['user'], reason = '') {
  await user.type(screen.getByLabelText('Email'), 'newcomer@example.com');
  await user.type(screen.getByLabelText('Display name'), 'Nia Newcomer');
  if (reason !== '') await user.type(screen.getByLabelText('Reason (optional)'), reason);
  await user.click(screen.getByRole('button', { name: 'Send request' }));
}

describe('RequestAccountPage', () => {
  it('always shows the 202 message and sends the optional reason', async () => {
    let body: unknown = null;
    server.use(
      http.post('/api/auth/request-account', async ({ request }) => {
        body = await request.json();
        return Response.json(
          { message: 'If the address is eligible, an administrator will review the request.' },
          { status: 202 },
        );
      }),
    );
    const { user } = renderApp('/request-account', 'anonymous');
    await fillAndSubmit(user, 'Regional desk analyst');
    expect(await screen.findByRole('status')).toHaveTextContent(
      'If the address is eligible, an administrator will review the request.',
    );
    expect(body).toEqual({
      email: 'newcomer@example.com',
      display_name: 'Nia Newcomer',
      reason: 'Regional desk analyst',
    });
    expect(screen.getByRole('link', { name: 'Back to sign in' })).toHaveAttribute('href', '/login');
  });

  it('omits an empty reason', async () => {
    let body: unknown = null;
    server.use(
      http.post('/api/auth/request-account', async ({ request }) => {
        body = await request.json();
        return Response.json({ message: 'Received.' }, { status: 202 });
      }),
    );
    const { user } = renderApp('/request-account', 'anonymous');
    await fillAndSubmit(user);
    await screen.findByRole('status');
    expect(body).toEqual({ email: 'newcomer@example.com', display_name: 'Nia Newcomer' });
  });

  it('shows validation reasons against the fields', async () => {
    server.use(
      http.post('/api/auth/request-account', () =>
        apiError(422, 'validation_error', 'Invalid input.', {
          email: 'Enter a valid email address.',
        }),
      ),
    );
    const { user } = renderApp('/request-account', 'anonymous');
    await fillAndSubmit(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('Enter a valid email address.');
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows other failures as a general message', async () => {
    server.use(http.post('/api/auth/request-account', () => apiError(429, 'rate_limited', 'x')));
    const { user } = renderApp('/request-account', 'anonymous');
    await fillAndSubmit(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts.');
  });
});

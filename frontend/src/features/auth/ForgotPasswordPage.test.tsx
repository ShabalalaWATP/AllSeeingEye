import { screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('ForgotPasswordPage', () => {
  it('explains the administrator recovery path when email is unavailable', async () => {
    server.use(
      http.post('/api/auth/forgot-password', () =>
        HttpResponse.json(
          {
            email_available: false,
            message:
              'Email password recovery is unavailable on this installation. Contact an administrator to request a password reset link.',
          },
          { status: 202 },
        ),
      ),
    );
    const { user } = renderApp('/forgot-password', 'anonymous');
    await user.type(screen.getByLabelText('Email'), 'someone@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));
    expect(await screen.findByRole('heading', { name: 'Contact an administrator' })).toBeVisible();
    expect(screen.getByRole('status')).toHaveTextContent('Email password recovery is unavailable');
    expect(screen.queryByText('Check your inbox')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to sign in' })).toHaveAttribute('href', '/login');
  });

  it('always shows the 202 message', async () => {
    const { user } = renderApp('/forgot-password', 'anonymous');
    await user.type(screen.getByLabelText('Email'), 'someone@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));
    expect(await screen.findByRole('status')).toHaveTextContent(
      'If the address is registered, check your email for a reset link. You can request another if it does not arrive.',
    );
    expect(screen.getByRole('link', { name: 'Back to sign in' })).toHaveAttribute('href', '/login');
  });

  it('shows validation reasons and general failures', async () => {
    server.use(
      http.post('/api/auth/forgot-password', () =>
        apiError(422, 'validation_error', 'Invalid.', { email: 'Enter a valid email address.' }),
      ),
    );
    const { user } = renderApp('/forgot-password', 'anonymous');
    await user.type(screen.getByLabelText('Email'), 'someone@example.com');
    await user.click(screen.getByRole('button', { name: 'Send reset link' }));
    const alerts = await screen.findAllByRole('alert');
    expect(alerts.map((node) => node.textContent)).toEqual([
      'Invalid.',
      'Enter a valid email address.',
    ]);
  });
});

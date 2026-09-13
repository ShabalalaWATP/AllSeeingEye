import { screen } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

describe('ForgotPasswordPage', () => {
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

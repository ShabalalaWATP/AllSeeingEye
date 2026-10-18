import { fireEvent, screen } from '@testing-library/react';
import { http } from 'msw';
import { describe, expect, it } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

async function fillAndSubmit(user: ReturnType<typeof renderApp>['user'], reason = '') {
  await user.type(await screen.findByLabelText('Email'), 'newcomer@example.com');
  await user.type(screen.getByLabelText('Display name'), 'Nia Newcomer');
  if (reason !== '') await user.type(screen.getByLabelText('Reason (optional)'), reason);
  await user.click(screen.getByLabelText('I agree to the Terms and Acceptable Use Policy'));
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
      accept_terms: true,
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
    expect(body).toEqual({
      email: 'newcomer@example.com',
      display_name: 'Nia Newcomer',
      accept_terms: true,
    });
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

  it('sends one pending request even when the form is submitted twice', async () => {
    let requests = 0;
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post('/api/auth/request-account', async () => {
        requests += 1;
        await pending;
        return Response.json({ message: 'Received.' }, { status: 202 });
      }),
    );
    const { user } = renderApp('/request-account', 'anonymous');
    await user.type(screen.getByLabelText('Email'), 'newcomer@example.com');
    await user.type(screen.getByLabelText('Display name'), 'Nia Newcomer');
    await user.click(screen.getByLabelText('I agree to the Terms and Acceptable Use Policy'));
    const form = screen.getByRole('button', { name: 'Send request' }).closest('form');
    if (form === null) throw new Error('Expected the request form');
    fireEvent.submit(form);
    fireEvent.submit(form);
    release();
    expect(await screen.findByRole('status')).toHaveTextContent('Received.');
    expect(requests).toBe(1);
  });

  it('requires agreement before sending, keeps the typed request and links the policies', async () => {
    let requests = 0;
    server.use(
      http.post('/api/auth/request-account', () => {
        requests += 1;
        return Response.json({ message: 'Received.' }, { status: 202 });
      }),
    );
    const { user, container } = renderApp('/request-account', 'anonymous');
    await user.type(await screen.findByLabelText('Email'), 'newcomer@example.com');
    await user.type(screen.getByLabelText('Display name'), 'Nia Newcomer');
    await user.click(screen.getByRole('button', { name: 'Send request' }));
    const agreement = screen.getByLabelText('I agree to the Terms and Acceptable Use Policy');
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Agree to the Terms and Acceptable Use Policy to request an account.',
    );
    expect(agreement).toHaveFocus();
    expect(agreement).toHaveAttribute('aria-invalid', 'true');
    expect(agreement).toHaveAccessibleDescription(/Read the Terms .* Agree to the Terms/);
    expect(requests).toBe(0);
    expect(screen.getByLabelText('Email')).toHaveValue('newcomer@example.com');
    for (const [name, href] of [
      ['Terms (opens in a new tab)', '/terms'],
      ['Acceptable Use Policy (opens in a new tab)', '/acceptable-use'],
    ] as const) {
      const link = screen.getByRole('link', { name });
      expect(link).toHaveAttribute('href', href);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
    await expectNoAxeViolations(container);
    await user.click(agreement);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Send request' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Received.');
    expect(requests).toBe(1);
  });

  it('shows a server refusal of missing agreement against the checkbox', async () => {
    server.use(
      http.post('/api/auth/request-account', () =>
        apiError(422, 'validation_error', 'The request is invalid.', {
          accept_terms: 'Agree to the Terms and Acceptable Use Policy to request an account.',
        }),
      ),
    );
    const { user } = renderApp('/request-account', 'anonymous');
    await fillAndSubmit(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('Agree to the Terms');
    expect(screen.getByLabelText('I agree to the Terms and Acceptable Use Policy')).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });
});

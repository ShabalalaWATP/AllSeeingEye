import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';

import { expectNoAxeViolations } from '@/test/axe';
import { server } from '@/test/server';
import { useAuthStore } from '@/stores/auth';
import * as authApi from '@/lib/api/auth';

import { EnterpriseEnquiryForm } from './EnterpriseEnquiryForm';
import { ENQUIRY_CONFIRMATION } from './useEnterpriseEnquiry';

function form() {
  const view = render(
    <MemoryRouter>
      <main>
        <h1>Self-hosting</h1>
        <h2>Talk to us</h2>
        <EnterpriseEnquiryForm />
      </main>
    </MemoryRouter>,
  );
  return { ...view, user: userEvent.setup() };
}

async function complete(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByRole('textbox', { name: 'Name' }), 'Example Visitor');
  await user.type(screen.getByRole('textbox', { name: 'Work email' }), 'visitor@example.test');
  await user.type(screen.getByRole('textbox', { name: 'Organisation' }), 'Example Organisation');
  await user.selectOptions(screen.getByLabelText('Deployment interest'), 'own_cloud');
  await user.selectOptions(screen.getByLabelText('Expected users'), '11_50');
  await user.click(screen.getByRole('checkbox', { name: /I have read/ }));
}

describe('public enquiry form', () => {
  it('sends generated-contract fields without auth, privacy acknowledgement or input echo', async () => {
    let submitted: unknown;
    let authorization: string | null = 'not requested';
    server.use(
      http.post('/api/enquiries', async ({ request }) => {
        authorization = request.headers.get('Authorization');
        submitted = await request.json();
        return HttpResponse.json({ message: 'UNTRUSTED RESPONSE CONTENT' }, { status: 202 });
      }),
    );
    useAuthStore.setState({ accessToken: 'synthetic-token', status: 'authenticated' });
    const { user } = form();
    await complete(user);
    await user.type(screen.getByLabelText('Role (optional)'), 'Research lead');
    await user.type(screen.getByLabelText('Message (optional)'), 'Planning a local deployment.');
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    expect(await screen.findByText(ENQUIRY_CONFIRMATION)).toHaveFocus();
    expect(submitted).toEqual({
      name: 'Example Visitor',
      email: 'visitor@example.test',
      organisation: 'Example Organisation',
      role: 'Research lead',
      deployment_interest: 'own_cloud',
      expected_users: '11_50',
      message: 'Planning a local deployment.',
      website: '',
    });
    expect(authorization).toBeNull();
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.queryByText(/UNTRUSTED RESPONSE|Example Visitor/)).toBeNull();
  });

  it('announces required errors, associates them with fields and focuses feedback', async () => {
    const post = vi.fn();
    server.use(
      http.post('/api/enquiries', () => {
        post();
        return HttpResponse.json({ message: 'ok' }, { status: 202 });
      }),
    );
    const { user } = form();
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    const feedback = screen.getByText(
      'Please check the marked fields before sending your enquiry.',
    );
    expect(feedback).toHaveFocus();
    expect(feedback).toHaveAttribute('role', 'status');
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByRole('textbox', { name: 'Name' })).toHaveAccessibleDescription(
      'Enter your name (up to 100 characters).',
    );
    expect(screen.getByRole('checkbox')).toHaveAccessibleDescription(
      'Confirm that you have read the privacy notice.',
    );
    expect(post).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: /privacy notice/ })).toHaveAttribute(
      'href',
      '/privacy',
    );
  });

  it('keeps the honeypot in the form but outside keyboard and accessible controls', async () => {
    const { container, user } = form();
    const trap = container.querySelector('input[name="website"]');
    expect(trap).toHaveAttribute('tabindex', '-1');
    expect(trap).toHaveAttribute('aria-hidden', 'true');
    expect(screen.queryByRole('textbox', { name: 'Website' })).toBeNull();
    screen.getByLabelText('Message (optional)').focus();
    await user.tab();
    expect(screen.getByRole('checkbox')).toHaveFocus();
  });

  it('bounds the message with an associated counter and rejects an oversized programmatic value', async () => {
    const { user } = form();
    await complete(user);
    const message = screen.getByLabelText('Message (optional)');
    expect(message).toHaveAttribute('maxlength', '2000');
    await user.type(message, 'Hello');
    expect(message).toHaveAccessibleDescription('5 / 2,000 characters');
    fireEvent.change(message, { target: { value: 'a'.repeat(2001) } });
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    expect(message).toHaveAttribute('aria-invalid', 'true');
  });

  it('shows calm throttling feedback and retains the in-memory draft', async () => {
    server.use(
      http.post('/api/enquiries', () =>
        HttpResponse.json(
          { error: { code: 'rate_limited', message: 'raw throttle content' } },
          { status: 429 },
        ),
      ),
    );
    const { user } = form();
    await complete(user);
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    expect(
      await screen.findByText('Enquiries are temporarily limited. Please try again later.'),
    ).toHaveFocus();
    expect(screen.getByLabelText('Name')).toHaveValue('Example Visitor');
    expect(screen.queryByText('raw throttle content')).toBeNull();
  });

  it('associates server validation with known fields without displaying arbitrary messages', async () => {
    server.use(
      http.post('/api/enquiries', () =>
        HttpResponse.json(
          {
            error: {
              code: 'validation_error',
              message: 'raw',
              fields: { email: 'raw private echo' },
            },
          },
          { status: 422 },
        ),
      ),
    );
    const { user } = form();
    await complete(user);
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    await screen.findByText('Please check your enquiry details and try again.');
    expect(screen.getByLabelText('Work email')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.queryByText('raw private echo')).toBeNull();
  });

  it('stops admission when the installation disables enquiries during a visit', async () => {
    server.use(http.post('/api/enquiries', () => new HttpResponse(null, { status: 404 })));
    const { user } = form();
    await complete(user);
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    expect(
      await screen.findByText('This installation is not accepting enquiries at the moment.'),
    ).toHaveFocus();
    expect(screen.queryByRole('button', { name: 'Send enquiry' })).toBeNull();
  });

  it('does not refresh or replay a public request after a 401', async () => {
    const refresh = vi.spyOn(authApi, 'refreshSession');
    const post = vi.fn();
    server.use(
      http.post('/api/enquiries', () => {
        post();
        return new HttpResponse(null, { status: 401 });
      }),
    );
    const { user } = form();
    await complete(user);
    await user.click(screen.getByRole('button', { name: 'Send enquiry' }));
    expect(
      await screen.findByText(
        'We could not confirm receipt of your enquiry. Please try again later.',
      ),
    ).toHaveFocus();
    expect(post).toHaveBeenCalledTimes(1);
    expect(refresh).not.toHaveBeenCalled();
  });

  it('does not save drafts when the form unmounts or reloads', async () => {
    const stored = vi.spyOn(Storage.prototype, 'setItem');
    const first = form();
    await first.user.type(screen.getByLabelText('Name'), 'Unsaved name');
    first.unmount();
    form();
    expect(screen.getByLabelText('Name')).toHaveValue('');
    expect(stored).not.toHaveBeenCalled();
  });

  it('prevents duplicate requests while submitting and aborts on navigation', async () => {
    let signal: AbortSignal | undefined;
    let finish: (() => void) | undefined;
    const post = vi.fn();
    const pending = new Promise<void>((resolve) => {
      finish = resolve;
    });
    server.use(
      http.post('/api/enquiries', async ({ request }) => {
        post();
        signal = request.signal;
        await pending;
        return HttpResponse.json({ message: 'ok' }, { status: 202 });
      }),
    );
    const { user, unmount } = form();
    await complete(user);
    await user.dblClick(screen.getByRole('button', { name: 'Send enquiry' }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
    expect(screen.getByRole('button', { name: 'Send enquiry' })).toHaveAttribute(
      'aria-busy',
      'true',
    );
    unmount();
    await waitFor(() => expect(signal?.aborted).toBe(true));
    finish?.();
  });

  it('has no detectable accessibility violations', async () => {
    form();
    await expectNoAxeViolations();
  });
});

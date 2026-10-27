import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import type { TermsStatus } from '@/lib/api/terms';
import { useAuthStore } from '@/stores/auth';
import { expectNoAxeViolations } from '@/test/axe';
import { installDialogStub } from '@/test/dialogStub';
import { plainUser, tokenFor } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

import { TermsAcceptanceDialog } from './TermsAcceptanceDialog';

installDialogStub();

const CURRENT = '2026-10-27';
const status = (accepted: string | null, current = CURRENT): TermsStatus => ({
  current_version: current,
  accepted_version: accepted,
  accepted_at: accepted === null ? null : `${accepted}T09:00:00Z`,
  acceptance_required: accepted !== current,
});

function signIn(terms: TermsStatus | undefined) {
  useAuthStore
    .getState()
    .setSession(tokenFor({ ...plainUser, ...(terms === undefined ? {} : { terms }) }));
}

describe('TermsAcceptanceDialog', () => {
  it.each([
    ['accepted the current version', status(CURRENT)],
    ['a response without terms', undefined],
  ])('stays closed for an account that has %s', (_, terms) => {
    signIn(terms);
    render(<TermsAcceptanceDialog />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('blocks until accepted, then records the shown version and closes', async () => {
    signIn(status('2026-01-01'));
    let body: unknown = null;
    server.use(
      http.post('/api/me/terms-acceptance', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(status(CURRENT));
      }),
    );
    render(<TermsAcceptanceDialog />);
    const dialog = screen.getByRole('dialog', { name: 'The Terms have changed' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAccessibleDescription(/version of 27 October 2026/);
    expect(screen.getByRole('heading', { name: 'The Terms have changed' })).toHaveFocus();
    for (const [name, href] of [
      ['Terms (opens in a new tab)', '/terms'],
      ['Acceptable Use Policy (opens in a new tab)', '/acceptable-use'],
    ] as const) {
      const link = within(dialog).getByRole('link', { name });
      expect(link).toHaveAttribute('href', href);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    }
    await expectNoAxeViolations(dialog);
    const cancel = new Event('cancel', { cancelable: true });
    fireEvent(dialog, cancel);
    fireEvent.keyDown(dialog, { key: 'Escape' });
    expect(cancel.defaultPrevented).toBe(true);
    expect(dialog).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole('button', { name: 'Accept and continue' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(body).toEqual({ version: CURRENT });
    expect(useAuthStore.getState().user?.terms?.acceptance_required).toBe(false);
  });

  it('asks a never-accepted account to accept and offers sign-out instead', async () => {
    signIn(status(null));
    render(<TermsAcceptanceDialog />);
    screen.getByRole('dialog', { name: 'Accept the Terms to continue' });
    await userEvent.setup().click(screen.getByRole('button', { name: 'Sign out' }));
    expect(useAuthStore.getState().status).toBe('anonymous');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('keeps the dialog open on failure and shows a newer version after a conflict', async () => {
    signIn(status(null));
    server.use(
      http.post('/api/me/terms-acceptance', () =>
        apiError(409, 'conflict', 'The terms have changed. Review the current version.'),
      ),
      http.get('/api/me', () =>
        HttpResponse.json({ ...plainUser, terms: status(null, '2026-12-01') }),
      ),
    );
    render(<TermsAcceptanceDialog />);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Accept and continue' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The terms have changed');
    expect(screen.getByRole('dialog')).toHaveAccessibleDescription(/version of 1 December 2026/);
    expect(useAuthStore.getState().user?.terms?.current_version).toBe('2026-12-01');
  });

  it('ignores an acceptance that completes after a different account signs in', async () => {
    signIn(status(null));
    let release: () => void = () => undefined;
    const pending = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post('/api/me/terms-acceptance', async () => {
        await pending;
        return HttpResponse.json(status(CURRENT));
      }),
    );
    render(<TermsAcceptanceDialog />);
    fireEvent.click(screen.getByRole('button', { name: 'Accept and continue' }));
    signIn(status(null));
    release();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: 'Accept and continue' })).not.toHaveAttribute(
        'aria-busy',
        'true',
      ),
    );
    expect(useAuthStore.getState().user?.terms?.acceptance_required).toBe(true);
  });

  it('is mounted by the research shell for an account that must accept', async () => {
    signIn(status(null));
    renderApp('/account?section=security');
    expect(
      await screen.findByRole('dialog', { name: 'Accept the Terms to continue' }),
    ).toBeInTheDocument();
  });
});

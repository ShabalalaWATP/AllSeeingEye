import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as download from '@/lib/download';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor, USER_PASSWORD } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const ownId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const otherId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const syntheticCodes = ['1234567890abcdef12345678', 'abcdef1234567890abcdef12'];
const sessions = [ownId, otherId].map((id, index) => ({
  id,
  current: index === 0,
  created_at: '2026-09-01T12:00:00Z',
  last_active_at: '2026-09-06T12:00:00Z',
  expires_at: '2026-10-01T12:00:00Z',
  user_agent: index === 0 ? 'Current test browser' : 'Other test browser',
  ip: '127.0.0.1',
}));

beforeEach(() => {
  server.use(
    http.get('/api/me/sessions', () => HttpResponse.json({ items: sessions, truncated: false })),
    http.get('/api/auth/mfa/recovery', () => HttpResponse.json({ remaining: 0, available: true })),
    http.get('/api/auth/mfa', () =>
      HttpResponse.json({
        methods: ['authenticator'],
        available_methods: ['authenticator'],
        required: false,
      }),
    ),
  );
});

async function openRecovery(user: ReturnType<typeof renderApp>['user']) {
  await user.click(await screen.findByRole('button', { name: 'Create recovery codes' }));
  await user.type(screen.getByLabelText('Current password for recovery codes'), USER_PASSWORD);
  await user.type(screen.getByLabelText('Authenticator code for recovery codes'), '123456');
}

describe('personal session controls', () => {
  it('confirms all-other revocation and preserves the current account', async () => {
    let requests = 0;
    server.use(
      http.post('/api/me/sessions/revoke-others', () => {
        requests += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await screen.findByText('Other test browser');
    await user.click(screen.getByRole('button', { name: 'Sign out other devices' }));
    expect(requests).toBe(0);
    expect(screen.getByText(/This session will stay signed in/)).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(requests).toBe(0);
    await user.click(screen.getByRole('button', { name: 'Sign out other devices' }));
    await user.click(screen.getByRole('button', { name: 'Confirm sign-out' }));
    expect(await screen.findByText('Other sessions have been signed out.')).toBeVisible();
    expect(requests).toBe(1);
    expect(useAuthStore.getState().user?.id).toBe(plainUser.id);
  });

  it('revokes only the selected other session and clears state for the current session', async () => {
    const deleted: string[] = [];
    server.use(
      http.delete('/api/me/sessions/:id', ({ params }) => {
        deleted.push(String(params.id));
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user, router } = renderApp('/account?section=security', 'user');
    await user.click(await screen.findByRole('button', { name: /^Sign out session$/ }));
    await user.click(screen.getByRole('button', { name: 'Confirm sign-out' }));
    await screen.findByText('The selected session has been signed out.');
    expect(deleted).toEqual([otherId]);
    expect(useAuthStore.getState().status).toBe('authenticated');
    await user.click(screen.getByRole('button', { name: 'Sign out this session' }));
    await user.click(screen.getByRole('button', { name: 'Confirm sign-out' }));
    await waitFor(() => expect(useAuthStore.getState().status).toBe('anonymous'));
    expect(deleted).toEqual([otherId, ownId]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  });

  it('keeps the session on a failed revocation and allows retry', async () => {
    server.use(
      http.post('/api/me/sessions/revoke-others', () =>
        apiError(422, 'invalid_request', 'Unable to revoke these sessions.'),
      ),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await screen.findByText('Other test browser');
    await user.click(screen.getByRole('button', { name: 'Sign out other devices' }));
    await user.click(screen.getByRole('button', { name: 'Confirm sign-out' }));
    expect(await screen.findByText('Unable to revoke these sessions.')).toBeVisible();
    expect(useAuthStore.getState().status).toBe('authenticated');
    expect(screen.getByRole('button', { name: 'Confirm sign-out' })).toBeEnabled();
  });
});

describe('personal recovery codes', () => {
  it('obtains an email challenge before generating codes and sends its bound proof', async () => {
    let challengeBody: unknown;
    let generateBody: unknown;
    server.use(
      http.get('/api/auth/mfa', () =>
        HttpResponse.json({ methods: ['email'], available_methods: ['email'], required: false }),
      ),
      http.post('/api/auth/mfa/recovery/challenge', async ({ request }) => {
        challengeBody = await request.json();
        return HttpResponse.json({
          mfa_required: true,
          challenge_token: 'synthetic-recovery-challenge',
          expires_at: '2026-09-06T12:10:00Z',
          methods: ['email'],
          enrollment_required: false,
          email_sent: true,
        });
      }),
      http.post('/api/auth/mfa/recovery/generate', async ({ request }) => {
        generateBody = await request.json();
        return HttpResponse.json({ codes: syntheticCodes });
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await user.click(await screen.findByRole('button', { name: 'Create recovery codes' }));
    await user.type(screen.getByLabelText('Current password for recovery codes'), USER_PASSWORD);
    expect(screen.queryByLabelText('Email code for recovery codes')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Send verification email' }));
    await user.type(await screen.findByLabelText('Email code for recovery codes'), '654321');
    expect(challengeBody).toEqual({ password: USER_PASSWORD });
    expect(generateBody).toBeUndefined();
    await user.click(screen.getByRole('button', { name: 'Generate new codes' }));
    await screen.findByRole('list', { name: 'New recovery codes' });
    expect(generateBody).toEqual({
      password: USER_PASSWORD,
      method: 'email',
      code: '654321',
      challenge_token: 'synthetic-recovery-challenge',
    });
  });

  it('displays a generated set once and downloads the exact codes before hiding them', async () => {
    const save = vi.spyOn(download, 'saveTextFile').mockImplementation(() => undefined);
    let body: unknown;
    server.use(
      http.post('/api/auth/mfa/recovery/generate', async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ codes: syntheticCodes });
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await openRecovery(user);
    await user.click(screen.getByRole('button', { name: 'Generate new codes' }));
    const list = await screen.findByRole('list', { name: 'New recovery codes' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(body).toEqual({
      password: USER_PASSWORD,
      method: 'authenticator',
      code: '123456',
      challenge_token: null,
    });
    await user.click(screen.getByRole('button', { name: 'Download recovery codes' }));
    expect(save).toHaveBeenCalledWith(
      'ase-recovery-codes.txt',
      expect.stringContaining(syntheticCodes.join('\n')),
    );
    await user.click(screen.getByRole('button', { name: 'I have saved my codes' }));
    expect(screen.queryByRole('list', { name: 'New recovery codes' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Download recovery codes' }),
    ).not.toBeInTheDocument();
    expect(useAuthStore.getState().status).toBe('authenticated');
  });

  it('retains proof inputs on an invalid proof and clears them on cancel', async () => {
    server.use(
      http.post('/api/auth/mfa/recovery/generate', () =>
        apiError(422, 'invalid_request', 'Verification failed. Try again.'),
      ),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await openRecovery(user);
    await user.click(screen.getByRole('button', { name: 'Generate new codes' }));
    expect(await screen.findByText('Verification failed. Try again.')).toBeVisible();
    expect(screen.getByLabelText('Current password for recovery codes')).toHaveValue(USER_PASSWORD);
    expect(screen.getByLabelText('Authenticator code for recovery codes')).toHaveValue('123456');
    expect(useAuthStore.getState().status).toBe('authenticated');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    await user.click(screen.getByRole('button', { name: 'Create recovery codes' }));
    expect(screen.getByLabelText('Current password for recovery codes')).toHaveValue('');
    expect(screen.getByLabelText('Authenticator code for recovery codes')).toHaveValue('');
  });

  it('does not reveal delayed codes after the signed-in identity changes', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let started = false;
    server.use(
      http.post('/api/auth/mfa/recovery/generate', async () => {
        started = true;
        await gate;
        return HttpResponse.json({ codes: syntheticCodes });
      }),
    );
    const { user } = renderApp('/account?section=security', 'user');
    await openRecovery(user);
    await user.click(screen.getByRole('button', { name: 'Generate new codes' }));
    await waitFor(() => expect(started).toBe(true));
    act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: otherId })));
    await act(async () => {
      release();
      await gate;
    });
    await screen.findByRole('button', { name: 'Create recovery codes' });
    expect(screen.queryByRole('list', { name: 'New recovery codes' })).not.toBeInTheDocument();
    expect(useAuthStore.getState().user?.id).toBe(otherId);
  });
});

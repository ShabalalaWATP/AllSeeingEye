import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor, USER_PASSWORD } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const otherId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const kinds = ['single session', 'other sessions', 'generate codes', 'email challenge'] as const;

describe('identity-bound account mutations', () => {
  it.each(
    kinds.flatMap((kind) => [
      { kind, unmountFirst: false },
      { kind, unmountFirst: true },
    ]),
  )(
    'aborts $kind on identity change (unmount first: $unmountFirst) before a delayed 401 retries',
    async ({ kind, unmountFirst }) => {
      let release: () => void = () => undefined;
      const gate = new Promise<void>((resolve) => {
        release = resolve;
      });
      let calls = 0;
      let refreshes = 0;
      let requestSignal: AbortSignal | undefined;
      const delayed = async ({ request }: { request: Request }) => {
        calls += 1;
        requestSignal = request.signal;
        await gate;
        return apiError(401, 'unauthenticated', 'Old session expired.');
      };
      const method = kind === 'email challenge' ? 'email' : 'authenticator';
      server.use(
        http.get('/api/auth/mfa', () =>
          HttpResponse.json({ methods: [method], available_methods: [method], required: false }),
        ),
        http.get('/api/auth/mfa/recovery', () =>
          HttpResponse.json({ available: true, remaining: 0 }),
        ),
        http.get('/api/me/sessions', () =>
          HttpResponse.json({
            truncated: false,
            items: [
              {
                id: otherId,
                current: false,
                created_at: '2026-09-01T12:00:00Z',
                last_active_at: '2026-09-01T12:00:00Z',
                expires_at: '2026-10-01T12:00:00Z',
                user_agent: 'Other browser',
                ip: null,
              },
            ],
          }),
        ),
        http.delete('/api/me/sessions/:id', delayed),
        http.post('/api/me/sessions/revoke-others', delayed),
        http.post('/api/auth/mfa/recovery/generate', delayed),
        http.post('/api/auth/mfa/recovery/challenge', delayed),
        http.post('/api/auth/refresh', () => {
          refreshes += 1;
          return HttpResponse.json(tokenFor({ ...plainUser, id: otherId }));
        }),
      );
      const { user, unmount } = renderApp('/account?section=security', 'user');
      if (kind === 'single session' || kind === 'other sessions') {
        await screen.findByText('Other browser');
        await user.click(
          screen.getByRole('button', {
            name: kind === 'single session' ? /^Sign out session$/ : 'Sign out other devices',
          }),
        );
        await user.click(screen.getByRole('button', { name: 'Confirm sign-out' }));
      } else {
        await user.click(await screen.findByRole('button', { name: 'Create recovery codes' }));
        await user.type(
          screen.getByLabelText('Current password for recovery codes'),
          USER_PASSWORD,
        );
        if (kind === 'generate codes')
          await user.type(screen.getByLabelText('Authenticator code for recovery codes'), '123456');
        await user.click(
          screen.getByRole('button', {
            name: kind === 'generate codes' ? 'Generate new codes' : 'Send verification email',
          }),
        );
      }
      await waitFor(() => expect(calls).toBe(1));
      if (unmountFirst) {
        unmount();
        expect(requestSignal?.aborted).toBe(true);
      }
      act(() => useAuthStore.getState().setSession(tokenFor({ ...plainUser, id: otherId })));
      expect(requestSignal?.aborted).toBe(true);
      await act(async () => {
        release();
        await gate;
      });
      if (!unmountFirst) await screen.findByRole('button', { name: 'Create recovery codes' });
      expect(calls).toBe(1);
      expect(refreshes).toBe(0);
      expect(useAuthStore.getState().user?.id).toBe(otherId);
      expect(screen.queryByRole('list', { name: 'New recovery codes' })).not.toBeInTheDocument();
    },
  );
});

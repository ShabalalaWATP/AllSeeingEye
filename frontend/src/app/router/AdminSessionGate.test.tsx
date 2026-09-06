import { act, fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { verifySession } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/errors';
import type { User } from '@/lib/api/schemas';
import { useAuthStore } from '@/stores/auth';
import { setVisibility } from '@/test/env';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';

import AdminSessionGate from './AdminSessionGate';

vi.mock('@/lib/api/auth', async (original) => ({
  ...(await original<typeof import('@/lib/api/auth')>()),
  verifySession: vi.fn(),
}));

function deferred() {
  let resolve!: (value: User) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<User>((accept, fail) => {
    resolve = accept;
    reject = fail;
  });
  return { promise, resolve, reject };
}

function mount() {
  useAuthStore.getState().setSession(tokenFor(adminUser));
  return render(
    <RouterProvider
      router={createMemoryRouter([
        {
          element: <AdminSessionGate />,
          children: [{ path: '/', element: <input aria-label="Private draft" /> }],
        },
      ])}
    />,
  );
}

afterEach(() => {
  vi.useRealTimers();
});

describe('fresh administrator session gate', () => {
  it('hides protected content until the captured session is verified', async () => {
    const request = deferred();
    vi.mocked(verifySession).mockReturnValueOnce(request.promise);
    mount();
    expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
    expect(screen.getByText('Verifying administrator access')).toBeVisible();
    expect(verifySession).toHaveBeenCalledWith('admin-access-token', expect.any(AbortSignal));
    await act(async () => {
      await Promise.resolve();
      request.resolve(adminUser);
    });
    expect(screen.getByLabelText('Private draft')).toBeVisible();
  });

  it('hides content after a network failure without logging out, and supports Retry', async () => {
    vi.mocked(verifySession)
      .mockResolvedValueOnce(adminUser)
      .mockRejectedValueOnce(new ApiError(0, 'network_error', 'Offline'))
      .mockResolvedValueOnce(adminUser);
    mount();
    await screen.findByLabelText('Private draft');
    await act(async () => {
      await Promise.resolve();
      window.dispatchEvent(new Event('focus'));
    });
    expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
    expect(useAuthStore.getState().status).toBe('authenticated');
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByLabelText('Private draft')).toBeVisible();
  });

  it.each(['user', 'inactive'] as const)(
    'revokes cached admin authority on fresh %s result',
    async (kind) => {
      const fresh =
        kind === 'user'
          ? { ...adminUser, role: 'user' as const }
          : { ...adminUser, is_active: false };
      vi.mocked(verifySession).mockResolvedValueOnce(fresh);
      mount();
      await screen.findByText('Administrator access required');
      expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
      if (kind === 'user') expect(useAuthStore.getState().user?.role).toBe('user');
      else expect(useAuthStore.getState().status).toBe('anonymous');
    },
  );

  it('clears only the matching expired session on401', async () => {
    vi.mocked(verifySession).mockRejectedValueOnce(new ApiError(401, 'unauthenticated', 'Expired'));
    mount();
    await screen.findByText('Administrator access required');
    expect(useAuthStore.getState().status).toBe('anonymous');
  });

  it.each(['success', 'failure'] as const)(
    'ignores late %s from a previous session',
    async (outcome) => {
      const older = deferred(),
        newer = deferred();
      vi.mocked(verifySession)
        .mockReturnValueOnce(older.promise)
        .mockReturnValueOnce(newer.promise);
      mount();
      const firstSignal = vi.mocked(verifySession).mock.calls[0]![1];
      const newAdmin = { ...adminUser, id: 'different-admin' };
      act(() => {
        useAuthStore.getState().setSession({ ...tokenFor(newAdmin), access_token: 'new-token' });
      });
      expect(firstSignal.aborted).toBe(true);
      await act(async () => {
        await Promise.resolve();
        if (outcome === 'success') older.resolve(plainUser);
        else older.reject(new ApiError(401, 'unauthenticated', 'Expired'));
      });
      expect(useAuthStore.getState().accessToken).toBe('new-token');
      expect(useAuthStore.getState().user?.id).toBe(newAdmin.id);
      expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
      await act(async () => {
        await Promise.resolve();
        newer.resolve(newAdmin);
      });
      expect(screen.getByLabelText('Private draft')).toBeVisible();
    },
  );

  it('requires another verification after the same account receives a new token', async () => {
    const pending = deferred();
    vi.mocked(verifySession).mockResolvedValueOnce(adminUser).mockReturnValueOnce(pending.promise);
    mount();
    await screen.findByLabelText('Private draft');
    act(() => {
      useAuthStore.getState().setSession({ ...tokenFor(adminUser), access_token: 'rotated' });
    });
    expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
    await act(async () => {
      await Promise.resolve();
      pending.resolve(adminUser);
    });
    expect(screen.getByLabelText('Private draft')).toBeVisible();
  });

  it('checks every30 seconds while visible, preserves drafts during checks, and deduplicates focus', async () => {
    vi.useFakeTimers();
    const second = deferred();
    vi.mocked(verifySession)
      .mockResolvedValueOnce(adminUser)
      .mockReturnValueOnce(second.promise)
      .mockResolvedValue(adminUser);
    mount();
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    fireEvent.change(screen.getByLabelText('Private draft'), { target: { value: 'Unsaved' } });
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(30_000);
    });
    expect(verifySession).toHaveBeenCalledTimes(2);
    fireEvent.focus(window);
    expect(verifySession).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText('Private draft')).toHaveValue('Unsaved');
    await act(async () => {
      await Promise.resolve();
      second.resolve(adminUser);
    });
    act(() => {
      setVisibility('hidden');
    });
    await act(async () => {
      await Promise.resolve();
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(verifySession).toHaveBeenCalledTimes(2);
    await act(async () => {
      await Promise.resolve();
      setVisibility('visible');
    });
    expect(verifySession).toHaveBeenCalledTimes(3);
  });

  it('aborts and ignores results after unmount', async () => {
    const request = deferred();
    vi.mocked(verifySession).mockReturnValueOnce(request.promise);
    const view = mount();
    const signal = vi.mocked(verifySession).mock.calls[0]![1];
    view.unmount();
    expect(signal.aborted).toBe(true);
    await act(async () => {
      await Promise.resolve();
      request.resolve({ ...adminUser, role: 'user' });
    });
    expect(useAuthStore.getState().user?.role).toBe('admin');
  });

  it('does not adopt a different identity returned for the captured token', async () => {
    vi.mocked(verifySession).mockResolvedValueOnce(plainUser);
    mount();
    await screen.findByRole('button', { name: 'Retry' });
    expect(useAuthStore.getState().user?.id).toBe(adminUser.id);
    expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
  });

  it('times out a stalled verification without treating it as a logout', async () => {
    vi.useFakeTimers();
    vi.mocked(verifySession).mockImplementationOnce(
      (_token, signal) =>
        new Promise((_resolve, reject) => {
          signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
        }),
    );
    mount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    expect(screen.getByRole('button', { name: 'Retry' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Return to research' })).toHaveAttribute('href', '/');
    expect(screen.queryByLabelText('Private draft')).not.toBeInTheDocument();
    expect(useAuthStore.getState().status).toBe('authenticated');
  });
});

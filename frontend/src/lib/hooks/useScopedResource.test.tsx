import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import {
  invalidateWorkspaceAccess,
  scopedMutation,
  workspaceRevision,
} from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { manager, roster, team } from '@/test/fixtures.teams';
import { server } from '@/test/server';

import { useScopedResource } from './useScopedResource';
import { useWorkspaces } from './useWorkspaces';

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

describe('Scoped resources', () => {
  it('hides the previous record when a route loader changes', async () => {
    const first = vi.fn().mockResolvedValue('first record');
    const second = deferred<string>();
    const next = () => second.promise;
    const { result, rerender } = renderHook(({ loader }) => useScopedResource(loader), {
      initialProps: { loader: first as () => Promise<string> },
    });
    await waitFor(() => expect(result.current.data).toBe('first record'));
    rerender({ loader: next });
    expect(result.current.data).toBeNull();
    await act(async () => {
      second.resolve('second record');
      await second.promise;
    });
    expect(result.current.data).toBe('second record');
  });

  it('hides prior identity data and rejects late responses and old local setters', async () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const old = deferred<string>();
    const next = deferred<string>();
    const loader = vi.fn().mockReturnValueOnce(old.promise).mockReturnValueOnce(next.promise);
    const { result } = renderHook(() => useScopedResource<string>(loader));
    const oldSetter = result.current.setData;
    act(() => useAuthStore.getState().setSession(tokenFor(adminUser)));
    expect(result.current.data).toBeNull();
    await act(async () => {
      old.resolve('private old result');
      await old.promise;
    });
    expect(result.current.data).toBeNull();
    act(() => oldSetter('old local update'));
    expect(result.current.data).toBeNull();
    await act(async () => {
      next.resolve('current result');
      await next.promise;
    });
    expect(result.current.data).toBe('current result');
  });

  it('clears access-revoked data and prevents superseded loads from restoring it', async () => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const stale = deferred<string>();
    const loader = vi
      .fn()
      .mockResolvedValueOnce('team secret')
      .mockReturnValueOnce(stale.promise)
      .mockRejectedValueOnce(new ApiError(403, 'forbidden', 'Access removed.'));
    const { result } = renderHook(() => useScopedResource<string>(loader));
    await waitFor(() => expect(result.current.data).toBe('team secret'));
    act(() => {
      void result.current.reload();
    });
    act(() => invalidateWorkspaceAccess());
    expect(result.current.data).toBeNull();
    await waitFor(() => expect(result.current.error?.status).toBe(403));
    await act(async () => {
      stale.resolve('team secret');
      await stale.promise;
    });
    expect(result.current.data).toBeNull();
  });

  it('invalidates denied mutations and drops results completed under a different account', async () => {
    const before = workspaceRevision();
    await expect(
      scopedMutation(() => Promise.reject(new ApiError(404, 'not_found', 'Gone.'))),
    ).rejects.toMatchObject({ status: 404 });
    expect(workspaceRevision()).toBe(before + 1);
    useAuthStore.getState().setSession(tokenFor(plainUser));
    const pending = deferred<string>();
    const outcome = scopedMutation(() => pending.promise);
    useAuthStore.getState().setSession(tokenFor(adminUser));
    pending.resolve('private result');
    await expect(outcome).rejects.toMatchObject({ code: 'access_changed' });
  });
});

describe('Workspace authority', () => {
  it('lets designated managers manage every contribution in teams they currently lead', async () => {
    useAuthStore.getState().setSession(tokenFor(manager));
    let detail = structuredClone(roster);
    server.use(
      http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
      http.get('/api/teams/:id', () => HttpResponse.json(detail)),
    );
    const { result } = renderHook(() => useWorkspaces());
    await waitFor(() => expect(result.current.teams).toHaveLength(1));
    const ordinary = { team_id: team.id, created_by: plainUser.id };
    expect(result.current.canManage(ordinary)).toBe(true);
    expect(result.current.canAcknowledge(team.id)).toBe(true);
    expect(result.current.canManage({ ...ordinary, team_id: null })).toBe(false);
    expect(result.current.canManage({ ...ordinary, created_by: adminUser.id })).toBe(true);
    expect(
      result.current.canManage({
        ...ordinary,
        created_by: '99999999-9999-4999-8999-999999999999',
      }),
    ).toBe(true);
    detail = { ...detail, members: detail.members.map((item) => ({ ...item, role: 'member' })) };
    await act(async () => {
      await result.current.reload();
    });
    expect(result.current.canManage(ordinary)).toBe(false);
    await waitFor(() => expect(result.current.canAcknowledge(team.id)).toBe(true));
    detail = { ...detail, members: detail.members.filter((item) => item.user_id !== manager.id) };
    await act(async () => {
      await result.current.reload();
    });
    expect(result.current.teams).toHaveLength(0);
    expect(result.current.canAcknowledge(team.id)).toBe(false);
    expect(result.current.canManage({ team_id: team.id, created_by: manager.id })).toBe(false);
  });
});

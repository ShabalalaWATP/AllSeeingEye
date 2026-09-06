import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { tokenFor } from '@/test/fixtures';
import { manager, roster, team } from '@/test/fixtures.teams';
import { server } from '@/test/server';

import { useScopedResource } from './useScopedResource';
import { useWorkspaces } from './useWorkspaces';

describe('Shared workspace refresh', () => {
  it.each(['removed', 'archived', 'membership removed', 'inactive', 'denied'])(
    'hides loaded private reports when focus detects access %s',
    async (change) => {
      useAuthStore.getState().setSession(tokenFor(manager));
      let revoked = false;
      let requests = 0;
      server.use(
        http.get('/api/teams', () => {
          requests += 1;
          return HttpResponse.json({
            items:
              revoked && change === 'removed'
                ? []
                : [
                    {
                      ...team,
                      is_active: !(revoked && change === 'archived'),
                    },
                  ],
          });
        }),
        http.get('/api/teams/:id', () => {
          if (revoked && change === 'denied') return new HttpResponse(null, { status: 403 });
          return HttpResponse.json({
            ...roster,
            members: roster.members
              .filter(
                (member) =>
                  !(revoked && change === 'membership removed' && member.user_id === manager.id),
              )
              .map((member) => ({
                ...member,
                is_active: !(revoked && change === 'inactive' && member.user_id === manager.id),
              })),
          });
        }),
      );
      const report = vi
        .fn()
        .mockResolvedValueOnce('private report body')
        .mockRejectedValue(new ApiError(403, 'forbidden', 'Access removed.'));
      const { result } = renderHook(() => ({
        first: useWorkspaces(),
        second: useWorkspaces(),
        report: useScopedResource<string>(report),
      }));
      await waitFor(() => expect(result.current.first.teams).toHaveLength(1));
      await waitFor(() => expect(result.current.second.teams).toHaveLength(1));
      expect(result.current.report.data).toBe('private report body');
      expect(requests).toBe(1);
      const revision = workspaceRevision();
      revoked = true;
      act(() => {
        window.dispatchEvent(new Event('focus'));
      });
      await waitFor(() => expect(result.current.report.error?.status).toBe(403));
      await waitFor(() => expect(result.current.first.loading).toBe(false));
      expect(result.current.report.data).toBeNull();
      expect(result.current.first.teams).toHaveLength(0);
      expect(workspaceRevision()).toBe(revision + 1);
      expect(report).toHaveBeenCalledTimes(2);
      expect(requests).toBe(3); // Initial, focus, and one shared load after invalidation.
      act(() => {
        window.dispatchEvent(new Event('focus'));
      });
      await waitFor(() => expect(requests).toBe(4));
      expect(workspaceRevision()).toBe(revision + 1);
      expect(report).toHaveBeenCalledTimes(2);
    },
  );

  it.each(['membership', 'account'])(
    'keeps unchanged pages visible during timer checks and detects a changed %s role',
    async (kind) => {
      useAuthStore.getState().setSession(tokenFor(manager));
      let detail = structuredClone(roster);
      let release: (() => void) | undefined;
      let held: Promise<void> | undefined;
      let reads = 0;
      const interval = vi.spyOn(window, 'setInterval');
      server.use(
        http.get('/api/teams', async () => {
          reads += 1;
          await held;
          return HttpResponse.json({ items: [team] });
        }),
        http.get('/api/teams/:id', () => HttpResponse.json(detail)),
      );
      const report = vi.fn().mockResolvedValue('readable report');
      const { result, unmount } = renderHook(() => ({
        workspaces: useWorkspaces(),
        report: useScopedResource<string>(report),
      }));
      await waitFor(() => expect(result.current.workspaces.teams).toHaveLength(1));
      const tick = interval.mock.calls.find((call) => call[1] === 60_000)?.[0];
      expect(typeof tick).toBe('function');
      const revision = workspaceRevision();
      held = new Promise<void>((resolve) => {
        release = resolve;
      });
      act(() => {
        if (typeof tick === 'function') tick();
      });
      await waitFor(() => expect(reads).toBe(2));
      expect(result.current.report.data).toBe('readable report');
      expect(result.current.workspaces.loading).toBe(false);
      expect(result.current.workspaces.teams).toHaveLength(1);
      await act(async () => {
        release?.();
        await held;
      });
      expect(workspaceRevision()).toBe(revision);
      expect(report).toHaveBeenCalledTimes(1);
      held = undefined;
      detail = {
        ...detail,
        members: detail.members.map((member) =>
          kind === 'membership'
            ? { ...member, role: 'member' }
            : { ...member, account_role: 'user' },
        ),
      };
      act(() => {
        if (typeof tick === 'function') tick();
      });
      await waitFor(() => expect(workspaceRevision()).toBe(revision + 1));
      await waitFor(() => expect(result.current.workspaces.loading).toBe(false));
      expect(
        result.current.workspaces.canManage({ created_by: team.created_by, team_id: team.id }),
      ).toBe(false);
      expect(report).toHaveBeenCalledTimes(2);
      unmount();
      interval.mockRestore();
    },
  );
});

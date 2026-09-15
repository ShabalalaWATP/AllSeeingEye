import { act, fireEvent, render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { TeamDashboard } from '@/lib/api/teamBoard';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { setVisibility } from '@/test/env';
import { boardPost, memberBoardCapabilities } from '@/test/fixtures.teamBoard';
import { team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { untilReal } from '@/test/realTime';
import { server } from '@/test/server';

import { TeamOverview } from './TeamOverview';

function dashboard(pinnedText: string): TeamDashboard {
  return {
    team: {
      id: team.id,
      name: team.name,
      description: null,
      is_active: true,
      role: 'member',
      member_count: 3,
    },
    pinned: [boardPost({ text: pinnedText, is_pinned: true })],
    unread_count: 0,
    recent_reports: [],
    upcoming_runs: [],
    action_items: [],
  };
}

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));
const until = untilReal;

function serve(respond: () => TeamDashboard | 403 | 500) {
  const calls: number[] = [];
  server.use(
    http.get(`/api/teams/${team.id}/dashboard`, () => {
      calls.push(Date.now());
      const next = respond();
      if (next === 403) return apiError(403, 'membership_required', 'Membership required.');
      if (next === 500) return apiError(500, 'server_error', 'Overview unavailable.');
      return HttpResponse.json(next);
    }),
    http.get(`/api/teams/${team.id}/ai-usage`, () => apiError(404, 'not_found', 'Not found.')),
  );
  return calls;
}

function renderOverview() {
  return render(
    <TeamOverview teamId={team.id} capabilities={memberBoardCapabilities} onTabChange={vi.fn()} />,
  );
}

describe('TeamOverview background refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
    setVisibility('visible');
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('refreshes every minute while visible and pauses while hidden', async () => {
    let current = dashboard('Monday orders');
    const calls = serve(() => current);
    renderOverview();
    await until(() => expect(screen.getByText('Monday orders')).toBeInTheDocument());
    current = dashboard('Tuesday orders');
    await advance(59_999);
    expect(calls).toHaveLength(1);
    await advance(1);
    await until(() => expect(screen.getByText('Tuesday orders')).toBeInTheDocument());
    act(() => setVisibility('hidden'));
    await advance(600_000);
    expect(calls).toHaveLength(2);
  });

  it('announces a failed refresh, keeps the last overview and recovers', async () => {
    let failing = false;
    const calls = serve(() => (failing ? 500 : dashboard('Monday orders')));
    renderOverview();
    await until(() => expect(screen.getByText('Monday orders')).toBeInTheDocument());
    failing = true;
    await advance(60_000);
    await until(() => expect(screen.getByText(/Automatic refresh failed/)).toBeInTheDocument());
    expect(screen.getByText('Monday orders')).toBeInTheDocument();
    failing = false;
    await advance(119_999);
    expect(calls).toHaveLength(2);
    await advance(1);
    await until(() =>
      expect(screen.queryByText(/Automatic refresh failed/)).not.toBeInTheDocument(),
    );
  });

  it('clears a failed first load once a background refresh succeeds', async () => {
    let failing = true;
    serve(() => (failing ? 500 : dashboard('Monday orders')));
    renderOverview();
    await until(() => expect(screen.getByText('Overview unavailable.')).toBeInTheDocument());
    failing = false;
    await advance(60_000);
    await until(() => expect(screen.getByText('Monday orders')).toBeInTheDocument());
    expect(screen.queryByText('Overview unavailable.')).not.toBeInTheDocument();
  });

  it('stops refreshing and hides the overview when access is removed', async () => {
    let revoked = false;
    const calls = serve(() => (revoked ? 403 : dashboard('Monday orders')));
    renderOverview();
    await until(() => expect(screen.getByText('Monday orders')).toBeInTheDocument());
    revoked = true;
    await advance(60_000);
    await until(() => expect(screen.getByText('Team access changed')).toBeInTheDocument());
    expect(screen.queryByText('Monday orders')).not.toBeInTheDocument();
    await advance(900_000);
    expect(calls).toHaveLength(2);
    revoked = false;
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await until(() => expect(screen.getByText('Monday orders')).toBeInTheDocument());
    expect(screen.queryByText('Team access changed')).not.toBeInTheDocument();
  });
  it('aborts an in-flight refresh quietly when the overview unmounts', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let refreshSignal: AbortSignal | null = null;
    const calls = serve(() => dashboard('Monday orders'));
    server.use(
      http.get(`/api/teams/${team.id}/dashboard`, async ({ request }) => {
        calls.push(Date.now());
        if (calls.length > 1) {
          refreshSignal = request.signal;
          await gate;
        }
        return HttpResponse.json(dashboard('Monday orders'));
      }),
    );
    const view = renderOverview();
    await until(() => expect(screen.getByText('Monday orders')).toBeInTheDocument());
    await advance(60_000);
    await until(() => expect(refreshSignal).not.toBeNull());
    view.unmount();
    expect((refreshSignal as AbortSignal | null)?.aborted).toBe(true);
    release();
    await advance(600_000);
    expect(calls).toHaveLength(2);
  });
});

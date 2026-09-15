import { act, fireEvent, render, screen } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { setVisibility } from '@/test/env';
import {
  boardBase,
  boardPage,
  boardPost,
  memberBoardCapabilities,
  renderTeamBoard,
  serveBoard,
} from '@/test/fixtures.teamBoard';
import { manager, team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { untilReal } from '@/test/realTime';
import { server } from '@/test/server';

import { TeamBoard } from './TeamBoard';

const mine = boardPost({ text: 'My handover', created_at: '2026-09-15T09:00:00Z' });
const arrival = boardPost({
  id: '66666666-6666-4666-8666-666666666667',
  author_id: manager.id,
  author_name: manager.display_name,
  text: 'Fresh arrival',
  created_at: '2026-09-15T11:00:00Z',
});

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));
const renderBoard = () => {
  renderTeamBoard(plainUser.id, memberBoardCapabilities);
};

/** A promise the test resolves to release a held MSW response. */
function hold() {
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { gate, release };
}

describe('TeamBoard refresh races', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
    setVisibility('visible');
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('never applies an older revision over a newer local copy', async () => {
    let current = boardPage([{ ...mine, text: 'Newest text', revision: 3 }]);
    serveBoard(() => current);
    renderBoard();
    await untilReal(() => expect(screen.getByText('Newest text')).toBeInTheDocument());
    current = boardPage([arrival, { ...mine, text: 'Stale replica', revision: 2 }]);
    await advance(30_000);
    await untilReal(() => expect(screen.getByText('Fresh arrival')).toBeInTheDocument());
    expect(screen.getByText('Newest text')).toBeInTheDocument();
    expect(screen.queryByText('Stale replica')).not.toBeInTheDocument();
  });

  it('does not send a read receipt while the page is hidden', async () => {
    setVisibility('hidden');
    const { reads } = serveBoard(() => boardPage([mine], { unread: 2 }));
    renderBoard();
    await untilReal(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    await advance(60_000);
    expect(reads).toEqual([]);
  });

  it('skips a refresh tick while a post is still being saved', async () => {
    const { gate, release } = hold();
    const { requests } = serveBoard(() => boardPage([mine]));
    server.use(
      http.post(`${boardBase}/posts`, async () => {
        await gate;
        return HttpResponse.json(arrival);
      }),
    );
    renderBoard();
    await untilReal(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('New board post'), { target: { value: 'Update' } });
    fireEvent.click(screen.getByRole('button', { name: 'Post update' }));
    await advance(30_000);
    expect(requests).toHaveLength(1);
    await act(async () => {
      release();
      await gate;
    });
    await untilReal(() => expect(requests).toHaveLength(2));
    expect(screen.getByLabelText('New board post')).toHaveValue('');
  });

  it('abandons an in-flight refresh without a failure notice when a manual load starts', async () => {
    const { gate, release } = hold();
    let calls = 0;
    let refreshSignal: AbortSignal | null = null;
    server.use(
      http.get(`${boardBase}/posts`, async ({ request }) => {
        calls += 1;
        if (calls === 2) {
          refreshSignal = request.signal;
          await gate;
        }
        return calls === 1
          ? apiError(500, 'server_error', 'Board unavailable.')
          : HttpResponse.json(boardPage([mine]));
      }),
    );
    renderBoard();
    await untilReal(() => expect(screen.getByText('Board unavailable.')).toBeInTheDocument());
    await advance(30_000);
    await untilReal(() => expect(refreshSignal).not.toBeNull());
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    await untilReal(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    expect((refreshSignal as AbortSignal | null)?.aborted).toBe(true);
    release();
    await advance(0);
    expect(screen.queryByText(/Automatic refresh failed/)).not.toBeInTheDocument();
    expect(screen.queryByText('Board unavailable.')).not.toBeInTheDocument();
  });

  it('aborts an in-flight refresh when the board unmounts', async () => {
    const { gate, release } = hold();
    let refreshSignal: AbortSignal | null = null;
    let calls = 0;
    server.use(
      http.get(`${boardBase}/posts`, async ({ request }) => {
        calls += 1;
        if (calls > 1) {
          refreshSignal = request.signal;
          await gate;
        }
        return HttpResponse.json(boardPage([mine]));
      }),
    );
    const view = render(
      <TeamBoard
        teamId={team.id}
        teamName={team.name}
        userId={plainUser.id}
        capabilities={memberBoardCapabilities}
      />,
    );
    await untilReal(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    await advance(30_000);
    await untilReal(() => expect(refreshSignal).not.toBeNull());
    view.unmount();
    expect((refreshSignal as AbortSignal | null)?.aborted).toBe(true);
    release();
    await advance(300_000);
    expect(calls).toBe(2);
  });
});

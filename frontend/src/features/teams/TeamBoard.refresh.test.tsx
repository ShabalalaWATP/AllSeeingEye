import { act, fireEvent, screen, within } from '@testing-library/react';
import { http } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { setVisibility } from '@/test/env';
import {
  boardBase,
  boardPage,
  boardPost,
  managerBoardCapabilities,
  memberBoardCapabilities,
  renderTeamBoard,
  serveBoard,
} from '@/test/fixtures.teamBoard';
import { manager } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { untilReal } from '@/test/realTime';
import { server } from '@/test/server';

const mine = boardPost({ text: 'My handover', created_at: '2026-09-15T09:00:00Z' });
const other = boardPost({
  id: '66666666-6666-4666-8666-666666666662',
  author_id: adminUser.id,
  author_name: adminUser.display_name,
  text: 'Administrator guidance',
  created_at: '2026-09-15T08:00:00Z',
});
const older = boardPost({
  id: '66666666-6666-4666-8666-666666666665',
  author_id: adminUser.id,
  author_name: adminUser.display_name,
  text: 'Older post',
  created_at: '2026-09-14T09:00:00Z',
});
const arrival = boardPost({
  id: '66666666-6666-4666-8666-666666666667',
  author_id: manager.id,
  author_name: manager.display_name,
  text: 'Fresh arrival',
  created_at: '2026-09-15T11:00:00Z',
});

const advance = (ms: number) => act(() => vi.advanceTimersByTimeAsync(ms));
const until = untilReal;
const serve = serveBoard;
const renderBoard = (userId = plainUser.id, capabilities = memberBoardCapabilities) => {
  renderTeamBoard(userId, capabilities);
};
const type = (field: HTMLElement, value: string) => fireEvent.change(field, { target: { value } });

describe('TeamBoard background refresh', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] });
    setVisibility('visible');
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('refreshes every thirty seconds while visible, pauses while hidden and resumes', async () => {
    let current = boardPage([mine]);
    const { requests } = serve(() => current);
    renderBoard();
    await until(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    expect(requests).toHaveLength(1);
    current = boardPage([arrival, mine]);
    await advance(29_999);
    expect(requests).toHaveLength(1);
    await advance(1);
    expect(requests).toHaveLength(2);
    await until(() => expect(screen.getByText('Fresh arrival')).toBeInTheDocument());
    act(() => setVisibility('hidden'));
    await advance(300_000);
    expect(requests).toHaveLength(2);
    act(() => setVisibility('visible'));
    await until(() => expect(requests).toHaveLength(3));
  });

  it('stops refreshing and hides the board once membership is removed', async () => {
    let revoked = false;
    const { requests } = serve(() => (revoked ? 404 : boardPage([mine])));
    renderBoard();
    await until(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    revoked = true;
    await advance(30_000);
    await until(() => screen.getByText('Team access changed'));
    expect(screen.queryByText('My handover')).not.toBeInTheDocument();
    expect(screen.queryByText('No board updates yet')).not.toBeInTheDocument();
    await advance(900_000);
    expect(requests).toHaveLength(2);
  });

  it('announces a failed refresh, keeps the posts and backs off', async () => {
    let failing = false;
    const { requests } = serve(() => (failing ? 503 : boardPage([mine])));
    renderBoard();
    await until(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    failing = true;
    await advance(30_000);
    await until(() => screen.getByText(/Automatic refresh failed/));
    expect(screen.getByText('My handover')).toBeInTheDocument();
    await advance(59_999);
    expect(requests).toHaveLength(2);
    failing = false;
    await advance(1);
    expect(requests).toHaveLength(3);
    await until(() =>
      expect(screen.queryByText(/Automatic refresh failed/)).not.toBeInTheDocument(),
    );
  });

  it('keeps a composer draft and adds new posts at the top, marking them read', async () => {
    let current = boardPage([mine]);
    const { reads } = serve(() => current);
    renderBoard();
    await until(() => expect(screen.getByText('My handover')).toBeInTheDocument());
    type(screen.getByLabelText('New board post'), 'Half-written update');
    current = boardPage([arrival, mine], { unread: 1 });
    await advance(30_000);
    await until(() => expect(screen.getByText('Fresh arrival')).toBeInTheDocument());
    expect(screen.getByLabelText('New board post')).toHaveValue('Half-written update');
    expect(screen.getByText('1 new post added')).toBeInTheDocument();
    const articles = screen.getAllByRole('article');
    expect(within(articles[0]!).getByText('Fresh arrival')).toBeInTheDocument();
    await until(() => expect(reads).toEqual([{ last_seen_post_id: arrival.id }]));
    // A later refresh with nothing new sends no further receipt.
    await advance(30_000);
    expect(reads).toHaveLength(1);
    expect(screen.queryByText('1 new post added')).not.toBeInTheDocument();
  });

  it('keeps an open edit when the post changed elsewhere and leaves the clash to save time', async () => {
    let current = boardPage([mine]);
    const edits: unknown[] = [];
    serve(() => current);
    server.use(
      http.patch(`${boardBase}/posts/:postId`, async ({ request }) => {
        edits.push(await request.json());
        return apiError(409, 'conflict', 'This post changed. Reload it before saving again.');
      }),
    );
    renderBoard();
    fireEvent.click(await until(() => screen.getByRole('button', { name: 'Edit' })));
    type(screen.getByLabelText('Edit post'), 'My careful rewrite');
    current = boardPage([{ ...mine, text: 'Changed elsewhere', revision: 2 }]);
    await advance(30_000);
    await until(() => expect(screen.getByText('Changed elsewhere')).toBeInTheDocument());
    expect(screen.getByLabelText('Edit post')).toHaveValue('My careful rewrite');
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    await until(() => screen.getByText(/The board changed/));
    expect(edits).toEqual([{ text: 'My careful rewrite', expected_revision: 1 }]);
    expect(screen.getByLabelText('Edit post')).toHaveValue('My careful rewrite');
  });

  it('keeps an open moderation reason prompt through a refresh', async () => {
    useAuthStore.getState().setSession(tokenFor(manager));
    let current = boardPage([other]);
    serve(() => current);
    renderBoard(manager.id, managerBoardCapabilities);
    const card = within(
      await until(() => screen.getByRole('article', { name: `Post by ${adminUser.display_name}` })),
    );
    fireEvent.click(card.getByRole('button', { name: 'Remove' }));
    type(card.getByLabelText(/Moderation reason/), 'Contains an access code');
    current = boardPage([arrival, { ...other, is_pinned: true, revision: 2 }]);
    await advance(30_000);
    await until(() => expect(screen.getByText('Fresh arrival')).toBeInTheDocument());
    const refreshed = within(
      screen.getByRole('article', { name: `Post by ${adminUser.display_name}` }),
    );
    expect(refreshed.getByLabelText(/Moderation reason/)).toHaveValue('Contains an access code');
    expect(refreshed.getByText('Pinned')).toBeInTheDocument();
  });

  it('merges new posts without dropping older pages already loaded', async () => {
    let current = boardPage([mine], { nextOffset: 1 });
    const { requests } = serve(() => current, { ...boardPage([older]), offset: 1 });
    renderBoard();
    fireEvent.click(await until(() => screen.getByRole('button', { name: 'Load older posts' })));
    await until(() => expect(screen.getByText('Older post')).toBeInTheDocument());
    const answer = boardPost({
      id: '66666666-6666-4666-8666-666666666668',
      parent_id: arrival.id,
      text: 'Quick answer',
      created_at: '2026-09-15T11:05:00Z',
    });
    current = boardPage([arrival], { nextOffset: 1, replies: [answer] });
    await advance(30_000);
    await until(() => expect(screen.getByText('Fresh arrival')).toBeInTheDocument());
    expect(screen.getByText('2 new posts added')).toBeInTheDocument();
    expect(screen.getAllByRole('article').map((item) => item.textContent)).toEqual([
      expect.stringContaining('Fresh arrival'),
      expect.stringContaining('Quick answer'),
      expect.stringContaining('My handover'),
      expect.stringContaining('Older post'),
    ]);
    expect(screen.queryByRole('button', { name: 'Load older posts' })).not.toBeInTheDocument();
    expect(requests).toEqual(['0', '1', '0']);
  });
});

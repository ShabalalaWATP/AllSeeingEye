import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import type { TeamBoardPost } from '@/lib/api/teamBoard';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import {
  boardBase,
  boardPage,
  boardPost,
  managerBoardCapabilities,
  memberBoardCapabilities,
  renderTeamBoard,
} from '@/test/fixtures.teamBoard';
import { manager } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

const mine = boardPost({ text: 'My handover' });
const theirs = boardPost({
  id: '66666666-6666-4666-8666-666666666662',
  author_id: adminUser.id,
  author_name: adminUser.display_name,
  text: 'Administrator guidance',
  is_pinned: true,
});

function article(name: string) {
  return screen.findByRole('article', { name: `Post by ${name}` });
}

describe('TeamBoard actions', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  it('creates a post and a reply, and cancels a reply draft', async () => {
    const created: unknown[] = [];
    let posts: TeamBoardPost[] = [mine];
    server.use(
      http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage(posts))),
      http.post(`${boardBase}/posts`, async ({ request }) => {
        const body = (await request.json()) as { text: string; parent_id?: string };
        created.push(body);
        const next = boardPost({
          id: `66666666-6666-4666-8666-66666666667${created.length}`,
          text: body.text,
        });
        if (body.parent_id === undefined) posts = [...posts, next];
        return HttpResponse.json(next, { status: 201 });
      }),
    );
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    await screen.findByText('My handover');
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument();
    const post = screen.getByRole('button', { name: 'Post update' });
    expect(post).toBeDisabled();
    await user.type(screen.getByLabelText(/New board post/), '  Shift summary  ');
    await user.click(post);
    expect(await screen.findByText('Shift summary')).toBeInTheDocument();

    const card = within(screen.getByText('My handover').closest('article')!);
    await user.click(card.getByRole('button', { name: 'Reply' }));
    const field = screen.getByLabelText(`Reply to ${plainUser.display_name}`);
    expect(field).toHaveAttribute('maxLength', '2000');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByLabelText(/New board post/)).toHaveAttribute('maxLength', '4000');

    await user.click(card.getByRole('button', { name: 'Reply' }));
    await user.type(screen.getByLabelText(`Reply to ${plainUser.display_name}`), 'Agreed');
    await user.click(screen.getByRole('button', { name: 'Post reply' }));
    await waitFor(() => {
      expect(created).toEqual([{ text: 'Shift summary' }, { text: 'Agreed', parent_id: mine.id }]);
    });
  });

  it('lets an author remove their own post without a reason', async () => {
    let query = '';
    let removed = false;
    server.use(
      http.get(`${boardBase}/posts`, () =>
        HttpResponse.json(
          boardPage([
            removed
              ? {
                  ...mine,
                  text: '[Removed]',
                  deleted_at: '2026-09-15T09:00:00Z',
                  removal: 'author',
                }
              : mine,
          ]),
        ),
      ),
      http.delete(`${boardBase}/posts/:postId`, ({ request }) => {
        query = new URL(request.url).search;
        removed = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    const card = within(await article(plainUser.display_name));
    await user.click(card.getByRole('button', { name: 'Remove' }));
    expect(card.getByText(/Remove your post\?/)).toBeInTheDocument();
    expect(card.queryByLabelText(/Moderation reason/)).not.toBeInTheDocument();
    await user.click(card.getByRole('button', { name: 'Cancel' }));
    await user.click(card.getByRole('button', { name: 'Remove' }));
    await user.click(card.getByRole('button', { name: 'Confirm remove post' }));
    expect(await screen.findByText('Removed by author')).toBeInTheDocument();
    expect(query).toBe('?expected_revision=1');
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
  });

  it('pins own posts without a reason and unpins others with one', async () => {
    const pins: unknown[] = [];
    useAuthStore.getState().setSession(tokenFor(manager));
    const own = boardPost({ author_id: manager.id, author_name: manager.display_name });
    const reply = boardPost({
      id: '66666666-6666-4666-8666-666666666663',
      author_id: plainUser.id,
      parent_id: own.id,
      text: 'A reply cannot be pinned',
    });
    server.use(
      http.get(`${boardBase}/posts`, () =>
        HttpResponse.json(boardPage([theirs, own], { replies: [reply] })),
      ),
      http.post(`${boardBase}/posts/:postId/pin`, async ({ request }) => {
        pins.push(await request.json());
        return HttpResponse.json(own);
      }),
    );
    const user = renderTeamBoard(manager.id, managerBoardCapabilities);
    const pinned = within(await article(adminUser.display_name));
    expect(pinned.getByText('Pinned')).toBeInTheDocument();
    await user.click(pinned.getByRole('button', { name: 'Unpin' }));
    const confirm = pinned.getByRole('button', { name: 'Confirm unpin post' });
    await user.type(pinned.getByLabelText(/Moderation reason/), ' ab ');
    expect(confirm).toBeDisabled();
    await user.type(pinned.getByLabelText(/Moderation reason/), 'c');
    await user.click(confirm);
    await waitFor(() => {
      expect(pinned.queryByRole('group')).not.toBeInTheDocument();
    });

    const replyCard = screen.getByText('A reply cannot be pinned').closest('article')!;
    expect(within(replyCard).queryByRole('button', { name: 'Pin' })).not.toBeInTheDocument();
    expect(within(replyCard).queryByRole('button', { name: 'Reply' })).not.toBeInTheDocument();
    const ownCard = within(screen.getByText('Handover note').closest('article')!);
    await user.click(ownCard.getByRole('button', { name: 'Pin' }));
    await user.click(ownCard.getByRole('button', { name: 'Confirm pin post' }));
    await waitFor(() => {
      expect(pins).toEqual([
        { pinned: false, expected_revision: 1, reason: 'ab c' },
        { pinned: true, expected_revision: 1 },
      ]);
    });
  });

  it('keeps the confirmation open when moderation conflicts or fails', async () => {
    useAuthStore.getState().setSession(tokenFor(manager));
    let status = 409;
    server.use(
      http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([theirs]))),
      http.post(`${boardBase}/posts/:postId/pin`, () =>
        status === 409
          ? apiError(409, 'conflict', 'This post changed.')
          : apiError(422, 'invalid_request', 'Pin limit reached.'),
      ),
    );
    const user = renderTeamBoard(manager.id, managerBoardCapabilities);
    const card = within(await article(adminUser.display_name));
    await user.click(card.getByRole('button', { name: 'Unpin' }));
    await user.type(card.getByLabelText(/Moderation reason/), 'Outdated guidance');
    await user.click(card.getByRole('button', { name: 'Confirm unpin post' }));
    expect(await screen.findByText(/This post changed\. Your draft is kept/)).toBeInTheDocument();
    expect(card.getByRole('group', { name: 'Unpin post' })).toBeInTheDocument();

    status = 422;
    await user.click(card.getByRole('button', { name: 'Confirm unpin post' }));
    expect(await screen.findByText('Pin limit reached.')).toBeInTheDocument();
    expect(card.getByRole('group', { name: 'Unpin post' })).toBeInTheDocument();
  });

  it('reports a failed save and keeps the draft', async () => {
    server.use(
      http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([]))),
      http.post(`${boardBase}/posts`, () =>
        apiError(403, 'forbidden', 'Only active members can post.'),
      ),
    );
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    expect(await screen.findByText('No board updates yet')).toBeInTheDocument();
    await user.type(screen.getByLabelText(/New board post/), 'Draft');
    await user.click(screen.getByRole('button', { name: 'Post update' }));
    expect(await screen.findByText('Only active members can post.')).toBeInTheDocument();
    expect(screen.getByLabelText(/New board post/)).toHaveValue('Draft');
    expect(screen.queryByText('No board updates yet')).not.toBeInTheDocument();
  });

  it('shows read-only explanations for archived teams and non-members', async () => {
    server.use(http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([mine]))));
    renderTeamBoard(adminUser.id, { ...managerBoardCapabilities, teamIsActive: false });
    expect(await screen.findByText(/This team is archived/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Remove|Pin|Reply|Edit/ })).not.toBeInTheDocument();
  });

  it('explains that only members can post', async () => {
    server.use(http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([]))));
    renderTeamBoard(plainUser.id, { ...memberBoardCapabilities, isMember: false });
    expect(await screen.findByText('Only team members can post.')).toBeInTheDocument();
  });
});

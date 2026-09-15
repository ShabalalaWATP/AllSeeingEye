import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import type { TeamBoardPage, TeamBoardPost } from '@/lib/api/teamBoard';
import { useAuthStore } from '@/stores/auth';
import { adminUser, plainUser, tokenFor } from '@/test/fixtures';
import { manager, team } from '@/test/fixtures.teams';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

import { TeamBoard } from './TeamBoard';
import type { TeamCapabilities } from './teamCapabilities';

const base = `/api/teams/${team.id}/board`;

function boardPost(overrides: Partial<TeamBoardPost>): TeamBoardPost {
  return {
    id: '66666666-6666-4666-8666-666666666661',
    team_id: team.id,
    author_id: plainUser.id,
    author_name: plainUser.display_name,
    text: 'Handover note',
    created_at: '2026-09-15T08:00:00Z',
    updated_at: '2026-09-15T08:00:00Z',
    edited_at: null,
    parent_id: null,
    is_pinned: false,
    deleted_at: null,
    removal: null,
    revision: 1,
    ...overrides,
  };
}

const mine = boardPost({ text: 'My handover', edited_at: '2026-09-15T08:30:00Z' });
const adminPost = boardPost({
  id: '66666666-6666-4666-8666-666666666662',
  author_id: adminUser.id,
  author_name: adminUser.display_name,
  text: 'Administrator guidance',
  created_at: '2026-09-15T09:00:00Z',
});
const reply = boardPost({
  id: '66666666-6666-4666-8666-666666666663',
  author_id: manager.id,
  author_name: manager.display_name,
  parent_id: mine.id,
  text: 'Newest reply',
  created_at: '2026-09-15T10:00:00Z',
});
const tombstone = boardPost({
  id: '66666666-6666-4666-8666-666666666664',
  text: '[Removed by a moderator]',
  deleted_at: '2026-09-15T07:00:00Z',
  removal: 'moderator',
  created_at: '2026-09-15T07:00:00Z',
});

function page(items: TeamBoardPost[], replies: TeamBoardPost[] = [], unread = 0): TeamBoardPage {
  return {
    items,
    replies,
    total: items.length,
    offset: 0,
    limit: 20,
    next_offset: null,
    unread_count: unread,
  };
}

const memberCapabilities: TeamCapabilities = {
  isAdmin: false,
  isMember: true,
  isManager: false,
  teamIsActive: true,
  canCreateTeam: true,
  canManageMembers: false,
  canManageTeam: false,
  canLeave: true,
};
const managerCapabilities: TeamCapabilities = {
  ...memberCapabilities,
  isManager: true,
  canManageMembers: true,
  canManageTeam: true,
};

function renderBoard(userId: string, capabilities: TeamCapabilities) {
  const user = userEvent.setup();
  render(
    <TeamBoard teamId={team.id} teamName={team.name} userId={userId} capabilities={capabilities} />,
  );
  return user;
}

describe('TeamBoard', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  it('shows threads, tombstones and the unread badge, then records the newest post as read', async () => {
    const reads: unknown[] = [];
    server.use(
      http.get(`${base}/posts`, () =>
        HttpResponse.json(page([adminPost, mine, tombstone], [reply], 3)),
      ),
      http.post(`${base}/read`, async ({ request }) => {
        reads.push(await request.json());
        return HttpResponse.json({ unread_count: 0 });
      }),
    );
    renderBoard(plainUser.id, memberCapabilities);

    expect(await screen.findByText('Administrator guidance')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('3 new since your last visit');
    expect(screen.getByText('Removed by a moderator')).toBeInTheDocument();
    expect(screen.getByText(/Edited/)).toBeInTheDocument();
    expect(screen.getByText('Newest reply')).toBeInTheDocument();
    await waitFor(() => {
      expect(reads).toEqual([{ last_seen_post_id: reply.id }]);
    });

    // Members edit only their own posts and never see moderation controls.
    const others = within(
      screen.getByRole('article', { name: `Post by ${adminUser.display_name}` }),
    );
    expect(others.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    expect(others.queryByRole('button', { name: 'Remove' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Pin' })).not.toBeInTheDocument();
  });

  it('requires a moderation reason before a manager removes someone else’s post', async () => {
    useAuthStore.getState().setSession(tokenFor(manager));
    const removals: unknown[] = [];
    let removed = false;
    server.use(
      http.get(`${base}/posts`, () =>
        HttpResponse.json(
          page([
            removed
              ? {
                  ...adminPost,
                  text: '[Removed by a moderator]',
                  deleted_at: '2026-09-15T11:00:00Z',
                  removal: 'moderator',
                  revision: 2,
                }
              : adminPost,
          ]),
        ),
      ),
      http.post(`${base}/posts/:postId/remove`, async ({ request }) => {
        removals.push(await request.json());
        removed = true;
        return HttpResponse.json({ ...adminPost, revision: 2 });
      }),
    );
    const user = renderBoard(manager.id, managerCapabilities);

    const card = within(
      await screen.findByRole('article', { name: `Post by ${adminUser.display_name}` }),
    );
    expect(card.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    await user.click(card.getByRole('button', { name: 'Remove' }));
    const confirm = card.getByRole('button', { name: 'Confirm remove post' });
    expect(confirm).toBeDisabled();
    expect(card.getByText(/not shown to the team/)).toBeInTheDocument();
    await user.type(card.getByLabelText(/Moderation reason/), 'Contains an access code');
    await user.click(confirm);

    expect(await screen.findByText('Removed by a moderator')).toBeInTheDocument();
    expect(removals).toEqual([{ expected_revision: 1, reason: 'Contains an access code' }]);
  });

  it('keeps the draft through a revision conflict and saves against the reloaded revision', async () => {
    const edits: unknown[] = [];
    let current = mine;
    server.use(
      http.get(`${base}/posts`, () => HttpResponse.json(page([current]))),
      http.patch(`${base}/posts/:postId`, async ({ request }) => {
        const body = (await request.json()) as { text: string; expected_revision: number };
        edits.push(body);
        if (body.expected_revision !== current.revision) {
          return apiError(409, 'conflict', 'This post changed. Reload it before saving again.');
        }
        current = { ...current, text: body.text, revision: current.revision + 1 };
        return HttpResponse.json(current);
      }),
    );
    const user = renderBoard(plainUser.id, memberCapabilities);

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    // Another tab saves first.
    current = { ...mine, text: 'Changed elsewhere', revision: 2 };
    const field = screen.getByLabelText(/Edit post/);
    await user.clear(field);
    await user.type(field, 'My careful rewrite');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(await screen.findByText(/The board changed/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Edit post/)).toHaveValue('My careful rewrite');
    await user.click(screen.getByRole('button', { name: 'Reload board' }));
    expect(await screen.findByText('Changed elsewhere')).toBeInTheDocument();
    expect(screen.getByLabelText(/Edit post/)).toHaveValue('My careful rewrite');

    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByText('My careful rewrite')).toBeInTheDocument();
    expect(edits).toEqual([
      { text: 'My careful rewrite', expected_revision: 1 },
      { text: 'My careful rewrite', expected_revision: 2 },
    ]);
  });

  it('offers a retry when the board is no longer available', async () => {
    let fail = true;
    server.use(
      http.get(`${base}/posts`, () =>
        fail ? apiError(404, 'not_found', 'Not found.') : HttpResponse.json(page([])),
      ),
    );
    const user = renderBoard(plainUser.id, memberCapabilities);
    expect(await screen.findByText('Team access changed')).toBeInTheDocument();
    expect(screen.queryByLabelText('New board post')).not.toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByText('No board updates yet')).toBeInTheDocument();
  });
});

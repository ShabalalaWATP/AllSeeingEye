import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import {
  boardBase,
  boardPage,
  boardPost,
  memberBoardCapabilities,
  renderTeamBoard,
} from '@/test/fixtures.teamBoard';
import { apiError } from '@/test/handlers';
import { server } from '@/test/server';

const first = boardPost({ text: 'First page post', created_at: '2026-09-15T09:00:00Z' });
const older = boardPost({
  id: '66666666-6666-4666-8666-666666666665',
  text: 'Older post',
  created_at: '2026-09-14T09:00:00Z',
});
const olderReply = boardPost({
  id: '66666666-6666-4666-8666-666666666666',
  parent_id: older.id,
  text: 'Older reply',
  created_at: '2026-09-14T10:00:00Z',
});

describe('TeamBoard paging and refresh', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  it('caps the unread badge and tolerates a failed read receipt', async () => {
    let reads = 0;
    server.use(
      http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([first], { unread: 250 }))),
      http.post(`${boardBase}/read`, () => {
        reads += 1;
        return apiError(500, 'server_error', 'Receipt failed.');
      }),
    );
    renderTeamBoard(plainUser.id, memberBoardCapabilities);
    expect(await screen.findByText('100+ new since your last visit')).toBeInTheDocument();
    await waitFor(() => {
      expect(reads).toBe(1);
    });
    expect(screen.queryByText('Receipt failed.')).not.toBeInTheDocument();
  });

  it('does not send a read receipt when nothing is unread', async () => {
    let reads = 0;
    server.use(
      http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([], { unread: 4 }))),
      http.post(`${boardBase}/read`, () => {
        reads += 1;
        return HttpResponse.json({ unread_count: 0 });
      }),
    );
    renderTeamBoard(plainUser.id, memberBoardCapabilities);
    expect(await screen.findByText('No board updates yet')).toBeInTheDocument();
    expect(reads).toBe(0);
  });

  it('loads older posts and merges duplicates from the next page', async () => {
    const offsets: string[] = [];
    server.use(
      http.get(`${boardBase}/posts`, ({ request }) => {
        const offset = new URL(request.url).searchParams.get('offset') ?? '';
        offsets.push(offset);
        if (offset === '0') return HttpResponse.json(boardPage([first], { nextOffset: 1 }));
        return HttpResponse.json({
          ...boardPage([{ ...first, text: 'First page post (refreshed)' }, older], {
            replies: [olderReply],
          }),
          offset: 1,
        });
      }),
    );
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    await user.click(await screen.findByRole('button', { name: 'Load older posts' }));
    expect(await screen.findByText('Older reply')).toBeInTheDocument();
    expect(screen.getByText('Older post')).toBeInTheDocument();
    expect(screen.getByText('First page post (refreshed)')).toBeInTheDocument();
    expect(screen.queryByText('First page post')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Load older posts' })).not.toBeInTheDocument();
    expect(offsets).toEqual(['0', '1']);
  });

  it('keeps loaded posts when an older page fails', async () => {
    server.use(
      http.get(`${boardBase}/posts`, ({ request }) =>
        new URL(request.url).searchParams.get('offset') === '0'
          ? HttpResponse.json(boardPage([first], { nextOffset: 20 }))
          : apiError(503, 'unavailable', 'Board temporarily unavailable.'),
      ),
    );
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    await user.click(await screen.findByRole('button', { name: 'Load older posts' }));
    expect(await screen.findByText('Board temporarily unavailable.')).toBeInTheDocument();
    expect(screen.getByText('First page post')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Load older posts' })).toBeEnabled();
  });

  it('abandons an edit when the post was removed before the reload', async () => {
    let removed = false;
    server.use(
      http.get(`${boardBase}/posts`, () =>
        HttpResponse.json(
          boardPage([
            removed
              ? {
                  ...first,
                  text: '[Removed]',
                  deleted_at: '2026-09-15T10:00:00Z',
                  edited_at: '2026-09-15T09:30:00Z',
                  removal: 'moderator',
                  revision: 2,
                }
              : first,
          ]),
        ),
      ),
      http.patch(`${boardBase}/posts/:postId`, () => {
        removed = true;
        return apiError(409, 'conflict', 'This post was removed.');
      }),
    );
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    await user.type(screen.getByLabelText('Edit post'), ' with more');
    await user.click(screen.getByRole('button', { name: 'Save changes' }));
    await user.click(await screen.findByRole('button', { name: 'Reload board' }));

    expect(await screen.findByText('Removed by a moderator')).toBeInTheDocument();
    expect(screen.queryByText(/Edited/)).not.toBeInTheDocument();
    expect(screen.getByLabelText('New board post')).toHaveValue('First page post with more');
    expect(screen.getByRole('button', { name: 'Post update' })).toBeEnabled();
  });

  it('cancels an edit and clears its draft', async () => {
    server.use(http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([first]))));
    const user = renderTeamBoard(plainUser.id, memberBoardCapabilities);
    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    expect(screen.getByLabelText('Edit post')).toHaveValue('First page post');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByLabelText('New board post')).toHaveValue('');
  });
});

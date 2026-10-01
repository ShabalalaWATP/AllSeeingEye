import { render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';

import type { BoardSubjectInput } from '@/lib/api/teamBoard';
import { plainUser } from '@/test/fixtures';
import {
  boardBase,
  boardPage,
  boardPost,
  memberBoardCapabilities,
  serveBoard,
} from '@/test/fixtures.teamBoard';
import { team } from '@/test/fixtures.teams';
import { server } from '@/test/server';

import { TeamBoard } from './TeamBoard';

const subject: BoardSubjectInput = {
  kind: 'report_version',
  id: '22222222-2222-4222-8222-222222222222',
  version: 2,
};

function captureCreates() {
  const bodies: unknown[] = [];
  server.use(
    http.post(`${boardBase}/posts`, async ({ request }) => {
      bodies.push(await request.json());
      return HttpResponse.json(boardPost({ id: '66666666-6666-4666-8666-666666666669' }), {
        status: 201,
      });
    }),
  );
  return bodies;
}

function renderBoard(props: { focusPostId?: string; initialSubject?: BoardSubjectInput }) {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <TeamBoard
        teamId={team.id}
        teamName={team.name}
        userId={plainUser.id}
        capabilities={memberBoardCapabilities}
        {...props}
      />
    </MemoryRouter>,
  );
  return user;
}

describe('TeamBoard subjects', () => {
  it('starts a thread about a linked report version and clears the link after posting', async () => {
    serveBoard(() => boardPage([boardPost({})]));
    const bodies = captureCreates();
    const user = renderBoard({ initialSubject: subject });
    const chip = await screen.findByRole('group', { name: 'Linked work' });
    expect(chip).toHaveTextContent('Report version 2');
    await user.type(screen.getByLabelText('New board post'), 'Does judgement two still hold?');
    await user.click(screen.getByRole('button', { name: 'Post update' }));
    await waitFor(() =>
      expect(bodies).toEqual([{ text: 'Does judgement two still hold?', subject }]),
    );
    await waitFor(() =>
      expect(screen.queryByRole('group', { name: 'Linked work' })).not.toBeInTheDocument(),
    );
  });

  it('lets the author drop the link and never sends it with a reply', async () => {
    serveBoard(() => boardPage([boardPost({})]));
    const bodies = captureCreates();
    const user = renderBoard({ initialSubject: subject });
    const chip = await screen.findByRole('group', { name: 'Linked work' });
    await user.click(within(chip).getByRole('button', { name: 'Remove link' }));
    expect(screen.queryByRole('group', { name: 'Linked work' })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText('New board post'), 'Plain handover');
    await user.click(screen.getByRole('button', { name: 'Post update' }));
    await waitFor(() => expect(bodies).toEqual([{ text: 'Plain handover' }]));
  });

  it('keeps a pending link out of replies', async () => {
    serveBoard(() => boardPage([boardPost({})]));
    const bodies = captureCreates();
    const user = renderBoard({ initialSubject: subject });
    await screen.findByRole('group', { name: 'Linked work' });
    await user.click(await screen.findByRole('button', { name: 'Reply' }));
    expect(screen.queryByRole('group', { name: 'Linked work' })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(`Reply to ${plainUser.display_name}`), 'On it');
    await user.click(screen.getByRole('button', { name: 'Post reply' }));
    await waitFor(() => expect(bodies).toEqual([{ text: 'On it', parent_id: boardPost({}).id }]));
  });

  it('highlights the linked thread once it has loaded', async () => {
    const target = boardPost({ id: '66666666-6666-4666-8666-666666666662', text: 'Linked' });
    serveBoard(() => boardPage([boardPost({}), target]));
    renderBoard({ focusPostId: target.id });
    const article = await screen.findByText('Linked');
    await waitFor(() => expect(article.closest('article')).toHaveAttribute('aria-current', 'true'));
    const other = screen.getByText('Handover note').closest('article');
    expect(other).not.toHaveAttribute('aria-current');
  });
});

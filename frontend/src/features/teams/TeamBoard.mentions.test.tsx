import { render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';

import type { TeamMember } from '@/lib/api/teams';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import {
  boardBase,
  boardPage,
  boardPost,
  memberBoardCapabilities,
} from '@/test/fixtures.teamBoard';
import { roster, team } from '@/test/fixtures.teams';
import { server } from '@/test/server';

import { TeamBoard } from './TeamBoard';

const inactive: TeamMember = {
  ...roster.members[0]!,
  user_id: '55555555-5555-4555-8555-555555555555',
  display_name: 'Former analyst',
  username: 'former_one',
  is_active: false,
};
const self: TeamMember = { ...roster.members[1]!, username: 'plain_user' };
const members = [roster.members[0]!, self, inactive];

function renderBoard() {
  const user = userEvent.setup();
  render(
    <TeamBoard
      teamId={team.id}
      teamName={team.name}
      userId={plainUser.id}
      capabilities={memberBoardCapabilities}
      members={members}
    />,
  );
  return user;
}

describe('TeamBoard mentions', () => {
  beforeEach(() => {
    useAuthStore.getState().setSession(tokenFor(plainUser));
  });

  it('offers only active teammates with handles, inserts the handle and says who was notified', async () => {
    let sent: unknown = null;
    server.use(
      http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([]))),
      http.post(`${boardBase}/posts`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(
          {
            ...boardPost({ text: '@mina_manager please review' }),
            notified: [{ user_id: roster.members[0]!.user_id, display_name: 'Mina Manager' }],
          },
          { status: 201 },
        );
      }),
    );
    const user = renderBoard();
    await screen.findByText('No board updates yet');
    const picker = screen.getByRole('combobox', { name: 'Mention a teammate' });
    const options = Array.from((picker as HTMLSelectElement).options).map((item) => item.text);
    expect(options).toEqual(['Choose a teammate', 'Mina Manager (@mina_manager)']);
    await user.selectOptions(picker, 'mina_manager');
    const draft = screen.getByLabelText(/New board post/);
    expect(draft).toHaveValue('@mina_manager ');
    expect(screen.getByText('1 of up to 10 mentions used.')).toBeVisible();
    await user.type(draft, 'please review');
    await user.click(screen.getByRole('button', { name: 'Post update' }));
    await waitFor(() => expect(sent).toEqual({ text: '@mina_manager please review' }));
    expect(await screen.findByText('Notified Mina Manager in their notifications.')).toBeVisible();
  });

  it('shows the ten-teammate limit before posting and blocks the save', async () => {
    server.use(http.get(`${boardBase}/posts`, () => HttpResponse.json(boardPage([]))));
    const user = renderBoard();
    await screen.findByText('No board updates yet');
    const handles = Array.from({ length: 11 }, (_, n) => `@user_${String(n)}`).join(' ');
    await user.click(screen.getByLabelText(/New board post/));
    await user.paste(handles);
    expect(screen.getByText(/mentions 11 different people/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Post update' })).toBeDisabled();
  });
});

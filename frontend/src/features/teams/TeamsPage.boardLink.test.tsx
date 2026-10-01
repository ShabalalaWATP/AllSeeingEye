import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { teamThreadPath, startTeamThreadPath } from '@/lib/teamBoardLinks';
import { plainUser } from '@/test/fixtures';
import { boardPage, boardPost, serveBoard } from '@/test/fixtures.teamBoard';
import { roster, setupTeams, team } from '@/test/fixtures.teams';

describe('TeamsPage board links', () => {
  it('opens the linked team on its board with the thread highlighted', async () => {
    const thread = boardPost({ text: 'Port review thread' });
    serveBoard(() => boardPage([thread]));
    setupTeams(plainUser, roster, [], teamThreadPath(team.id, thread.id));
    const article = (await screen.findByText('Port review thread')).closest('article');
    expect(screen.getByRole('tab', { name: /Board/ })).toHaveAttribute('aria-selected', 'true');
    await waitFor(() => expect(article).toHaveAttribute('aria-current', 'true'));
  });

  it('prefills a new thread about a report version', async () => {
    serveBoard(() => boardPage([]));
    setupTeams(
      plainUser,
      roster,
      [],
      startTeamThreadPath(team.id, {
        kind: 'report_version',
        id: '22222222-2222-4222-8222-222222222222',
        version: 4,
      }),
    );
    expect(await screen.findByRole('group', { name: 'Linked work' })).toHaveTextContent(
      'Report version 4',
    );
  });

  it('keeps the roster landing view without a board link', async () => {
    setupTeams();
    expect(await screen.findByRole('table', { name: 'Team members' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Members/ })).toHaveAttribute('aria-selected', 'true');
  });
});

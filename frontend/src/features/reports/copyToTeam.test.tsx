import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';

import type { TeamCopyPreview, TeamCopyProvenance } from '@/lib/api/reportTeamCopies';
import { plainUser, report, reportSummary } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const teamId = '44444444-4444-4444-8444-444444444444';
const copyId = '77777777-7777-4777-8777-777777777777';
const team = {
  id: teamId,
  name: 'Northern desk',
  is_active: true,
  created_by: plainUser.id,
  created_at: '2026-09-06T10:00:00Z',
  updated_at: '2026-09-06T10:00:00Z',
  description: null,
};
const preview: TeamCopyPreview = {
  team_id: teamId,
  team_name: 'Northern desk',
  source_version_number: 1,
  private_inputs: [{ label: 'E2', title: 'Field notes', source_id: 'research_import' }],
  omissions: ['research_brief', 'scope_references'],
  omitted_scope_keys: ['plan'],
  not_copied: {
    claims: 3,
    original_files: 1,
    original_passages: 0,
    reviewed_snapshots: 0,
    map_views: 0,
  },
  content_sha256: 'a'.repeat(64),
  existing_report_id: null,
};

function serveTeams(isActive = true) {
  server.use(
    http.get('/api/teams', () => HttpResponse.json({ items: [{ ...team, is_active: isActive }] })),
    http.get('/api/teams/:id', () =>
      HttpResponse.json({
        team: { ...team, is_active: isActive },
        members: [
          {
            user_id: plainUser.id,
            display_name: plainUser.display_name,
            username: null,
            account_role: 'user',
            is_active: true,
            role: 'member',
            joined_at: team.created_at,
          },
        ],
      }),
    ),
  );
}

function serveCopy(shown: TeamCopyPreview, status = 201) {
  const bodies: unknown[] = [];
  server.use(
    http.get('/api/reports/:id/versions/:number/team-copy-preview', ({ request }) => {
      expect(new URL(request.url).searchParams.get('team_id')).toBe(teamId);
      return HttpResponse.json(shown);
    }),
    http.post('/api/reports/:id/versions/:number/team-copies', async ({ request }) => {
      bodies.push(await request.json());
      if (status >= 400)
        return apiError(status, 'invalid_request', 'Confirm the current disclosure list.');
      return HttpResponse.json(
        {
          report_id: copyId,
          version_number: 1,
          team_id: teamId,
          copied_at: '2026-10-01T10:00:00Z',
          created: status === 201,
        },
        { status },
      );
    }),
  );
  return bodies;
}

async function openPanel() {
  const view = renderApp(`/reports/${reportSummary.id}`, 'user');
  await view.user.click(await screen.findByRole('button', { name: 'Copy to team' }));
  const panel = screen.getByRole('region', { name: 'Copy version 1 to a team' });
  await view.user.selectOptions(within(panel).getByLabelText('Team'), teamId);
  await view.user.click(within(panel).getByRole('button', { name: 'Review what is shared' }));
  return { ...view, panel };
}

it('reviews the disclosure, requires private-input confirmation and copies once', async () => {
  serveTeams();
  const bodies = serveCopy(preview);
  const { user, panel } = await openPanel();
  expect(
    await within(panel).findByText('The link to your Research Brief is not copied.'),
  ).toBeVisible();
  expect(
    within(panel).getByText('3 claim ledger entries stay with your personal report.'),
  ).toBeVisible();
  expect(
    within(panel).getByText('1 retained original file stays with your personal report.'),
  ).toBeVisible();
  const copy = within(panel).getByRole('button', { name: 'Copy to Northern desk' });
  expect(copy).toBeDisabled();
  await user.click(
    within(panel).getByRole('checkbox', {
      name: 'Share these private inputs with current members of Northern desk',
    }),
  );
  await user.click(copy);
  expect(await within(panel).findByRole('link', { name: 'Open the team copy' })).toHaveAttribute(
    'href',
    `/reports/${copyId}`,
  );
  expect(within(panel).getByText('Copied to the team')).toBeVisible();
  expect(bodies).toEqual([{ team_id: teamId, disclosed_evidence_labels: ['E2'] }]);
});

it('links an existing copy instead of offering another', async () => {
  serveTeams();
  serveCopy({ ...preview, existing_report_id: copyId });
  const { panel } = await openPanel();
  expect(await within(panel).findByText('Already copied to Northern desk')).toBeVisible();
  expect(within(panel).getByRole('link', { name: 'Open the team copy' })).toHaveAttribute(
    'href',
    `/reports/${copyId}`,
  );
  expect(within(panel).queryByRole('button', { name: /Copy to Northern/ })).toBeNull();
});

it('announces a refused copy and keeps the panel open', async () => {
  serveTeams();
  serveCopy({ ...preview, private_inputs: [] }, 422);
  const { user, panel } = await openPanel();
  await user.click(await within(panel).findByRole('button', { name: 'Copy to Northern desk' }));
  expect(await within(panel).findByRole('alert')).toHaveTextContent(
    'Confirm the current disclosure list.',
  );
  expect(within(panel).getByRole('button', { name: 'Copy to Northern desk' })).toBeEnabled();
});

it.each([
  ['a team report', { team_id: teamId }, true],
  ['someone else’s report', { created_by: '99999999-9999-4999-8999-000000000000' }, true],
  ['a report without an active team membership', {}, false],
])('offers no copy action for %s', async (_case, summary, activeTeam) => {
  serveTeams(activeTeam);
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({ ...report, report: { ...reportSummary, ...summary } }),
    ),
    http.get('/api/reports/:id/team-copy-provenance', () =>
      apiError(404, 'not_found', 'Not found.'),
    ),
  );
  renderApp(`/reports/${reportSummary.id}`, 'user');
  await screen.findByRole('button', { name: 'Sources & methods' });
  expect(screen.queryByRole('button', { name: 'Copy to team' })).toBeNull();
});

it('shows the provenance of a team copy without linking a hidden original', async () => {
  serveTeams();
  const provenance: TeamCopyProvenance = {
    report_id: reportSummary.id,
    team_id: teamId,
    copied_by: plainUser.id,
    copied_by_name: 'Uma User',
    copied_at: '2026-10-01T10:00:00Z',
    source_version_number: 3,
    source_report_id: null,
    content_sha256: 'a'.repeat(64),
    disclosed_private_inputs: 1,
    omissions: [],
  };
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({ ...report, report: { ...reportSummary, team_id: teamId } }),
    ),
    http.get('/api/reports/:id/team-copy-provenance', () => HttpResponse.json(provenance)),
  );
  renderApp(`/reports/${reportSummary.id}`, 'user');
  expect(
    await screen.findByText(/Copied from a personal report \(version 3\) by Uma User/),
  ).toHaveTextContent('It includes 1 private input its owner chose to share.');
  expect(screen.queryByRole('link', { name: 'Open your personal original' })).toBeNull();
});

it('closes with Escape and returns focus to the action', async () => {
  serveTeams();
  const { user } = renderApp(`/reports/${reportSummary.id}`, 'user');
  const toggle = await screen.findByRole('button', { name: 'Copy to team' });
  await user.click(toggle);
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('region', { name: 'Copy version 1 to a team' })).toBeNull();
  expect(toggle).toHaveFocus();
});

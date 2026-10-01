import { act, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { readReportWatchDraft } from '@/lib/alertRuleDraft';
import { indicator, report, reportSummary } from '@/test/fixtures';
import { roster, team } from '@/test/fixtures.teams';
import { applySession, renderApp } from '@/test/render';
import { server } from '@/test/server';

const LONG = 'Large convoys of armoured vehicles moving south along the northern road at night';

function reportWith(changes: { team_id?: string | null; indicators?: string[] }) {
  const judgement = report.version.body.key_judgements[0]!;
  server.use(
    http.get('/api/reports/:id', () =>
      HttpResponse.json({
        report: { ...reportSummary, team_id: changes.team_id ?? null },
        version: {
          ...report.version,
          body: {
            ...report.version.body,
            key_judgements: [
              { ...judgement, indicators: changes.indicators ?? judgement.indicators },
            ],
          },
        },
      }),
    ),
  );
}

function trackRuleWrites() {
  const writes: unknown[] = [];
  server.use(
    http.post('/api/warning/indicators', async ({ request }) => {
      writes.push(await request.json());
      return HttpResponse.json({ ...indicator, name: 'Watch' }, { status: 201 });
    }),
  );
  return writes;
}

async function draftFromReport() {
  const view = renderApp(`/reports/${reportSummary.id}`, 'user');
  const panel = await screen.findByRole('region', { name: 'Watch for these indicators' });
  await view.user.click(
    within(panel).getByRole('button', { name: 'Draft an alert rule from judgement 1' }),
  );
  const form = within(await screen.findByRole('form', { name: 'New alert rule' }));
  return { ...view, form };
}

describe('turning Watch for indicators into an alert rule draft', () => {
  it('prefills an editable draft from the exact report version and sends nothing yet', async () => {
    const writes = trackRuleWrites();
    const { router, form } = await draftFromReport();
    expect(router.state.location.pathname).toBe('/warning');
    expect(router.state.location.search).toBe('');
    const notice = form.getByRole('region', { name: 'Draft from a report' });
    expect(within(notice).getByRole('link', { name: /version 1/ })).toHaveAttribute(
      'href',
      `/reports/${reportSummary.id}?version=1`,
    );
    expect(
      within(notice).getByRole('list', { name: 'Original indicator wording' }),
    ).toHaveTextContent('Reinforcements on the northern road');
    expect(notice).toHaveTextContent('They do not monitor the meaning of an indicator');
    expect(form.getByLabelText('Alert rule name')).toHaveValue(
      'Watch: Intelligence summary: Ukraine',
    );
    expect(form.getByLabelText('Keywords')).toHaveValue('Reinforcements on the northern road');
    expect(await form.findByRole('button', { name: 'Remove Ukraine' })).toBeVisible();
    expect(form.getByLabelText('Workspace')).toBeDisabled();
    expect(writes).toEqual([]);
  });

  it('saves once on Add, then offers a route back to the report version', async () => {
    const writes = trackRuleWrites();
    const { user, form } = await draftFromReport();
    await user.click(form.getByRole('button', { name: 'Add alert rule' }));
    expect(
      await screen.findByRole('link', {
        name: 'Back to “Intelligence summary: Ukraine”, version 1',
      }),
    ).toHaveAttribute('href', `/reports/${reportSummary.id}?version=1`);
    expect(writes).toHaveLength(1);
    expect(writes[0]).toMatchObject({
      countries: ['UA'],
      keywords: ['Reinforcements on the northern road'],
    });
    expect(writes[0]).not.toHaveProperty('team_id');
    expect(readReportWatchDraft()).toBeNull();
  });

  it('makes an overlong indicator phrase a visible edit, not a silent cut', async () => {
    reportWith({ indicators: [LONG] });
    const writes = trackRuleWrites();
    const { user, form } = await draftFromReport();
    expect(form.getByLabelText('Keywords')).toHaveValue(LONG);
    await user.click(form.getByRole('button', { name: 'Add alert rule' }));
    expect(
      await form.findByRole('alert', { name: 'Check these fields and try again:' }),
    ).toHaveTextContent('Keywords: Shorten each keyword to 60 characters or fewer (1 is longer).');
    expect(writes).toEqual([]);
    await user.clear(form.getByLabelText('Keywords'));
    await user.type(form.getByLabelText('Keywords'), 'armoured convoy, northern road');
    await user.click(form.getByRole('button', { name: 'Add alert rule' }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]).toMatchObject({ keywords: ['armoured convoy', 'northern road'] });
    expect((writes[0] as { description: string }).description).toContain(LONG);
  });

  it('discards the draft on Discard', async () => {
    const { user, form } = await draftFromReport();
    await user.click(form.getByRole('button', { name: 'Discard draft' }));
    expect(readReportWatchDraft()).toBeNull();
    expect(screen.queryByRole('region', { name: 'Draft from a report' })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Alert rule name')).toHaveValue('');
  });

  it('discards the draft when the signed-in account changes', async () => {
    await draftFromReport();
    expect(readReportWatchDraft()).not.toBeNull();
    act(() => applySession('admin'));
    expect(readReportWatchDraft()).toBeNull();
    await waitFor(() =>
      expect(screen.queryByRole('region', { name: 'Draft from a report' })).not.toBeInTheDocument(),
    );
  });

  it('keeps a team report draft in its team and refuses it after membership is lost', async () => {
    reportWith({ team_id: team.id });
    server.use(http.get('/api/teams', () => HttpResponse.json({ items: [] })));
    const writes = trackRuleWrites();
    const { user, form } = await draftFromReport();
    expect(
      await form.findByText(/You can no longer create alert rules in the report's team/),
    ).toBeVisible();
    await user.click(form.getByRole('button', { name: 'Add alert rule' }));
    expect(
      await form.findByRole('alert', { name: 'Check these fields and try again:' }),
    ).toHaveTextContent('Workspace');
    expect(writes).toEqual([]);
    server.use(
      http.get('/api/teams', () => HttpResponse.json({ items: [team] })),
      http.get('/api/teams/:id', () => HttpResponse.json(roster)),
    );
  });
});

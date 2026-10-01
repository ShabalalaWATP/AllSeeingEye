import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { plan } from '@/test/fixtures';
import { planEvidence } from '@/test/fixtures.direction';
import { renderApp } from '@/test/render';
import { reportJob } from '@/test/reportJobFixture';
import { server } from '@/test/server';

const briefId = 'd73c2988-d2ca-4482-9e39-7269e876eaa0';
const now = '2026-09-14T10:00:00Z';
const twoPirPlan = {
  ...plan,
  aoi_id: null,
  pirs: [
    ...plan.pirs,
    {
      code: 'PIR-2',
      text: 'Who is resupplying the axis?',
      sirs: [{ code: 'SIR-2.1', text: 'Rail convoys', keywords: ['rail'], categories: [] }],
    },
  ],
};

function brief(draft: BriefDraft): ResearchBrief {
  return {
    ...draft,
    identity: {
      id: briefId,
      revision: 1,
      owner_id: '22222222-2222-4222-8222-222222222222',
      team_id: draft.team_id,
      title: draft.title,
      created_at: now,
      revised_at: now,
      preset_id: draft.preset_id,
      preset_version: draft.preset_version,
      schema_version: 1,
      origin: 'authored',
      published: false,
    },
  };
}

interface Traffic {
  saved: BriefDraft[];
  runs: Record<string, unknown>[];
  reopened: number;
}

function serve(current: () => typeof twoPirPlan, runStatus: () => number = () => 202): Traffic {
  const traffic: Traffic = { saved: [], runs: [], reopened: 0 };
  let stored: ResearchBrief | null = null;
  server.use(
    http.get(`/api/direction/plans/${plan.id}/definition`, () => HttpResponse.json(current())),
    http.post('/api/research/briefs', async ({ request }) => {
      const body = (await request.json()) as BriefDraft;
      traffic.saved.push(body);
      stored = brief(body);
      return HttpResponse.json({ brief: stored }, { status: 201 });
    }),
    http.get(`/api/research/briefs/${briefId}/revisions/1`, () => {
      traffic.reopened += 1;
      return HttpResponse.json({ brief: stored });
    }),
    http.post('/api/report-jobs/from-brief', async ({ request }) => {
      traffic.runs.push((await request.json()) as Record<string, unknown>);
      const status = runStatus();
      if (status === 409)
        return HttpResponse.json(
          {
            error: {
              code: 'conflict',
              message: 'The collection plan changed after you reviewed it.',
            },
          },
          { status },
        );
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  return traffic;
}

async function runOnceWhenReady({ user }: ReturnType<typeof renderApp>, traffic: Traffic) {
  // Saving navigates to the exact saved revision, which reloads and remounts the editor.
  await waitFor(() => expect(traffic.reopened).toBe(1));
  await screen.findByRole('region', { name: 'Research Brief editor' });
  await waitFor(() => expect(screen.getByRole('button', { name: 'Run once' })).toBeEnabled());
  await user.click(screen.getByRole('button', { name: 'Run once' }));
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('plan-led durable research', () => {
  it('opens Research from the plan for review without starting any work', async () => {
    const traffic = serve(() => twoPirPlan);
    server.use(
      http.get(`/api/direction/plans/${plan.id}`, () =>
        HttpResponse.json({ ...planEvidence, plan: twoPirPlan, aoi: null }),
      ),
    );
    const setItem = vi.spyOn(Storage.prototype, 'setItem');
    const { user, router } = renderApp(`/direction/plans/${plan.id}`, 'user');
    await user.click(await screen.findByRole('link', { name: 'Generate assessment' }));
    const context = await screen.findByRole('region', { name: 'Collection plan' });
    expect(router.state.location.search).toBe(`?brief=new&plan=${plan.id}`);
    expect(await within(context).findByText('Rail convoys')).toBeInTheDocument();
    expect(within(context).getByText('Personal')).toBeInTheDocument();
    expect(within(context).getByText('Nations: UA')).toBeInTheDocument();
    const editor = within(screen.getByRole('region', { name: 'Research Brief editor' }));
    expect(editor.getByLabelText('Main research question')).toHaveValue(twoPirPlan.pirs[0]?.text);
    expect(traffic.runs).toEqual([]);
    expect(traffic.saved).toEqual([]);
    const stored = setItem.mock.calls.map((call) => call[1]).join(' ');
    expect(stored).not.toContain('resupplying');
  });

  it('starts research only on request, with the plan and its reviewed revision', async () => {
    const traffic = serve(() => twoPirPlan);
    const view = renderApp(`/research?brief=new&plan=${plan.id}`, 'user');
    const { user } = view;
    const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
    await screen.findByText('Rail convoys');
    await user.click(editor.getByRole('button', { name: 'Save brief' }));
    await waitFor(() => expect(traffic.saved).toHaveLength(1));
    expect(traffic.saved[0]).toMatchObject({
      title: plan.name,
      team_id: null,
      scope: { plan_id: plan.id },
      question: {
        main: twoPirPlan.pirs[0]?.text,
        requirements: [
          { id: 'PIR-1', question: twoPirPlan.pirs[0]?.text, required: true, priority: 1 },
          { id: 'PIR-2', question: 'Who is resupplying the axis?', required: true, priority: 2 },
        ],
      },
    });
    expect(traffic.runs).toEqual([]);
    await runOnceWhenReady(view, traffic);
    await waitFor(() => expect(traffic.runs).toHaveLength(1));
    expect(traffic.runs[0]).toMatchObject({
      brief_id: briefId,
      revision: 1,
      expected_plan_updated_at: plan.updated_at,
    });
    expect(await screen.findByRole('link', { name: 'Open research job' })).toBeVisible();
  });

  it('blocks a changed plan, reloads it and retries without a second job identity', async () => {
    let current = twoPirPlan;
    let attempts = 0;
    const traffic = serve(
      () => current,
      () => (++attempts === 1 ? 409 : 202),
    );
    const view = renderApp(`/research?brief=new&plan=${plan.id}`, 'user');
    const { user } = view;
    const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
    await screen.findByText('Rail convoys');
    await user.click(editor.getByRole('button', { name: 'Save brief' }));
    await runOnceWhenReady(view, traffic);
    current = { ...twoPirPlan, updated_at: '2026-09-15T08:00:00Z' };
    expect(await screen.findByText(/changed after you reviewed it/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Reload plan' }));
    await user.click(screen.getByRole('button', { name: /^(Run once|Retry research run)$/ }));
    await waitFor(() => expect(traffic.runs).toHaveLength(2));
    expect(traffic.runs[1]?.expected_plan_updated_at).toBe('2026-09-15T08:00:00Z');
    expect(traffic.runs[1]?.request_id).toBe(traffic.runs[0]?.request_id);
  });

  it.each([
    [
      'disabled',
      () => HttpResponse.json({ ...twoPirPlan, enabled: false }),
      /collection plan is disabled/,
    ],
    [
      'missing',
      () => HttpResponse.json({ error: { code: 'not_found', message: 'Gone.' } }, { status: 404 }),
      /no longer exists or is not available/,
    ],
  ])('explains a %s plan and keeps research blocked', async (_, reply, message) => {
    const traffic = serve(() => twoPirPlan);
    server.use(
      http.get(`/api/direction/plans/${plan.id}/definition`, () =>
        traffic.saved.length > 0 ? reply() : HttpResponse.json(twoPirPlan),
      ),
    );
    const { user } = renderApp(`/research?brief=new&plan=${plan.id}`, 'user');
    const editor = within(await screen.findByRole('region', { name: 'Research Brief editor' }));
    await screen.findByText('Rail convoys');
    await user.click(editor.getByRole('button', { name: 'Save brief' }));
    await user.click(await screen.findByRole('button', { name: 'Reload plan' }));
    expect(await screen.findAllByText(message)).not.toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Run once' })).toBeDisabled();
  });

  it('rejects a malformed plan link before any request', async () => {
    renderApp('/research?brief=new&plan=not-a-plan', 'user');
    expect(await screen.findByText('This collection plan link is not valid.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Retry brief' })).toBeInTheDocument();
  });

  it('hands legacy plan assessment bookmarks to Research and keeps specialist templates', async () => {
    const { user } = renderApp(`/reports?template=ask&plan=${plan.id}`, 'user');
    const link = await screen.findByRole('link', { name: 'Continue in Research with this plan' });
    expect(link).toHaveAttribute('href', `/research?brief=new&plan=${plan.id}`);
    expect(screen.queryByRole('form', { name: 'Generate a report' })).toBeNull();
    await user.click(screen.getByRole('button', { name: 'Specialist report templates' }));
    expect(await screen.findByRole('form', { name: 'Generate a report' })).toBeInTheDocument();
  });
});

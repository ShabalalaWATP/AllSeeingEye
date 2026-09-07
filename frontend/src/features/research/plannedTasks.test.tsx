import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { report } from '@/test/fixtures';
import type { ReportRequest } from '@/lib/api/reports';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { followUpRequest } from './followUpScope';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';

it('previews and submits distinct same-source tasks, preserves exact phrases and invalidates changed candidates', async () => {
  const previews: ResearchPlanInput[] = [];
  let submitted: ReportRequest | undefined;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as ResearchPlanInput;
      previews.push(input);
      return HttpResponse.json({
        ...input,
        mode: 'quick',
        focus: 'general',
        subject: null,
        country_iso: null,
        request_limit: 6,
        seconds_limit: 45,
        item_limit: 200,
        policy_version: 'ase-deterministic-plan-v1',
        model_calls: 0,
        translation_calls: 0,
        replans: 0,
        tasks: [
          {
            source_id: 'example',
            source_name: 'Example public search',
            selected: true,
            supported: true,
            planned_terms_supported: true,
            language: 'en',
            terms: [],
            provenance: 'original_terms',
            temporal_scope: 'Recent records',
          },
          ...(input.planned_tasks ?? []).map((task) => ({
            ...task,
            task_id: `operator:${task.id}`,
            source_name: 'Example public search',
            selected: true,
            supported: true,
            planned_terms_supported: true,
            language: 'en',
            provenance: 'operator_supplied_task',
            temporal_scope: 'Recent records',
          })),
        ],
      });
    }),
    http.post('/api/reports', async ({ request }) => {
      submitted = (await request.json()) as ReportRequest;
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  const { user } = renderApp('/research?question=Which%20Acme%20is%20this%3F', 'user');
  await screen.findByLabelText('Your question');
  await user.click(screen.getByText('Collection plan (optional)'));
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  await user.click(screen.getByText('Identity candidates and challenge searches'));
  await user.click(screen.getByRole('button', { name: 'Add identity candidate' }));
  await user.type(screen.getByLabelText('Candidate 1 label'), 'Acme UK');
  fireEvent.change(screen.getByLabelText('Candidate 1 identifiers'), {
    target: { value: 'UK 01234567\nLEI 12345' },
  });
  for (const index of [1, 2]) {
    await user.click(screen.getByRole('button', { name: 'Add challenge or identity search' }));
    await user.selectOptions(screen.getByLabelText(`Search ${index} source`), 'example');
    fireEvent.change(screen.getByLabelText(`Search ${index} exact terms`), {
      target: { value: index === 1 ? 'Acme denial\n"not affiliated"' : 'Acme UK 01234567' },
    });
  }
  await user.selectOptions(screen.getByLabelText('Search 2 purpose'), 'disambiguation');
  await user.selectOptions(screen.getByLabelText('Search 2 candidate'), 'Acme UK');
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  expect(submitted).toBeUndefined();
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  const preview = previews.at(-1)!;
  expect(preview.planned_tasks).toHaveLength(2);
  expect(preview.planned_tasks?.[0]?.terms).toEqual(['Acme denial', '"not affiliated"']);
  expect(preview.planned_tasks?.[1]?.candidate_id).toBe(preview.candidate_hypotheses?.[0]?.id);
  await user.type(screen.getByLabelText('Candidate 1 label'), ' alternative');
  expect(screen.getByText('Previous preview, settings have changed')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(submitted?.research_planned_tasks).toEqual(previews.at(-1)?.planned_tasks),
  );
  expect(submitted?.research_candidate_hypotheses).toEqual(previews.at(-1)?.candidate_hypotheses);
  const parent = {
    ...report,
    report: { ...report.report, scope: { ...report.report.scope, ...submitted } },
  };
  expect(followUpRequest(parent).research_planned_tasks).toEqual(submitted?.research_planned_tasks);
});

it('does not carry candidate drafts into a changed workspace authority', async () => {
  const { user } = renderApp('/research?question=Identity%20check', 'user');
  await screen.findByLabelText('Your question');
  await user.click(screen.getByText('Collection plan (optional)'));
  await user.click(screen.getByText('Identity candidates and challenge searches'));
  await user.click(screen.getByRole('button', { name: 'Add identity candidate' }));
  await user.type(screen.getByLabelText('Candidate 1 label'), 'Private draft candidate');
  act(() => invalidateWorkspaceAccess());
  await waitFor(() =>
    expect(screen.queryByDisplayValue('Private draft candidate')).not.toBeInTheDocument(),
  );
});

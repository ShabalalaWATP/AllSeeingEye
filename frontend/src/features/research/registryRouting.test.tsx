import { reportJob, readReportJobRequest } from '@/test/reportJobFixture';
import { act, fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { report } from '@/test/fixtures';
import type { ReportRequest } from '@/lib/api/reports';
import {
  candidateHypothesisSchema,
  plannedQueryTaskSchema,
  type ResearchPlanInput,
} from '@/lib/api/researchPlan';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { followUpRequest } from '@/lib/followUpScope';

const lookup = {
  candidate_id: 'candidate',
  identifier_id: 'identifier',
  namespace: 'sec_cik' as const,
  original_value: '320193',
  subject: 'CIK:0000320193',
};
const base = {
  question: 'Which company?',
  since: '2026-09-01T00:00:00Z',
  until: '2026-09-02T00:00:00Z',
  languages: ['en'],
  mode: 'quick',
  focus: 'company',
  subject: 'Acme',
  country_iso: null,
  request_limit: 6,
  seconds_limit: 45,
  item_limit: 200,
  policy_version: 'test-plan',
  model_calls: 0,
  translation_calls: 0,
  replans: 0,
};

it('keeps legacy bare identifiers as context and defaults historic tasks to phrase searches', () => {
  expect(
    candidateHypothesisSchema.parse({ id: 'old', label: 'Acme', identifiers: ['320193'] })
      .registry_identifiers,
  ).toEqual([]);
  expect(
    plannedQueryTaskSchema.parse({
      id: 'old',
      source_id: 'news',
      purpose: 'challenge',
      terms: ['Acme denial'],
      candidate_id: null,
    }),
  ).toMatchObject({ route: 'terms', identifier_id: null });
});

it('selects only server-issued exact lookups, preserves original inputs and clears private drafts on access change', async () => {
  const previews: ResearchPlanInput[] = [];
  let submitted: ReportRequest | undefined;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as ResearchPlanInput;
      previews.push(input);
      const candidate = input.candidate_hypotheses?.[0];
      const identifier = candidate?.registry_identifiers?.[0];
      if (identifier?.value === 'invalid')
        return HttpResponse.json(
          {
            error: {
              code: 'invalid_request',
              message: 'Identifier does not match its explicit registry namespace',
            },
          },
          { status: 422 },
        );
      const option =
        candidate && identifier
          ? {
              ...lookup,
              candidate_id: candidate.id,
              identifier_id: identifier.id,
              namespace: identifier.namespace,
              original_value: identifier.value,
            }
          : null;
      return HttpResponse.json({
        ...base,
        ...input,
        tasks: [
          {
            source_id: 'sec',
            source_name: 'SEC submissions',
            selected: true,
            supported: false,
            planned_terms_supported: false,
            language: null,
            terms: [],
            provenance: 'original_terms',
            temporal_scope: 'Current filings; original filing dates filter results.',
            registry_namespaces: ['sec_cik'],
            registry_options: option ? [option] : [],
          },
          ...(input.planned_tasks ?? []).map((task) => ({
            ...task,
            source_name: 'SEC submissions',
            selected: true,
            supported: true,
            language: null,
            terms: [],
            provenance: 'operator_supplied_task',
            temporal_scope: 'Current filings only.',
            registry_lookup: option,
          })),
        ],
      });
    }),
    http.post('/api/report-jobs', async ({ request }) => {
      submitted = await readReportJobRequest(request);
      return HttpResponse.json(reportJob(), { status: 202 });
    }),
  );
  const { user } = renderApp('/research?question=Which%20Acme%20is%20this%3F', 'user');
  await screen.findByLabelText('Your question');
  fireEvent.change(screen.getByLabelText('Research focus'), { target: { value: 'company' } });
  fireEvent.change(screen.getByLabelText('Company name'), { target: { value: 'Acme' } });
  await user.click(screen.getByText('Collection plan (optional)'));
  await user.click(screen.getByText('Identity candidates and challenge searches'));
  await user.click(screen.getByRole('button', { name: 'Add identity candidate' }));
  fireEvent.change(screen.getByLabelText('Candidate 1 label'), {
    target: { value: 'Acme candidate' },
  });
  await user.click(screen.getByRole('button', { name: 'Add registry identifier' }));
  await user.selectOptions(
    screen.getByLabelText('Candidate 1 registry identifier 1 type'),
    'sec_cik',
  );
  fireEvent.change(screen.getByLabelText('Candidate 1 registry identifier 1 value'), {
    target: { value: 'invalid' },
  });
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await waitFor(() => expect(previews).toHaveLength(1));
  expect(screen.getByRole('button', { name: 'Add challenge or identity search' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Candidate 1 registry identifier 1 value'), {
    target: { value: '320193' },
  });
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  await user.click(screen.getByRole('button', { name: 'Add challenge or identity search' }));
  await user.selectOptions(screen.getByLabelText('Search 1 method'), 'candidate_identifier');
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await waitFor(() => expect(previews).toHaveLength(3));
  expect(previews.at(-1)?.planned_tasks).toEqual([]);
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  expect(submitted).toBeUndefined();
  await user.selectOptions(screen.getByLabelText('Search 1 registry lookup'), '0');
  expect(screen.queryByLabelText('Search 1 exact terms')).not.toBeInTheDocument();
  expect(screen.queryByLabelText('Search 1 purpose')).not.toBeInTheDocument();
  expect(screen.getByText('CIK:0000320193')).toBeVisible();
  expect(screen.getByRole('option', { name: /SEC submissions.*Acme candidate/ })).toBeVisible();
  fireEvent.change(screen.getByLabelText('Candidate 1 label'), {
    target: { value: 'Acme revised candidate' },
  });
  expect(screen.getByLabelText('Search 1 registry lookup')).toHaveValue('');
  expect(
    screen.queryByRole('option', { name: /SEC submissions.*Acme candidate/ }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(submitted?.research_planned_tasks?.[0]).toMatchObject({
      route: 'candidate_identifier',
      purpose: 'disambiguation',
      source_id: 'sec',
      terms: [],
    }),
  );
  const parent = {
    ...report,
    report: { ...report.report, scope: { ...report.report.scope, ...submitted } },
  };
  expect(followUpRequest(parent).research_planned_tasks).toEqual(submitted?.research_planned_tasks);
  expect(followUpRequest(parent).research_candidate_hypotheses).toEqual(
    submitted?.research_candidate_hypotheses,
  );
  act(() => invalidateWorkspaceAccess());
  await waitFor(() => expect(screen.queryByDisplayValue('320193')).not.toBeInTheDocument());
});

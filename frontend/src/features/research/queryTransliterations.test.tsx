import { fireEvent, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { expect, it } from 'vitest';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';
import { report } from '@/test/fixtures';
import type { ResearchPlanInput } from '@/lib/api/researchPlan';
import { followUpRequest } from './followUpScope';
import type { ReportRequest } from '@/lib/api/reports';

it('previews and submits distinct translation and transliteration with exact original linkage', async () => {
  const previews: ResearchPlanInput[] = [];
  let submitted: ReportRequest | undefined;
  server.use(
    http.post('/api/research/runs/plan', async ({ request }) => {
      const input = (await request.json()) as ResearchPlanInput;
      previews.push(input);
      return HttpResponse.json({
        ...input,
        subject: null,
        country_iso: null,
        request_limit: 6,
        seconds_limit: 45,
        item_limit: 200,
        policy_version: 'fixture-plan',
        model_calls: 0,
        translation_calls: 0,
        replans: 0,
        tasks: (input.query_variants ?? []).map((variant) => ({
          source_id: 'search',
          source_name: 'Compatible search',
          selected: true,
          supported: true,
          language: 'en',
          terms: variant.terms,
          query_variant: variant,
          provenance: 'operator_supplied_variant',
          temporal_scope: 'Selected date interval.',
        })),
      });
    }),
    http.post('/api/reports', async ({ request }) => {
      submitted = (await request.json()) as ReportRequest;
      return HttpResponse.json(report, { status: 201 });
    }),
  );
  const { user } = renderApp('/research?question=Which%20company%3F', 'user');
  await screen.findByLabelText('Your question');
  await user.click(screen.getByText('Collection plan (optional)'));
  await user.click(screen.getByLabelText('Supply exact search terms'));
  const original = '\u0634\u0631\u06a9\u062a\u200c\u0627\u0644\u0641';
  fireEvent.change(screen.getByLabelText('Original search terms'), { target: { value: original } });
  await user.click(screen.getByText('Language-specific search terms'));
  fireEvent.change(screen.getByLabelText('Search terms: English'), {
    target: { value: 'Company A' },
  });
  fireEvent.change(screen.getByLabelText('Translation originals: English'), {
    target: { value: original },
  });
  await user.click(screen.getByText('Supply transliteration: English'));
  fireEvent.change(screen.getByLabelText('Transliteration originals: English'), {
    target: { value: original },
  });
  fireEvent.change(screen.getByLabelText('Transliterated terms: English'), {
    target: { value: 'Sherkat-e Alef' },
  });
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  expect(previews).toHaveLength(0);
  expect(screen.getByText(/Provide source and target script codes/)).toBeVisible();
  fireEvent.change(screen.getByLabelText('Original script: English'), {
    target: { value: 'Arab' },
  });
  fireEvent.change(screen.getByLabelText('Transliteration script: English'), {
    target: { value: 'Latn' },
  });
  fireEvent.change(screen.getByLabelText('Transliteration method: English'), {
    target: { value: 'Operator convention' },
  });
  await user.click(screen.getByRole('button', { name: 'Preview collection plan' }));
  await screen.findByText('Current preview');
  expect(screen.getByText('Exact outbound term: Sherkat-e Alef')).toBeVisible();
  expect(screen.getByText('Exact outbound term: Company A')).toBeVisible();
  expect(previews[0]?.query_variants).toEqual([
    { language: 'en', kind: 'translation', terms: ['Company A'], original_terms: [original] },
    {
      language: 'en',
      kind: 'transliteration',
      terms: ['Sherkat-e Alef'],
      original_terms: [original],
      source_script: 'Arab',
      target_script: 'Latn',
      method: 'Operator convention',
    },
  ]);
  await user.click(screen.getByRole('button', { name: 'Start research' }));
  await waitFor(() =>
    expect(submitted?.research_query_variants).toEqual(previews[0]?.query_variants),
  );
  const followUp = followUpRequest({
    ...report,
    report: { ...report.report, scope: { ...report.report.scope, ...submitted, country: null } },
  });
  expect(followUp.research_query_variants?.[1]).toMatchObject(previews[0]!.query_variants![1]!);
  expect(followUp.research_terms).toEqual([original]);
});

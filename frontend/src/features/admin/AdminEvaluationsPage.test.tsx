import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { EvaluationCatalogue, EvaluationRun } from '@/lib/api/evaluations';
import { llmProfiles } from '@/test/fixtures';
import { apiError } from '@/test/handlers';
import { renderApp } from '@/test/render';
import { server } from '@/test/server';

const BASE = '/api/admin/llm/evaluations';

const catalogue: EvaluationCatalogue = {
  cases: [
    {
      id: 'conflicting_reports',
      casebook: 'core',
      title: 'Conflicting reports',
      fingerprint: 'a'.repeat(64),
    },
    { id: 'date_pitfall', casebook: 'core', title: 'Date pitfall', fingerprint: 'b'.repeat(64) },
    {
      id: 'ru_language',
      casebook: 'regional',
      title: 'Russian language',
      fingerprint: 'c'.repeat(64),
    },
  ],
  calls_per_case: 4,
  max_calls: 200,
  max_cases: 40,
  estimate_notice: 'Estimate only: selected cases multiplied by the usual calls per case.',
  result_notice: 'Deterministic structural checks only; not accuracy.',
};

function run(overrides: Partial<EvaluationRun> = {}): EvaluationRun {
  return {
    id: '99999999-9999-4999-8999-999999999999',
    profile_id: llmProfiles[0]!.id,
    profile_name: 'Local Llama',
    model: 'llama3.1:8b',
    status: 'running',
    stop_reason: null,
    cancel_requested: false,
    case_ids: ['conflicting_reports', 'date_pitfall'],
    case_fingerprints: { conflicting_reports: 'a'.repeat(64), date_pitfall: 'b'.repeat(64) },
    max_calls: 8,
    estimated_calls: 8,
    calls_reserved: 1,
    calls_failed: 0,
    prompt_tokens: null,
    completion_tokens: null,
    results: [],
    has_artefact: false,
    created_at: '2026-10-01T09:00:00Z',
    finished_at: null,
    notice: 'Deterministic structural checks only; not accuracy.',
    ...overrides,
  };
}

const completed = run({
  status: 'completed',
  calls_reserved: 4,
  prompt_tokens: 120,
  completion_tokens: 80,
  has_artefact: true,
  finished_at: '2026-10-01T09:05:00Z',
  results: [
    {
      case_id: 'conflicting_reports',
      fingerprint: 'a'.repeat(64),
      report_status: 'needs_review',
      model_calls: 4,
      prompt_tokens: 120,
      completion_tokens: 80,
      checks: {
        final_citation_reference_validity: 1,
        required_evidence_cited_recall: 0.5,
        counterevidence_referenced_any_role_recall: null,
        uncited_statement_fields: 0,
        validation_errors: 0,
      },
    },
  ],
});

function serve(runs: EvaluationRun[]) {
  server.use(
    http.get(`${BASE}/catalogue`, () => HttpResponse.json(catalogue)),
    http.get(BASE, () => HttpResponse.json({ items: runs })),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('AdminEvaluationsPage', () => {
  it('shows the estimate before starting and posts the chosen subset and cap', async () => {
    serve([]);
    let posted: unknown = null;
    server.use(
      http.post(BASE, async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json(run(), { status: 202 });
      }),
    );
    const { user } = renderApp('/admin/evaluations', 'admin');
    await screen.findByRole('heading', { name: 'Evaluations', level: 1 });
    expect(await screen.findByText('No evaluation runs yet.')).toBeInTheDocument();
    const start = screen.getByRole('button', { name: 'Start evaluation' });
    expect(start).toBeDisabled();

    await user.click(screen.getByRole('checkbox', { name: 'Select every core case' }));
    expect(screen.getByText(/Expected usage \(estimate\):/).closest('p')).toHaveTextContent(
      '2 cases × 4 calls = 8 calls',
    );
    expect(screen.getByRole('textbox', { name: /Call cap/ })).toHaveValue('8');
    await user.click(screen.getByRole('checkbox', { name: /Russian language/ }));
    expect(screen.getByText(/Expected usage/).closest('p')).toHaveTextContent(
      '3 cases × 4 calls = 12 calls',
    );
    const cap = screen.getByRole('textbox', { name: /Call cap/ });
    await user.clear(cap);
    await user.type(cap, '6');
    await user.click(start);

    expect(posted).toEqual({
      profile_id: llmProfiles[0]!.id,
      case_ids: ['conflicting_reports', 'date_pitfall', 'ru_language'],
      max_calls: 6,
    });
    const card = await screen.findByRole('article', { name: /Evaluation of Local Llama/ });
    expect(within(card).getByText('Running')).toBeInTheDocument();
    expect(within(card).getByText('1 of 8 (estimate 8)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start evaluation' })).toBeDisabled();
  });

  it('refuses an invalid call cap', async () => {
    serve([]);
    const { user } = renderApp('/admin/evaluations', 'admin');
    await user.click(await screen.findByRole('checkbox', { name: /Date pitfall/ }));
    const cap = screen.getByRole('textbox', { name: /Call cap/ });
    await user.clear(cap);
    await user.type(cap, '999');
    expect(screen.getByText('Enter a whole number from 1 to 200.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start evaluation' })).toBeDisabled();
  });

  it('reports a run already in progress', async () => {
    serve([]);
    server.use(
      http.post(BASE, () => apiError(409, 'conflict', 'An evaluation run is already in progress.')),
    );
    const { user } = renderApp('/admin/evaluations', 'admin');
    await user.click(await screen.findByRole('checkbox', { name: /Date pitfall/ }));
    await user.click(screen.getByRole('button', { name: 'Start evaluation' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'An evaluation run is already in progress.',
    );
  });

  it('cancels a running run', async () => {
    serve([run()]);
    let cancelled = false;
    server.use(
      http.post(`${BASE}/:id/cancel`, () => {
        cancelled = true;
        return HttpResponse.json(run({ cancel_requested: true }));
      }),
    );
    const { user } = renderApp('/admin/evaluations', 'admin');
    await user.click(await screen.findByRole('button', { name: 'Cancel run' }));
    expect(cancelled).toBe(true);
    expect(await screen.findByText('Cancelling')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel run' })).toBeDisabled();
  });

  it('shows structural checks, never accuracy, and downloads the results', async () => {
    serve([completed]);
    let downloaded = false;
    server.use(
      http.get(`${BASE}/:id/artefact`, () => {
        downloaded = true;
        return new HttpResponse(new Uint8Array([80, 75]), {
          headers: {
            'Content-Type': 'application/zip',
            'Content-Disposition': 'attachment; filename="evaluation-run.zip"',
          },
        });
      }),
    );
    if (!('createObjectURL' in URL)) {
      Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => undefined });
    }
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:evaluation');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    const { user } = renderApp('/admin/evaluations', 'admin');
    const card = await screen.findByRole('article', { name: /Evaluation of Local Llama/ });
    expect(within(card).getByText('Completed')).toBeInTheDocument();
    expect(within(card).getByText('Structural checks per case (not accuracy)')).toBeInTheDocument();
    expect(within(card).getByText('50%')).toBeInTheDocument();
    expect(within(card).getByText('Not applicable')).toBeInTheDocument();
    expect(within(card).queryByText(/^Accuracy/i)).not.toBeInTheDocument();
    await user.click(within(card).getByRole('button', { name: 'Download results' }));
    expect(downloaded).toBe(true);
  });

  it('explains when no assessment connection exists', async () => {
    serve([]);
    server.use(
      http.get('/api/admin/llm/profiles', () =>
        HttpResponse.json({
          items: [{ ...llmProfiles[0]!, roles: ['embeddings'] }],
          encryption_available: true,
        }),
      ),
    );
    renderApp('/admin/evaluations', 'admin');
    expect(
      await screen.findByRole('option', { name: 'No assessment connection is configured' }),
    ).toBeInTheDocument();
  });
});

import { act, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import * as evaluations from '@/lib/api/evaluations';
import type { EvaluationCatalogue } from '@/lib/api/evaluations';
import * as llm from '@/lib/api/llm';

import AdminEvaluationsPage from './AdminEvaluationsPage';

it('replaces the loading message with an access error without offering an incomplete start form', async () => {
  let reject!: (error: unknown) => void;
  const catalogue = new Promise<EvaluationCatalogue>((_resolve, fail) => {
    reject = fail;
  });
  vi.spyOn(evaluations, 'fetchEvaluationCatalogue').mockReturnValue(catalogue);
  vi.spyOn(evaluations, 'fetchEvaluationRuns').mockResolvedValue([]);
  vi.spyOn(llm, 'fetchLlmProfiles').mockResolvedValue({ items: [], encryption_available: true });
  render(<AdminEvaluationsPage />);
  expect(screen.getByText('Loading the evaluation casebook')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Start evaluation' })).not.toBeInTheDocument();
  await act(async () => {
    reject(new ApiError(403, 'forbidden', 'Administrator access has ended.'));
    await catalogue.catch(() => undefined);
  });
  expect(screen.getByRole('alert')).toHaveTextContent('Administrator access has ended.');
  expect(screen.queryByText('Loading the evaluation casebook')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Start evaluation' })).not.toBeInTheDocument();
  expect(screen.queryByText('No evaluation runs yet.')).not.toBeInTheDocument();
});

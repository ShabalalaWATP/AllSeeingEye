import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { ClaimGenerationNote } from './ClaimGenerationNote';
import { claimGenerationSchema } from '@/lib/api/claimGeneration';

it('distinguishes a legacy report from an attempted empty result', () => {
  const view = render(<ClaimGenerationNote />);
  expect(screen.getByText(/not recorded/)).toBeInTheDocument();
  view.rerender(
    <ClaimGenerationNote
      receipt={claimGenerationSchema.parse({
        schema_version: 1,
        status: 'empty',
        revision_ids: [],
        model_origin: null,
      })}
    />,
  );
  expect(screen.getByText(/does not confirm an absence/)).toBeInTheDocument();
  expect(screen.queryByText(/not recorded/)).not.toBeInTheDocument();
});

it('describes initial generated revisions separately from later corrections', () => {
  const receipt = claimGenerationSchema.parse({
    schema_version: 1,
    status: 'completed',
    revision_ids: ['revision-1', 'revision-2'],
    model_origin: {
      batch_id: 'batch-1',
      profile_id: 'profile-1',
      profile_revision: 1,
      provider: 'openai_compatible',
      requested_model: 'configured-model',
      returned_model: 'returned-model',
      input_sha256: 'a'.repeat(64),
      method_version: 'ase-claim-proposals-v1',
      generated_at: '2026-09-07T00:00:00Z',
    },
  });
  render(<ClaimGenerationNote receipt={receipt} />);
  expect(screen.getByText(/2 initial proposed claims/)).toHaveTextContent(/later corrections/);
});

it('discloses a storage limit without claiming the model found no evidence', () => {
  render(
    <ClaimGenerationNote
      receipt={claimGenerationSchema.parse({
        schema_version: 1,
        status: 'quota_exceeded',
        revision_ids: [],
        model_origin: null,
      })}
    />,
  );
  expect(screen.getByText(/storage allowance/)).toHaveTextContent('No automatic claims were saved');
  expect(screen.queryByText(/found no supported/)).not.toBeInTheDocument();
});

it('rejects an unknown receipt version instead of treating it as a current result', () => {
  expect(
    claimGenerationSchema.safeParse({
      schema_version: 2,
      status: 'empty',
      revision_ids: [],
      model_origin: null,
    }).success,
  ).toBe(false);
});

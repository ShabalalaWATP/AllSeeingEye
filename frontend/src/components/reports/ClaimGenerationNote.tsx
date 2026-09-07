import type { ClaimGenerationReceipt } from '@/lib/api/claimGeneration';

const messages = {
  empty: 'The model found no supported proposals. This does not confirm an absence of events.',
  invalid: 'Automatic proposals failed validation. No generated claims were saved.',
  unavailable: 'The model was unavailable during automatic claim generation.',
  unsupported:
    'Automatic claim generation did not support this report input. Manual review is available.',
  no_model: 'No assessment model was available for automatic claim generation.',
  rate_limited: 'Automatic claim generation reached its model-call allowance.',
  quota_exceeded: 'The claim storage allowance was reached. No automatic claims were saved.',
};

export function ClaimGenerationNote({ receipt }: { receipt?: ClaimGenerationReceipt | null }) {
  return (
    <p className="mb-3 text-sm text-muted">
      {receipt
        ? receipt.status === 'completed'
          ? `${receipt.revision_ids.length} initial proposed claims were generated with this report. Review their evidence; later corrections are recorded separately.`
          : messages[receipt.status]
        : 'Automatic claim generation was not recorded for this report version.'}
    </p>
  );
}

import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { SavedCollectionPlan } from './SavedCollectionPlan';

it('preserves and renders the frozen plan independently of collection attempt outcomes', () => {
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    plan: {
      question: 'A question',
      since: '2026-01-01T00:00:00Z',
      until: '2026-01-02T00:00:00Z',
      languages: ['fa'],
      mode: 'quick',
      focus: 'general',
      subject: null,
      country_iso: 'IR',
      tasks: [
        {
          source_id: 'example',
          source_name: 'Example record source',
          selected: true,
          supported: true,
          language: 'fa',
          terms: ['بندر'],
          provenance: 'operator_supplied_variant',
          temporal_scope: 'requested_window',
        },
      ],
      request_limit: 8,
      seconds_limit: 20,
      item_limit: 50,
      policy_version: 'v1',
      model_calls: 0,
      translation_calls: 0,
      replans: 0,
    },
  });
  render(<SavedCollectionPlan plan={receipt.plan!} />);
  expect(screen.getByText('بندر')).toBeVisible();
  expect(screen.getByText(/Operator-supplied language terms/)).toBeVisible();
  expect(screen.getByText(/8 requests, 20 seconds, 50 items/)).toBeVisible();
});

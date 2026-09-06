import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { planSchema } from '@/lib/api/researchPlan';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { SavedCollectionPlan } from './SavedCollectionPlan';

const frozenPlan = {
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
};
const translation = {
  policy_version: 'query-translation-v1',
  original_terms: ['Port ABC-123'],
  languages: ['fa', 'zh-Hant'],
  model: 'configured-model',
  status: 'completed',
  variants: [
    { language: 'fa', terms: ['بندر ABC-123'] },
    { language: 'zh-Hant', terms: ['港口 ABC-123'] },
  ],
};

it('preserves and renders the frozen plan independently of collection attempt outcomes', () => {
  const receipt = researchReceiptSchema.parse({ ...researchReceipt, plan: frozenPlan });
  render(<SavedCollectionPlan plan={receipt.plan!} />);
  expect(screen.getByText('بندر')).toBeVisible();
  expect(screen.getByText(/Operator-supplied language terms/)).toBeVisible();
  expect(screen.getByText(/8 requests, 20 seconds, 50 items/)).toBeVisible();
  expect(
    screen.queryByRole('region', { name: 'Automatic query translation' }),
  ).not.toBeInTheDocument();
});

it('displays the recorded translation phrases and model without claiming verified meaning', () => {
  const plan = planSchema.parse({
    ...frozenPlan,
    translation,
    tasks: [
      {
        ...frozenPlan.tasks[0],
        provenance: 'machine_translated_variant',
        query_language: 'zh-Hant',
      },
    ],
  });
  render(<SavedCollectionPlan plan={plan} />);
  const section = within(screen.getByRole('region', { name: 'Automatic query translation' }));
  expect(
    section.getByText(/Completed: generated phrases passed syntax and identifier checks only/),
  ).toBeVisible();
  expect(
    section.getByText(/Translation meaning has not been independently verified/),
  ).toBeVisible();
  expect(section.getByText('Port ABC-123')).toBeVisible();
  expect(section.getByText('بندر ABC-123')).toHaveAttribute('dir', 'auto');
  expect(section.getByText('港口 ABC-123')).toBeVisible();
  expect(section.getByText('configured-model')).toBeVisible();
  expect(section.getByText('query-translation-v1')).toBeVisible();
  expect(screen.getByText('Query language: zh-Hant')).toBeVisible();
  expect(screen.getByText(/Machine-translated search terms, meaning unverified/)).toBeVisible();
});

it.each([
  ['failed', 'Failed: no valid translation result was available; original terms were retained.'],
  [
    'unavailable',
    'Unavailable: no translation model was configured, so no translation call was made.',
  ],
])('shows the recorded %s status without suggesting completed translation', (status, message) => {
  const plan = planSchema.parse({
    ...frozenPlan,
    translation: {
      ...translation,
      status,
      variants: [],
      model: status === 'unavailable' ? '' : 'configured-model',
    },
  });
  render(<SavedCollectionPlan plan={plan} />);
  expect(screen.getByText(message)).toBeVisible();
  expect(screen.getByText('No translated phrases recorded.')).toBeVisible();
  expect(screen.queryByText(/Completed:/)).not.toBeInTheDocument();
  expect(screen.getByText('Port ABC-123')).toBeVisible();
});

it('rejects unrecognised translation status instead of rendering an invented success', () => {
  expect(
    planSchema.safeParse({ ...frozenPlan, translation: { ...translation, status: 'verified' } })
      .success,
  ).toBe(false);
});

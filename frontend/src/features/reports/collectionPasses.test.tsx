import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it } from 'vitest';

import { researchReceiptSchema } from '@/lib/api/reportResearch';
import { researchReceipt } from '@/test/fixtures.researchMetadata';
import { ResearchCoverage } from './ResearchCoverage';

const attempt = {
  source_id: 'example',
  source_name: 'Example search source',
  status: 'empty',
  result_count: 0,
  explanation: 'No results returned for this query.',
  language: 'en',
};
function savedPlan(terms: string[]) {
  return {
    question: 'What changed?',
    since: researchReceipt.since,
    until: researchReceipt.until,
    languages: ['en'],
    mode: 'quick',
    focus: 'general',
    subject: null,
    country_iso: null,
    tasks: [
      {
        source_id: 'example',
        source_name: 'Example search source',
        selected: true,
        supported: true,
        language: 'en',
        query_language: 'en',
        terms,
        provenance: 'original_terms',
        temporal_scope: 'requested_window',
      },
    ],
    request_limit: 8,
    seconds_limit: 20,
    item_limit: 50,
    policy_version: 'bounded-v1',
    model_calls: 0,
    translation_calls: 0,
    replans: 0,
  };
}

it('retains the original empty outcome and later successful outcome under one shared budget', async () => {
  const completed = {
    ...attempt,
    status: 'completed',
    result_count: 1,
    explanation: 'One matching result returned after replanning.',
  };
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    terms: ['revised harbour query'],
    attempts: [completed],
    collected_items: 1,
    passes: [
      {
        terms: ['original port query'],
        attempts: [attempt],
        plan: savedPlan(['original port query']),
      },
      {
        terms: ['revised harbour query'],
        attempts: [completed],
        plan: savedPlan(['revised harbour query']),
      },
    ],
  });
  render(<ResearchCoverage receipt={receipt} />);
  const user = userEvent.setup();
  await user.click(screen.getByText('Collection coverage · 1 source outcome · 1 item collected'));
  expect(screen.getByText(/not the total number of HTTP requests/)).toBeVisible();
  expect(screen.getByText(/one shared collection budget/)).toBeVisible();
  expect(screen.getByText(/An empty search does not establish absence of events/)).toBeVisible();
  const first = within(screen.getByRole('region', { name: 'Collection pass 1' }));
  const second = within(screen.getByRole('region', { name: 'Collection pass 2' }));
  expect(first.getAllByText('original port query')[0]).toBeVisible();
  expect(first.getByText(/empty · 0 results/i)).toBeVisible();
  expect(second.getAllByText('revised harbour query')[0]).toBeVisible();
  expect(second.getByText(/completed · 1 result/i)).toBeVisible();
  expect(
    within(screen.getByRole('region', { name: 'Latest source outcomes' })).queryByText(/empty ·/i),
  ).not.toBeInTheDocument();
  await user.click(first.getByText('Saved plan for pass 1'));
  await user.click(second.getByText('Saved plan for pass 2'));
  expect(first.getByRole('region', { name: 'Saved collection plan' })).toBeVisible();
  expect(second.getByRole('region', { name: 'Saved collection plan' })).toBeVisible();
});

it('defaults missing legacy passes to an empty list without inventing an initial pass', async () => {
  const { passes: _passes, ...legacy } = { ...researchReceipt, passes: [] };
  const receipt = researchReceiptSchema.parse(legacy);
  expect(receipt.passes).toEqual([]);
  render(<ResearchCoverage receipt={receipt} />);
  await userEvent.setup().click(screen.getByText(/Collection coverage/));
  expect(screen.queryByRole('region', { name: 'Collection passes' })).not.toBeInTheDocument();
  expect(screen.getByRole('region', { name: 'Latest source outcomes' })).toBeVisible();
});

it('shows missing per-pass terms, plans and outcomes without implying successful collection', async () => {
  const receipt = researchReceiptSchema.parse({
    ...researchReceipt,
    attempts: [],
    passes: [{ terms: [], attempts: [], plan: null }],
  });
  render(<ResearchCoverage receipt={receipt} />);
  await userEvent.setup().click(screen.getByText(/Collection coverage/));
  const pass = within(screen.getByRole('region', { name: 'Collection pass 1' }));
  expect(pass.getByText('No search terms recorded')).toBeVisible();
  expect(pass.getByText('No collection attempts recorded.')).toBeVisible();
  expect(pass.getByText('No plan recorded for this pass.')).toBeVisible();
  expect(pass.queryByText(/completed/i)).not.toBeInTheDocument();
});

it('rejects excess passes and invalid nested outcome states', () => {
  const pass = { terms: [], attempts: [attempt], plan: null };
  expect(
    researchReceiptSchema.safeParse({ ...researchReceipt, passes: [pass, pass, pass] }).success,
  ).toBe(false);
  expect(
    researchReceiptSchema.safeParse({
      ...researchReceipt,
      passes: [{ ...pass, attempts: [{ ...attempt, status: 'verified' }] }],
    }).success,
  ).toBe(false);
});

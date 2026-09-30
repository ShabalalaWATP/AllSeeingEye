import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it } from 'vitest';

import type { BriefDraft } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';

import { BriefOptionsEditor } from './BriefOptionsEditor';

function editor(initial: BriefDraft = newBriefDraft()) {
  let current = initial;
  function Harness() {
    const [draft, setDraft] = useState(initial);
    return (
      <BriefOptionsEditor
        draft={draft}
        change={(next) => {
          current = next;
          setDraft(next);
        }}
      />
    );
  }
  return { ...render(<Harness />), user: userEvent.setup(), draft: () => current };
}

it('stores trimmed search terms and explicit source selection, then clears obsolete restrictions', async () => {
  const view = editor();
  const terms = screen.getByLabelText('Search terms, one per line');
  await view.user.type(terms, ' port \ntraffic\n');
  expect(view.draft().collection.terms).toEqual(['port', 'traffic']);
  await view.user.clear(terms);
  expect(view.draft().collection.terms).toBeNull();
  await view.user.selectOptions(screen.getByLabelText('Source policy'), 'selected_only');
  expect(view.draft().collection.source_ids).toEqual([]);
  await view.user.type(
    screen.getByLabelText('Selected source IDs, one per line'),
    'feed-a\nfeed-b',
  );
  expect(view.draft().collection.source_ids).toEqual(['feed-a', 'feed-b']);
  await view.user.selectOptions(screen.getByLabelText('Source policy'), 'all_eligible');
  expect(view.draft().collection.source_ids).toBeNull();
  expect(screen.queryByLabelText('Selected source IDs, one per line')).not.toBeInTheDocument();
  expect(view.draft().output).toEqual(newBriefDraft().output);
});

it('renders an unfinished selected-source draft without inventing source IDs', async () => {
  const draft = newBriefDraft();
  draft.collection.source_policy = 'selected_only';
  const view = editor(draft);
  expect(screen.getByLabelText('Selected source IDs, one per line')).toHaveValue('');
  await view.user.type(screen.getByLabelText('Selected source IDs, one per line'), 'reviewed-feed');
  expect(view.draft().collection.source_ids).toEqual(['reviewed-feed']);
});

it('changes each collection requirement independently without losing the other choices', async () => {
  const view = editor();
  for (const label of [
    'Allow fresh web search',
    'Require primary sources',
    'Require local sources',
    'Require opposing evidence',
  ]) {
    await view.user.click(screen.getByLabelText(label));
    expect(screen.getByLabelText(label)).toBeChecked();
  }
  expect(view.draft().collection).toMatchObject({
    web_search: true,
    require_primary: true,
    require_local: true,
    require_opposition: true,
  });
  await view.user.click(screen.getByLabelText('Allow fresh web search'));
  expect(view.draft().collection).toMatchObject({ web_search: false, require_primary: true });
  expect(
    screen.getByText(/Private inputs retain their separate disclosure permissions/),
  ).toBeVisible();
});

it('supports optional numeric limits with browser bounds and nullable novelty preference', async () => {
  const view = editor();
  for (const [key, label, maximum] of [
    ['max_passes', 'Maximum passes', 2],
    ['max_external_operations', 'Maximum external operations', 32],
    ['max_model_calls', 'Maximum model calls', 24],
    ['max_output_tokens', 'Maximum output tokens', 256000],
    ['max_collection_seconds', 'Maximum collection seconds', 240],
  ] as const) {
    const field = screen.getByLabelText(label);
    expect(field).toHaveValue(null);
    fireEvent.change(field, { target: { value: String(maximum + 1) } });
    expect(field).toBeInvalid();
    fireEvent.change(field, { target: { value: String(maximum) } });
    expect(field).toBeValid();
    expect(view.draft().limits[key]).toBe(maximum);
    await view.user.clear(field);
    expect(view.draft().limits[key]).toBeNull();
  }
  const novelty = screen.getByLabelText('Prefer novel evidence');
  await view.user.selectOptions(novelty, 'true');
  expect(view.draft().monitoring.prefer_novelty).toBe(true);
  await view.user.selectOptions(novelty, 'false');
  expect(view.draft().monitoring.prefer_novelty).toBe(false);
  await view.user.selectOptions(novelty, '');
  expect(view.draft().monitoring.prefer_novelty).toBeNull();
});

it('edits and removes one monitoring indicator while preserving its neighbour and review conditions', async () => {
  const draft = newBriefDraft();
  draft.monitoring.indicators = [
    { id: 'first', condition: 'Original condition' },
    { id: 'second', condition: 'Keep this condition' },
  ];
  const view = editor(draft);
  await view.user.clear(screen.getByLabelText('Indicator 1 ID'));
  await view.user.type(screen.getByLabelText('Indicator 1 ID'), 'reviewed');
  await view.user.clear(screen.getByLabelText('Indicator 1 condition'));
  await view.user.type(screen.getByLabelText('Indicator 1 condition'), 'Traffic falls');
  await view.user.type(
    screen.getByLabelText('Review conditions, one per line'),
    'New evidence\nWeekly',
  );
  expect(view.draft().monitoring.indicators).toEqual([
    { id: 'reviewed', condition: 'Traffic falls' },
    { id: 'second', condition: 'Keep this condition' },
  ]);
  await view.user.click(screen.getByRole('button', { name: 'Remove indicator 1' }));
  expect(view.draft().monitoring.indicators).toEqual([
    { id: 'second', condition: 'Keep this condition' },
  ]);
  await view.user.click(screen.getByRole('button', { name: 'Add indicator' }));
  expect(view.draft().monitoring.indicators[1]).toEqual({ id: 'indicator-2', condition: '' });
  expect(view.draft().monitoring.review_conditions).toEqual(['New evidence', 'Weekly']);
});

it('does not add a thirteenth monitoring indicator', async () => {
  const draft = newBriefDraft();
  draft.monitoring.indicators = Array.from({ length: 12 }, (_, index) => ({
    id: `condition-${index + 1}`,
    condition: 'Review when evidence changes',
  }));
  const view = editor(draft);
  const add = screen.getByRole('button', { name: 'Add indicator' });
  expect(add).toBeDisabled();
  await view.user.click(add);
  expect(view.draft().monitoring.indicators).toHaveLength(12);
});

it.each(['query_variants', 'candidate_hypotheses', 'planned_tasks', 'private_inputs'] as const)(
  'discloses pinned %s without modifying them while editing collection options',
  async (kind) => {
    const draft = newBriefDraft();
    if (kind === 'private_inputs') {
      draft.private_inputs = [
        {
          kind: 'session',
          input_id: null,
          report_id: null,
          report_version: null,
          expires_at: null,
          disclose_to_provider: false,
        },
      ];
    } else {
      draft.collection[kind] = [{ id: 'pinned-reference' }];
    }
    const original = structuredClone(draft);
    const view = editor(draft);
    expect(screen.getByText(/remain pinned to this revision/)).toBeVisible();
    await view.user.click(screen.getByLabelText('Require primary sources'));
    expect(view.draft().private_inputs).toEqual(original.private_inputs);
    for (const field of ['query_variants', 'candidate_hypotheses', 'planned_tasks'] as const) {
      expect(view.draft().collection[field]).toEqual(original.collection[field]);
    }
  },
);

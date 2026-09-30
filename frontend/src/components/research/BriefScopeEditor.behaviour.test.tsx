import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it } from 'vitest';

import type { BriefDraft } from '@/lib/api/researchBriefSchema';
import { newBriefDraft, validateBriefDraft } from '@/lib/researchBriefDraft';

import { BriefScopeEditor } from './BriefScopeEditor';

function editor(initial: BriefDraft = newBriefDraft()) {
  let current = initial;
  function Harness() {
    const [draft, setDraft] = useState(initial);
    return (
      <BriefScopeEditor
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

it('normalises country codes and clears geographical filters when selecting a named subject focus', async () => {
  const view = editor();
  await view.user.type(screen.getByLabelText('Country codes, comma separated'), 'gb, fr');
  expect(view.draft().scope.country_isos).toEqual(['GB', 'FR']);
  await view.user.type(screen.getByLabelText('Research subject'), 'Example company');
  await view.user.selectOptions(screen.getByLabelText('Research focus'), 'company');
  expect(view.draft().scope).toMatchObject({
    focus: 'company',
    country_isos: [],
    subject: 'Example company',
  });
  expect(screen.getByLabelText('Country codes, comma separated')).toBeDisabled();
  expect(
    screen.queryByText('Optional named subject or required preset input.'),
  ).not.toBeInTheDocument();
  await view.user.selectOptions(screen.getByLabelText('Research focus'), 'general');
  expect(view.draft().scope.country_isos).toEqual([]);
  expect(screen.getByLabelText('Country codes, comma separated')).toBeEnabled();
  await view.user.clear(screen.getByLabelText('Research subject'));
  expect(view.draft().scope.subject).toBeNull();
});

it('edits and clears optional scope filters while preserving aliases and unrelated draft content', async () => {
  const view = editor();
  await view.user.click(screen.getByText('Additional scope filters'));
  for (const [label, key, value] of [
    ['Conflict ID', 'conflict_id', 'conflict-123'],
    ['Hazard', 'hazard', 'wildfire'],
    ['Collection plan ID', 'plan_id', '11111111-1111-4111-8111-111111111111'],
  ] as const) {
    const field = screen.getByLabelText(label);
    await view.user.type(field, value);
    expect(view.draft().scope[key]).toBe(value);
    await view.user.clear(field);
    expect(view.draft().scope[key]).toBeNull();
  }
  await view.user.type(screen.getByLabelText('Event categories, comma separated'), 'news, cyber');
  await view.user.type(
    screen.getByLabelText('Reviewed aliases, one per line'),
    'Alias one\nAlias two',
  );
  expect(view.draft().scope.categories).toEqual(['news', 'cyber']);
  expect(view.draft().scope.reviewed_aliases).toEqual(['Alias one', 'Alias two']);
  expect(view.draft().collection).toEqual(newBriefDraft().collection);
});

it('keeps UTC observation dates separate from the forecast horizon and resets dates on policy changes', async () => {
  const draft = newBriefDraft();
  draft.title = 'Port review';
  draft.question.main = 'What changed at the port?';
  draft.observation.lookback_hours = null;
  const view = editor(draft);
  expect(screen.getByLabelText('Lookback hours')).toHaveValue(null);
  fireEvent.change(screen.getByLabelText('Lookback hours'), { target: { value: '72' } });
  expect(view.draft().observation.lookback_hours).toBe(72);
  await view.user.selectOptions(screen.getByLabelText('Observation period'), 'explicit');
  expect(screen.queryByLabelText('Lookback hours')).not.toBeInTheDocument();
  const start = screen.getByLabelText('Observation start (UTC)');
  const end = screen.getByLabelText('Observation end (UTC)');
  expect(start).toHaveValue('');
  expect(end).toHaveValue('');
  fireEvent.change(start, { target: { value: '2026-09-01T09:30' } });
  fireEvent.change(end, { target: { value: '2026-09-02T16:45' } });
  const period = { since: '2026-09-01T09:30:00.000Z', until: '2026-09-02T16:45:00.000Z' };
  expect(view.draft().observation).toMatchObject(period);
  fireEvent.change(screen.getByLabelText('Forecast horizon in days (optional)'), {
    target: { value: '7' },
  });
  expect(view.draft().observation).toMatchObject({ ...period, forecast_horizon_days: 7 });
  await view.user.selectOptions(screen.getByLabelText('Evidence date basis'), 'recorded_time');
  expect(view.draft().observation.time_basis).toBe('recorded_time');
  expect(validateBriefDraft(view.draft())).toBeNull();
  fireEvent.change(end, { target: { value: '' } });
  expect(view.draft().observation.until).toBeNull();
  expect(validateBriefDraft(view.draft())).toBe(
    'Choose a positive exact UTC observation interval.',
  );
  await view.user.selectOptions(screen.getByLabelText('Evidence date basis'), '');
  await view.user.clear(screen.getByLabelText('Forecast horizon in days (optional)'));
  expect(view.draft().observation).toMatchObject({ time_basis: null, forecast_horizon_days: null });
  await view.user.selectOptions(screen.getByLabelText('Observation period'), 'template_default');
  expect(view.draft().observation).toMatchObject({
    since: null,
    until: null,
    lookback_hours: null,
  });
  expect(screen.queryByLabelText('Observation start (UTC)')).not.toBeInTheDocument();
  await view.user.selectOptions(screen.getByLabelText('Observation period'), 'relative');
  expect(view.draft().observation.lookback_hours).toBe(24);
});

it.each(['area', 'map_origin', 'map_view_id'] as const)(
  'keeps pinned %s immutable and requires a separate area disclosure choice',
  async (kind) => {
    const draft = newBriefDraft();
    if (kind === 'map_view_id') {
      draft.scope.map_view_id = '11111111-1111-4111-8111-111111111111';
      draft.scope.map_revision_id = '22222222-2222-4222-8222-222222222222';
    } else {
      draft.scope[kind] = { source: 'saved-review', sha256: 'a'.repeat(64) };
    }
    const original = structuredClone(draft.scope);
    const view = editor(draft);
    expect(screen.getByLabelText('Country codes, comma separated')).toBeDisabled();
    expect(screen.getByLabelText('Research focus')).toBeDisabled();
    expect(screen.queryByText('Additional scope filters')).not.toBeInTheDocument();
    if (kind === 'map_view_id')
      expect(screen.getByText(/Exact saved map revision pinned/)).toBeVisible();
    else expect(screen.getByText('Exact saved polygon is pinned to this brief.')).toBeVisible();
    const disclosure = screen.getByLabelText(
      'Permit area and period disclosure to selected providers',
    );
    expect(disclosure).not.toBeChecked();
    await view.user.click(disclosure);
    expect(view.draft().scope).toEqual({ ...original, disclose_area_to_provider: true });
    await view.user.click(disclosure);
    expect(view.draft().scope).toEqual(original);
  },
);

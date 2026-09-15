import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import * as briefs from '@/lib/api/researchBriefs';
import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';

import { BriefEditor } from './BriefEditor';

function draft(): BriefDraft {
  return {
    ...newBriefDraft(),
    title: 'Port watch',
    question: {
      main: 'What changed at the port?',
      requirements: [],
      exclusions: [],
    },
  };
}
function saved(value: BriefDraft): ResearchBrief {
  return {
    ...value,
    identity: {
      id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
      revision: 1,
      owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
      team_id: null,
      title: value.title,
      created_at: '2026-09-14T10:00:00Z',
      revised_at: '2026-09-14T10:00:00Z',
      preset_id: null,
      preset_version: null,
      schema_version: 1,
      origin: 'authored',
      published: false,
    },
  };
}
function editor(value = draft()) {
  const onSaved = vi.fn();
  const view = render(
    <MemoryRouter>
      <BriefEditor
        initial={{ draft: value, brief: null, copy: false, mapTitle: null }}
        onSaved={onSaved}
      />
    </MemoryRouter>,
  );
  return { ...view, onSaved, user: userEvent.setup() };
}

it('preserves typed scope, languages, dates and requirements through all four stages', async () => {
  const create = vi
    .spyOn(briefs, 'createBrief')
    .mockImplementation((value) => Promise.resolve(saved(value)));
  const { user, onSaved } = editor();
  await user.click(screen.getByRole('button', { name: 'Add requirement' }));
  await user.type(screen.getByLabelText('Requirement 1 question'), 'Has throughput changed?');
  await user.type(
    screen.getByLabelText('Excluded questions or claims, one per line'),
    'Rumours{Enter}Forecast claims',
  );
  await user.click(screen.getByRole('button', { name: 'Continue to Scope' }));
  expect(screen.getByRole('heading', { name: 'Scope and perspective' })).toHaveFocus();
  expect(screen.getByLabelText('Main research question')).not.toBeVisible();
  await user.type(screen.getByLabelText('Country codes, comma separated'), 'gb,fr');
  await user.selectOptions(screen.getByLabelText('Observation period'), 'explicit');
  fireEvent.change(screen.getByLabelText('Observation start (UTC)'), {
    target: { value: '2026-09-01T00:00' },
  });
  fireEvent.change(screen.getByLabelText('Observation end (UTC)'), {
    target: { value: '2026-09-14T00:00' },
  });
  await user.type(screen.getByLabelText('Forecast horizon in days (optional)'), '30');
  await user.type(screen.getByLabelText('Audience'), 'Port operators');
  await user.type(screen.getByLabelText('Collection languages, comma separated'), ',fr');
  await user.click(screen.getByRole('button', { name: 'Continue to Depth' }));
  await user.click(screen.getByRole('radio', { name: /^Deep/ }));
  await user.click(screen.getByRole('button', { name: 'Continue to Run' }));
  const summary = within(screen.getByRole('region', { name: 'Brief run summary' }));
  expect(summary.getByText('GB, FR')).toBeVisible();
  expect(summary.getByText(/30 days forward, separate from observed evidence/)).toBeVisible();
  expect(summary.getByText('Report: en; collection: en, fr')).toBeVisible();
  expect(create).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Back' }));
  expect(screen.getByRole('radio', { name: /^Deep/ })).toBeChecked();
  await user.click(screen.getByRole('button', { name: 'Back' }));
  expect(screen.getByLabelText('Audience')).toHaveValue('Port operators');
  expect(screen.getByLabelText('Observation end (UTC)')).toHaveValue('2026-09-14T00:00');
  await user.click(screen.getByRole('button', { name: '1 Brief' }));
  expect(screen.getByLabelText('Requirement 1 question')).toHaveValue('Has throughput changed?');
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(create.mock.calls[0]?.[0]).toMatchObject({
    question: { exclusions: ['Rumours', 'Forecast claims'] },
    scope: { country_isos: ['GB', 'FR'] },
    observation: {
      since: '2026-09-01T00:00:00.000Z',
      until: '2026-09-14T00:00:00.000Z',
      forecast_horizon_days: 30,
    },
    collection: { languages: ['en', 'fr'] },
    output: { depth: 'detailed' },
  });
  expect(screen.getByRole('button', { name: 'Run once' })).toBeEnabled();
});

it('supports keyboard stage navigation and puts focus on the newly visible heading', async () => {
  const { user } = editor();
  const nav = within(screen.getByRole('navigation', { name: 'Research stages' }));
  expect(nav.getByRole('button', { name: '1 Brief' })).toHaveAttribute('aria-current', 'step');
  nav.getByRole('button', { name: '2 Scope' }).focus();
  await user.keyboard('{Enter}');
  expect(screen.getByRole('heading', { name: 'Scope and perspective' })).toHaveFocus();
  expect(nav.getByRole('button', { name: '2 Scope' })).toHaveAttribute('aria-current', 'step');
  expect(nav.getByRole('button', { name: '1 Brief' })).not.toHaveAttribute('aria-current');
  expect(screen.getByLabelText('Brief title')).not.toBeVisible();
  await user.tab();
  expect(screen.getByLabelText('Country codes, comma separated')).toHaveFocus();
});

it('opens hidden invalid fields, focuses the error summary and offers a working field link', async () => {
  const create = vi.spyOn(briefs, 'createBrief');
  const { user } = editor({ ...draft(), title: '' });
  await user.click(screen.getByRole('button', { name: '4 Run' }));
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(screen.getByRole('alert').parentElement).toHaveFocus();
  expect(screen.getByRole('heading', { name: 'Define your brief' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Review field' }));
  expect(screen.getByLabelText('Brief title')).toHaveFocus();
  await user.click(screen.getByRole('button', { name: '4 Run' }));
  await user.click(screen.getByRole('button', { name: 'Review field' }));
  expect(screen.getByLabelText('Brief title')).toHaveFocus();
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(screen.getByRole('alert').parentElement).toHaveFocus();
  expect(create).not.toHaveBeenCalled();
});

it('finds an out-of-range advanced limit before dispatch and retains the corrected value', async () => {
  const value = draft();
  value.limits.max_external_operations = 33;
  const create = vi
    .spyOn(briefs, 'createBrief')
    .mockImplementation((next) => Promise.resolve(saved(next)));
  const { user } = editor(value);
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(screen.getByRole('heading', { name: 'Depth and coverage' })).toBeVisible();
  expect(screen.getByText(/Maximum external operations: use a maximum of 32/)).toBeVisible();
  const input = screen.getByLabelText('Maximum external operations');
  expect(input).toBeVisible();
  expect(create).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Review field' }));
  expect(input).toHaveFocus();
  await user.clear(input);
  await user.type(input, '6');
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(create.mock.calls[0]?.[0].limits.max_external_operations).toBe(6);
});

it('does not silently remove questions when a shallower depth cannot hold them', async () => {
  const value = draft();
  value.output.depth = 'detailed';
  value.question.requirements = Array.from({ length: 4 }, (_, i) => ({
    id: `question-${i + 1}`,
    question: `What changed in area ${i + 1}?`,
    required: true,
    priority: i + 1,
  }));
  const create = vi.spyOn(briefs, 'createBrief');
  const { user } = editor(value);
  await user.click(screen.getByRole('button', { name: '3 Depth' }));
  await user.click(screen.getByRole('radio', { name: /^Basic/ }));
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(screen.getByText('This depth allows at most 3 required questions.')).toBeVisible();
  expect(screen.getByRole('alert').parentElement).toHaveFocus();
  await user.click(screen.getByRole('button', { name: '1 Brief' }));
  expect(screen.getAllByLabelText(/Requirement \d question/)).toHaveLength(4);
  expect(create).not.toHaveBeenCalled();
});

it('shows saved offset timestamps as UTC without changing their original instants', async () => {
  const value = draft();
  value.observation = {
    ...value.observation,
    policy: 'explicit',
    lookback_hours: null,
    since: '2026-09-01T03:00:00+03:00',
    until: '2026-09-14T03:00:00+03:00',
  };
  const create = vi
    .spyOn(briefs, 'createBrief')
    .mockImplementation((next) => Promise.resolve(saved(next)));
  const { user } = editor(value);
  await user.click(screen.getByRole('button', { name: '2 Scope' }));
  expect(screen.getByLabelText('Observation start (UTC)')).toHaveValue('2026-09-01T00:00');
  expect(screen.getByLabelText('Observation end (UTC)')).toHaveValue('2026-09-14T00:00');
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(create).toHaveBeenCalledOnce());
  expect(create.mock.calls[0]?.[0].observation).toEqual(value.observation);
});

it('shows the stage for the reported semantic error when another hidden field is also invalid', async () => {
  const value = draft();
  value.observation.policy = 'explicit';
  value.observation.lookback_hours = null;
  value.limits.max_external_operations = 33;
  const create = vi.spyOn(briefs, 'createBrief');
  const { user } = editor(value);
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(screen.getByText('Choose a positive exact UTC observation interval.')).toBeVisible();
  expect(screen.getByRole('heading', { name: 'Scope and perspective' })).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Review field' }));
  expect(screen.getByRole('heading', { name: 'Scope and perspective' })).toHaveFocus();
  expect(create).not.toHaveBeenCalled();
});

it('keeps values and gives focus to a recoverable server error', async () => {
  vi.spyOn(briefs, 'createBrief').mockRejectedValue(
    new ApiError(409, 'conflict', 'Review the newer revision before saving.'),
  );
  const { user } = editor();
  await user.type(screen.getByLabelText('Brief title'), ' revised');
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(await screen.findByText('Review the newer revision before saving.')).toBeVisible();
  expect(screen.getByRole('alert').parentElement).toHaveFocus();
  expect(screen.getByLabelText('Brief title')).toHaveValue('Port watch revised');
  expect(screen.getByRole('button', { name: 'Save brief' })).toBeEnabled();
});

it('aborts a pending save on leaving and ignores a late successful response', async () => {
  let finish!: (result: ResearchBrief) => void;
  const create = vi.spyOn(briefs, 'createBrief').mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { user, unmount, onSaved } = editor();
  await user.dblClick(screen.getByRole('button', { name: 'Save brief' }));
  expect(create).toHaveBeenCalledOnce();
  expect(screen.getByLabelText('Brief title')).toBeDisabled();
  expect(screen.getByRole('button', { name: '2 Scope' })).toBeDisabled();
  const signal = create.mock.calls[0]?.[1];
  unmount();
  expect(signal?.aborted).toBe(true);
  await act(async () => {
    finish(saved(draft()));
    await Promise.resolve();
  });
  expect(onSaved).not.toHaveBeenCalled();
});

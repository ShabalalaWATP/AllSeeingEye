import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';

import * as briefs from '@/lib/api/researchBriefs';
import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';

import { BriefEditor } from './BriefEditor';

function saved(draft: BriefDraft): ResearchBrief {
  return {
    ...draft,
    identity: {
      id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
      revision: 1,
      owner_id: 'd2e73f24-a73a-4ee7-b478-f175a05ba96d',
      team_id: null,
      title: draft.title,
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

async function editor(indicators: BriefDraft['monitoring']['indicators'] = []) {
  const draft = newBriefDraft();
  draft.title = 'Port watch';
  draft.question.main = 'What changed at the port?';
  draft.monitoring.indicators = indicators;
  const create = vi
    .spyOn(briefs, 'createBrief')
    .mockImplementation((value) => Promise.resolve(saved(value)));
  const onSaved = vi.fn();
  render(
    <MemoryRouter>
      <BriefEditor
        initial={{ draft, brief: null, copy: false, mapTitle: null }}
        onSaved={onSaved}
      />
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: '3 Depth' }));
  await user.click(screen.getByText('Advanced sources, limits and monitoring'));
  return { user, create, onSaved };
}

it('saves unique indicator IDs after removing the middle row and adding another', async () => {
  const { user, create, onSaved } = await editor();
  for (let number = 1; number <= 3; number += 1) {
    await user.click(screen.getByRole('button', { name: 'Add indicator' }));
    fireEvent.change(screen.getByLabelText(`Indicator ${number} condition`), {
      target: { value: `Condition ${number}` },
    });
  }
  await user.click(screen.getByRole('button', { name: 'Remove indicator 2' }));
  await user.click(screen.getByRole('button', { name: 'Add indicator' }));
  fireEvent.change(screen.getByLabelText('Indicator 3 condition'), {
    target: { value: 'Replacement condition' },
  });
  expect(screen.getByLabelText('Indicator 1 ID')).toHaveValue('indicator-1');
  expect(screen.getByLabelText('Indicator 2 ID')).toHaveValue('indicator-3');
  expect(screen.getByLabelText('Indicator 3 ID')).toHaveValue('indicator-4');
  await user.click(screen.getByRole('button', { name: '4 Run' }));
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(create).toHaveBeenCalledOnce();
  expect(create.mock.calls[0]?.[0].monitoring.indicators).toEqual([
    { id: 'indicator-1', condition: 'Condition 1' },
    { id: 'indicator-3', condition: 'Condition 3' },
    { id: 'indicator-4', condition: 'Replacement condition' },
  ]);
});

it('skips consecutive occupied IDs without renumbering existing custom IDs', async () => {
  const { user } = await editor([
    { id: 'custom', condition: 'Keep custom condition' },
    { id: 'indicator-4', condition: 'Keep fourth condition' },
    { id: 'indicator-5', condition: 'Keep fifth condition' },
  ]);
  await user.click(screen.getByRole('button', { name: 'Add indicator' }));
  expect(screen.getByLabelText('Indicator 1 ID')).toHaveValue('custom');
  expect(screen.getByLabelText('Indicator 2 ID')).toHaveValue('indicator-4');
  expect(screen.getByLabelText('Indicator 3 ID')).toHaveValue('indicator-5');
  expect(screen.getByLabelText('Indicator 4 ID')).toHaveValue('indicator-6');
});

it('rejects manually duplicated indicator IDs before dispatch and saves their correction', async () => {
  const { user, create, onSaved } = await editor([
    { id: 'traffic', condition: 'Traffic falls' },
    { id: 'delays', condition: 'Delays rise' },
  ]);
  fireEvent.change(screen.getByLabelText('Indicator 2 ID'), { target: { value: 'traffic' } });
  await user.click(screen.getByRole('button', { name: '4 Run' }));
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  expect(create).not.toHaveBeenCalled();
  expect(onSaved).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toHaveTextContent('Indicator IDs must be unique.');
  expect(screen.getByRole('alert').parentElement).toHaveFocus();
  expect(screen.getByRole('heading', { name: 'Depth and coverage' })).toBeVisible();
  expect(screen.getByLabelText('Indicator 2 ID')).toBeVisible();
  fireEvent.change(screen.getByLabelText('Indicator 2 ID'), { target: { value: 'delays' } });
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(create).toHaveBeenCalledOnce();
  expect(create.mock.calls[0]?.[0].monitoring.indicators).toEqual([
    { id: 'traffic', condition: 'Traffic falls' },
    { id: 'delays', condition: 'Delays rise' },
  ]);
});

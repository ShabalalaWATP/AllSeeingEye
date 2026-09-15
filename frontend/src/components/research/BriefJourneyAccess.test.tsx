import { act, fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';

import * as briefs from '@/lib/api/researchBriefs';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import { invalidateWorkspaceAccess } from '@/lib/workspaceAccess';
import { renderApp } from '@/test/render';
import { reportJob } from '@/test/reportJobFixture';

import { BriefEditor } from './BriefEditor';

const value = {
  ...newBriefDraft(),
  title: 'Port watch',
  question: {
    main: 'What changed at the port?',
    requirements: [],
    exclusions: [],
  },
};
const saved: ResearchBrief = {
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

it('discards the visible draft and aborts a pending save when workspace access changes', async () => {
  let finish!: (brief: ResearchBrief) => void;
  const create = vi.spyOn(briefs, 'createBrief').mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { user, router } = renderApp('/research?brief=new', 'user');
  await user.type(await screen.findByLabelText('Brief title'), 'Previous scope draft');
  await user.type(screen.getByLabelText('Main research question'), 'Private local question');
  await user.click(screen.getByRole('button', { name: 'Save brief' }));
  const signal = create.mock.calls[0]?.[1];
  await act(async () => {
    invalidateWorkspaceAccess();
    await Promise.resolve();
  });
  expect(signal?.aborted).toBe(true);
  expect(screen.queryByDisplayValue('Previous scope draft')).not.toBeInTheDocument();
  expect(screen.queryByDisplayValue('Private local question')).not.toBeInTheDocument();
  await act(async () => {
    finish(saved);
    await Promise.resolve();
  });
  expect(router.state.location.search).toBe('?brief=new');
  expect(await screen.findByLabelText('Brief title')).toHaveValue('');
});

it.each(['resolve', 'reject'] as const)(
  'aborts a pending run and ignores a late %s after unmount',
  async (outcome) => {
    let finish!: (job: ReturnType<typeof reportJob>) => void;
    let fail!: (error: Error) => void;
    const run = vi.spyOn(briefs, 'runBrief').mockImplementation(
      () =>
        new Promise((resolve, reject) => {
          finish = resolve;
          fail = reject;
        }),
    );
    const user = userEvent.setup();
    const view = render(
      <MemoryRouter>
        <BriefEditor
          initial={{ draft: value, brief: saved, copy: false, mapTitle: null }}
          initialStep="run"
          onSaved={vi.fn()}
        />
      </MemoryRouter>,
    );
    await user.dblClick(screen.getByRole('button', { name: 'Run once' }));
    expect(run).toHaveBeenCalledOnce();
    expect(run.mock.calls[0]?.[0].identity.revision).toBe(1);
    const signal = run.mock.calls[0]?.[1];
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      if (outcome === 'resolve') finish(reportJob());
      else fail(new Error('Late transport failure'));
      await Promise.resolve();
    });
    expect(screen.queryByText(/Research started from brief/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  },
);

it('keeps subscription timing while moving back through the same unchanged brief', async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <BriefEditor
        initial={{ draft: value, brief: saved, copy: false, mapTitle: null }}
        intent="subscribe"
        onSaved={vi.fn()}
      />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText('Local time'), { target: { value: '09:45' } });
  await user.click(screen.getByRole('button', { name: '1 Brief' }));
  expect(screen.getByLabelText('Local time')).not.toBeVisible();
  await user.click(screen.getByRole('button', { name: '4 Run' }));
  expect(screen.getByLabelText('Local time')).toHaveValue('09:45');
  expect(screen.getByRole('button', { name: 'Create subscription' })).toBeEnabled();
});

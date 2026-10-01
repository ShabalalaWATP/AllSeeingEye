import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import * as briefApi from '@/lib/api/researchBriefs';
import * as subscriptions from '@/lib/api/briefSubscriptions';
import { researchBriefSchema } from '@/lib/api/researchBriefSchema';
import { ApiError } from '@/lib/api/errors';
import { newBriefDraft } from '@/lib/researchBriefDraft';
import { schedule } from '@/test/fixtures.schedules';
import { BriefScheduleCopy } from './BriefScheduleCopy';

const linked = {
  ...schedule,
  brief_id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
  brief_revision: 2,
};
const brief = researchBriefSchema.parse({
  ...newBriefDraft(),
  question: { main: 'What changed at the port?', requirements: [], exclusions: [] },
  identity: {
    id: linked.brief_id,
    revision: 2,
    owner_id: linked.created_by,
    team_id: null,
    title: 'Port watch',
    created_at: linked.created_at,
    revised_at: linked.created_at,
    preset_id: null,
    preset_version: null,
    schema_version: 1,
    origin: 'authored',
    published: false,
  },
});
const fetchBrief = vi.fn<typeof briefApi.fetchBrief>();
const createCopy = vi.fn<typeof subscriptions.createBriefSubscription>();
const created = { ...linked, enabled: false };

beforeEach(() => {
  fetchBrief.mockReset().mockResolvedValue(brief);
  createCopy.mockReset().mockResolvedValue(created);
  vi.spyOn(briefApi, 'fetchBrief').mockImplementation(fetchBrief);
  vi.spyOn(subscriptions, 'createBriefSubscription').mockImplementation(createCopy);
});

function mount(source = linked) {
  const onCancel = vi.fn();
  const onCreated = vi.fn();
  return {
    ...render(<BriefScheduleCopy source={source} onCancel={onCancel} onCreated={onCreated} />),
    onCancel,
    onCreated,
  };
}

it.each([{ brief_id: '' }, { brief_revision: 0 }])(
  'refuses a missing pinned brief reference and allows cancellation: %j',
  (missing) => {
    const { onCancel } = mount({ ...linked, ...missing });
    expect(screen.getByRole('alert')).toHaveTextContent(
      'linked Research Brief revision is missing',
    );
    expect(fetchBrief).not.toHaveBeenCalled();
    expect(createCopy).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledOnce();
  },
);

it('retries loading the same exact revision and applies legacy recurrence defaults to a paused copy', async () => {
  fetchBrief.mockRejectedValueOnce(
    new ApiError(503, 'unavailable', 'Brief temporarily unavailable.'),
  );
  const { onCreated } = mount();
  expect(await screen.findByRole('alert')).toHaveTextContent('Brief temporarily unavailable.');
  fireEvent.click(screen.getByRole('button', { name: 'Retry brief' }));
  await screen.findByRole('form', { name: 'Duplicate Research Brief subscription' });
  expect(fetchBrief).toHaveBeenCalledTimes(2);
  for (const [id, revision] of fetchBrief.mock.calls)
    expect([id, revision]).toEqual([linked.brief_id, 2]);
  expect(screen.getByLabelText('IANA timezone')).toHaveValue('UTC');
  expect(screen.getByLabelText('Local time')).toHaveValue('06:00');
  fireEvent.click(screen.getByRole('button', { name: 'Create paused copy' }));
  await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
  expect(createCopy).toHaveBeenCalledWith(
    brief,
    expect.objectContaining({
      name: 'Copy of Morning INTSUM',
      timezone: 'UTC',
      local_hour: 6,
      local_minute: 0,
      collection_policy: 'rolling_snapshot',
      enabled: false,
    }),
    expect.any(AbortSignal),
  );
});

it('refuses invalid saved recurrence settings after loading the referenced brief', async () => {
  const { onCancel } = mount({ ...linked, hour_utc: 99 });
  expect(await screen.findByRole('alert')).toHaveTextContent('invalid recurrence settings');
  expect(screen.queryByRole('form')).not.toBeInTheDocument();
  expect(createCopy).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(onCancel).toHaveBeenCalledOnce();
});

it.each([{ brief_id: 'different-brief' }, { brief_revision: 3 }, { enabled: true }])(
  'blocks another submission after an unverified copy response: %j',
  async (mismatch) => {
    createCopy.mockResolvedValueOnce({ ...created, ...mismatch });
    const { onCreated } = mount();
    const form = await screen.findByRole('form', { name: 'Duplicate Research Brief subscription' });
    const button = screen.getByRole('button', { name: 'Create paused copy' });
    button.focus();
    fireEvent.submit(form);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'did not retain the exact brief revision and paused state',
    );
    expect(onCreated).not.toHaveBeenCalled();
    expect(button).toHaveAttribute('aria-disabled', 'true');
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveFocus();
    fireEvent.click(button);
    fireEvent.submit(form);
    expect(createCopy).toHaveBeenCalledOnce();
  },
);

it('allows a known failed create to be retried without enabling the copy', async () => {
  createCopy.mockRejectedValueOnce(
    new ApiError(403, 'forbidden', 'Current workspace access is required.'),
  );
  const { onCreated } = mount();
  const button = await screen.findByRole('button', { name: 'Create paused copy' });
  fireEvent.click(button);
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Current workspace access is required.',
  );
  expect(button).toBeEnabled();
  expect(onCreated).not.toHaveBeenCalled();
  fireEvent.click(button);
  await waitFor(() => expect(onCreated).toHaveBeenCalledOnce());
  expect(createCopy).toHaveBeenCalledTimes(2);
  expect(createCopy.mock.calls.every(([, settings]) => !settings.enabled)).toBe(true);
});

it('aborts a revision request on unmount without showing its eventual cancellation error', async () => {
  let reject!: (reason: Error) => void;
  fetchBrief.mockReturnValueOnce(
    new Promise((_, no) => {
      reject = no;
    }),
  );
  const { unmount, onCreated } = mount();
  expect(screen.getByText('Loading the exact Research Brief revision')).toBeVisible();
  const signal = fetchBrief.mock.calls[0]![2];
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    reject(new DOMException('Aborted', 'AbortError'));
    await Promise.resolve();
  });
  expect(onCreated).not.toHaveBeenCalled();
});

it('aborts an outstanding copy on unmount and never announces its cancellation as a success', async () => {
  let reject!: (reason: Error) => void;
  createCopy.mockReturnValueOnce(
    new Promise((_, no) => {
      reject = no;
    }),
  );
  const { unmount, onCreated } = mount();
  const button = await screen.findByRole('button', { name: 'Create paused copy' });
  button.focus();
  fireEvent.click(button);
  const signal = createCopy.mock.calls[0]![2];
  expect(button).toHaveAttribute('aria-disabled', 'true');
  expect(button).toHaveAttribute('aria-busy', 'true');
  expect(button).toHaveFocus();
  fireEvent.click(button);
  expect(createCopy).toHaveBeenCalledOnce();
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    reject(new DOMException('Aborted', 'AbortError'));
    await Promise.resolve();
  });
  expect(onCreated).not.toHaveBeenCalled();
});

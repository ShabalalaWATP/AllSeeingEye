import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import axe from 'axe-core';
import { beforeEach, expect, it, vi } from 'vitest';

import * as api from '@/lib/api/briefSubscriptions';
import { ApiError } from '@/lib/api/errors';
import type { Schedule } from '@/lib/api/schedules';
import { schedule } from '@/test/fixtures.schedules';
import { BriefScheduleEdit } from './BriefScheduleEdit';

const source = {
  ...schedule,
  brief_id: 'd73c2988-d2ca-4482-9e39-7269e876eaa0',
  brief_revision: 2,
  settings_revision: 'a'.repeat(64),
  timezone: 'Europe/London',
  local_hour: 9,
  local_minute: 30,
  cadence: 'weekly',
  enabled: false,
};
const update = vi.fn<typeof api.updateBriefSubscriptionSettings>();
beforeEach(() => {
  update.mockReset().mockResolvedValue(source);
  vi.spyOn(api, 'updateBriefSubscriptionSettings').mockImplementation(update);
});
function mount(item: Schedule = source) {
  const onCancel = vi.fn();
  const onSaved = vi.fn();
  return {
    ...render(<BriefScheduleEdit source={item} onCancel={onCancel} onSaved={onSaved} />),
    onCancel,
    onSaved,
  };
}

it('refuses a missing settings revision and permits cancellation', () => {
  const { settings_revision: _revision, ...legacy } = source;
  const { onCancel } = mount(legacy);
  expect(screen.getByRole('alert')).toHaveTextContent('Reload subscriptions');
  fireEvent.submit(screen.getByRole('form'));
  expect(update).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(onCancel).toHaveBeenCalledOnce();
});

it.each([
  ['Subscription name', '   ', 'Enter a subscription name.'],
  ['IANA timezone', 'Invalid/Zone', 'Check the timezone'],
  ['Local time', '', 'Check the timezone'],
])('validates %s before submitting', (label, value, message) => {
  mount();
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.submit(screen.getByRole('form'));
  expect(screen.getByRole('alert')).toHaveTextContent(message);
  expect(update).not.toHaveBeenCalled();
});

it('retains the original revision during list refresh and sends calendar settings only', async () => {
  const { rerender, onCancel, onSaved } = mount();
  rerender(
    <BriefScheduleEdit
      source={{ ...source, settings_revision: 'b'.repeat(64), enabled: true }}
      onCancel={onCancel}
      onSaved={onSaved}
    />,
  );
  fireEvent.change(screen.getByLabelText('Cadence'), { target: { value: 'quarterly' } });
  fireEvent.change(screen.getByLabelText('Day of month'), { target: { value: '31' } });
  fireEvent.change(screen.getByLabelText('Starting month'), { target: { value: '2' } });
  fireEvent.submit(screen.getByRole('form'));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(update).toHaveBeenCalledWith(
    source.id,
    {
      expected_revision: 'a'.repeat(64),
      name: source.name,
      cadence: 'quarterly',
      monthday: 31,
      anchor_month: 2,
      weekday: source.weekday,
      timezone: 'Europe/London',
      local_hour: 9,
      local_minute: 30,
    },
    expect.any(AbortSignal),
  );
});

it('shows field errors and preserves input for a corrected retry', async () => {
  update.mockRejectedValueOnce(
    new ApiError(422, 'invalid_request', 'Invalid recurrence.', {
      timezone: 'Choose a valid IANA timezone.',
    }),
  );
  const { onSaved } = mount();
  fireEvent.submit(screen.getByRole('form'));
  await waitFor(() =>
    expect(screen.getByLabelText('IANA timezone')).toHaveAttribute('aria-invalid', 'true'),
  );
  expect(screen.getByLabelText('IANA timezone')).toHaveValue('Europe/London');
  fireEvent.change(screen.getByLabelText('IANA timezone'), { target: { value: 'UTC' } });
  fireEvent.submit(screen.getByRole('form'));
  await waitFor(() => expect(onSaved).toHaveBeenCalledOnce());
  expect(update).toHaveBeenCalledTimes(2);
});

it('aborts on unmount and ignores a late success', async () => {
  let finish:
    ((value: Awaited<ReturnType<typeof api.updateBriefSubscriptionSettings>>) => void) | undefined;
  update.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const { unmount, onSaved } = mount();
  fireEvent.submit(screen.getByRole('form'));
  fireEvent.submit(screen.getByRole('form'));
  expect(update).toHaveBeenCalledOnce();
  const signal = update.mock.calls[0]![2];
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    finish?.(source);
    await Promise.resolve();
  });
  expect(onSaved).not.toHaveBeenCalled();
});

it('uses labelled keyboard controls without detectable structural accessibility violations', async () => {
  const { container } = mount();
  expect(screen.getByLabelText('Subscription name')).toHaveFocus();
  const result = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } });
  expect(result.violations).toEqual([]);
});

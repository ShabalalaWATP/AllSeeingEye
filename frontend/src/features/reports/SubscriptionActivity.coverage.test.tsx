import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';

import * as controls from '@/lib/api/subscriptionControls';
import { ApiError } from '@/lib/api/errors';
import { SubscriptionActivity } from './SubscriptionActivity';

type Page = Awaited<ReturnType<typeof controls.fetchSubscriptionEvents>>;
const empty: Page = { items: [], limit: 10, offset: 0 };
const fetchEvents = vi.fn<typeof controls.fetchSubscriptionEvents>();
beforeEach(() => {
  fetchEvents.mockReset().mockResolvedValue(empty);
  vi.spyOn(controls, 'fetchSubscriptionEvents').mockImplementation(fetchEvents);
});

function deferred() {
  let resolve!: (page: Page) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<Page>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, resolve, reject };
}

it('recovers an error on retry and reopens cached activity without another request', async () => {
  fetchEvents.mockRejectedValueOnce(
    new ApiError(503, 'unavailable', 'Activity temporarily unavailable.'),
  );
  render(<SubscriptionActivity subscriptionId="subscription-1" />);
  expect(fetchEvents).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Activity' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Activity temporarily unavailable.');
  fetchEvents.mockResolvedValueOnce({
    ...empty,
    items: ['material_change', 'other_update'].map((event_kind, index) => ({
      id: `event-${index}`,
      edition_id: 'edition-1',
      event_kind,
      created_at: '2026-09-30T10:00:00Z',
    })),
  });
  fireEvent.click(screen.getByRole('button', { name: 'Retry activity' }));
  expect(await screen.findByText('Material change identified')).toBeVisible();
  expect(screen.getByText('Subscription update')).toBeVisible();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Activity' }));
  expect(screen.queryByRole('list')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Activity' }));
  expect(screen.getByRole('list', { name: 'Subscription activity' })).toBeVisible();
  expect(fetchEvents).toHaveBeenCalledTimes(2);
});

it.each(['success', 'failure'] as const)(
  'ignores an aborted %s while a newer activity request is still loading',
  async (outcome) => {
    const first = deferred();
    const second = deferred();
    fetchEvents.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    render(<SubscriptionActivity subscriptionId="subscription-1" />);
    const toggle = screen.getByRole('button', { name: 'Activity' });
    fireEvent.click(toggle);
    const oldSignal = fetchEvents.mock.calls[0]![1]!;
    fireEvent.click(toggle);
    expect(oldSignal.aborted).toBe(true);
    fireEvent.click(toggle);
    await act(async () => {
      if (outcome === 'success') first.resolve(empty);
      else first.reject(new Error('Old request failed'));
      await Promise.resolve();
    });
    expect(screen.getByText('Loading subscription activity')).toBeVisible();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText('No change alerts yet.')).not.toBeInTheDocument();
    await act(async () => {
      second.resolve(empty);
      await Promise.resolve();
    });
    expect(screen.getByText('No change alerts yet.')).toBeVisible();
    expect(screen.queryByText('Loading subscription activity')).not.toBeInTheDocument();
  },
);

it('aborts an outstanding activity request when its subscription view unmounts', async () => {
  const request = deferred();
  fetchEvents.mockReturnValueOnce(request.promise);
  const { unmount } = render(<SubscriptionActivity subscriptionId="subscription-1" />);
  fireEvent.click(screen.getByRole('button', { name: 'Activity' }));
  const signal = fetchEvents.mock.calls[0]![1]!;
  unmount();
  expect(signal.aborted).toBe(true);
  await act(async () => {
    request.reject(new DOMException('Aborted', 'AbortError'));
    await Promise.resolve();
  });
});

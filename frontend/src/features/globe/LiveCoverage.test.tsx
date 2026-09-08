import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { LiveCoverage } from './LiveCoverage';

it('distinguishes loaded, filtered and capped snapshot coverage and offers a resync', async () => {
  useEventsStore.getState().reset();
  useEventsStore.getState().applyUpsert([liveEvent(), liveEvent({ id: 'another' })]);
  useEventsStore.setState({ snapshotCount: 2000, snapshotLimited: true, mirrorCapped: true });
  const load = vi.spyOn(useEventsStore.getState(), 'load').mockResolvedValue();
  render(<LiveCoverage filteredCount={1} />);
  expect(
    screen.getByText('2 loaded in this browser; 1 in the selected country and time window.'),
  ).toBeVisible();
  expect(screen.getByText('Snapshot limit 2,000; browser limit 5,000.')).toBeVisible();
  expect(screen.getByText('Last snapshot: 2,000 records. Partial feed coverage.')).toBeVisible();
  expect(screen.getByText(/ship positions receive reserved capacity/)).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Reload live events' }));
  expect(load).toHaveBeenCalledOnce();
  act(() => useEventsStore.setState({ loading: true }));
  expect(screen.getByRole('button', { name: 'Synchronising events...' })).toBeDisabled();
});

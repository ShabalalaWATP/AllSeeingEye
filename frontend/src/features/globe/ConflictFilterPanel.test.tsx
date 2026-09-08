import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { useEventsStore } from '@/stores/events';
import { ConflictFilterPanel } from './ConflictFilterPanel';
import { useConflictFilters } from './useConflictFilters';

afterEach(() => useEventsStore.getState().reset());
const clash = liveEvent({ id: 'clash', category: 'conflict', subtype: 'fight' });
const protest = liveEvent({ id: 'protest', category: 'conflict', subtype: 'protest' });
const plane = liveEvent({ id: 'plane', category: 'aviation' });
const events = [clash, protest, plane];

it('lets operators choose report types with loaded counts and truthful language', () => {
  function Harness() {
    const filters = useConflictFilters(events);
    return (
      <>
        <ConflictFilterPanel {...filters} />
        <output aria-label="Shown IDs">
          {filters.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Harness />);
  expect(screen.getByRole('radio', { name: /All loaded reports 2 loaded reports/ })).toBeChecked();
  fireEvent.click(screen.getByRole('radio', { name: /Protests and riots 1 loaded reports/ }));
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('protest,plane');
  expect(screen.getByText(/not verified conflicts or unique incidents/)).toBeInTheDocument();
  expect(screen.getByText(/do not establish armed conflict/)).toBeInTheDocument();
});

it('clears a selected excluded report but preserves unrelated selections and category visibility', () => {
  useEventsStore.getState().applyUpsert(events);
  useEventsStore.getState().select('clash');
  useEventsStore.getState().toggleCategory('conflict');
  const { result } = renderHook(() => useConflictFilters(events));
  act(() => result.current.setGroup('protests'));
  expect(useEventsStore.getState().selectedId).toBeNull();
  expect(useEventsStore.getState().hidden).toContain('conflict');
  act(() => useEventsStore.getState().select('plane'));
  act(() => result.current.setGroup('armed_clashes'));
  expect(useEventsStore.getState().selectedId).toBe('plane');
  expect(result.current.counts.all).toBe(2);
});

it('hides provisional monthly baselines by default and lets the operator opt in explicitly', () => {
  const historical = liveEvent({
    id: 'july',
    category: 'conflict',
    subtype: 'organised_violence',
    attributes: { dataset_status: 'provisional_monthly', dataset_version: '26.0.7' },
  });
  const withHistory = [...events, historical];
  useEventsStore.getState().applyUpsert(withHistory);
  function Harness() {
    const filters = useConflictFilters(withHistory);
    return (
      <>
        <ConflictFilterPanel {...filters} />
        <output aria-label="Shown IDs">
          {filters.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Harness />);
  const toggle = screen.getByRole('checkbox', { name: 'Historical baseline (1 loaded)' });
  expect(toggle).not.toBeChecked();
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('clash,protest,plane');
  expect(screen.getByLabelText('Shown IDs')).not.toHaveTextContent('july');
  fireEvent.click(toggle);
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('july');
  fireEvent.click(screen.getByRole('radio', { name: /Organised violence.*1 loaded reports/ }));
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('plane,july');
  act(() => useEventsStore.getState().select('july'));
  fireEvent.click(toggle);
  expect(screen.getByLabelText('Shown IDs')).toHaveTextContent('plane');
  expect(useEventsStore.getState().selectedId).toBeNull();
});

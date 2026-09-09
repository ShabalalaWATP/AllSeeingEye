import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { afterEach, expect, it } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { matchesConflictDisplay } from '@/lib/conflictDisplayFilters';
import { useEventsStore } from '@/stores/events';
import { ConflictFilterPanel } from './ConflictFilterPanel';
import { useConflictFilters } from './useConflictFilters';

afterEach(() => useEventsStore.getState().reset());
const exact = liveEvent({
  id: 'exact',
  category: 'conflict',
  subtype: 'fight',
  source_id: 'acled',
  title: 'Kyiv clashes',
  summary: 'Bridge damaged',
  geo_confidence: 'exact',
  point: { lat: 50, lon: 30 },
});
const city = liveEvent({
  ...exact,
  id: 'city',
  subtype: 'protest',
  source_id: 'gdelt',
  title: 'Kyiv protest',
  summary: null,
  geo_confidence: 'city',
});
const plane = liveEvent({ id: 'plane', category: 'aviation' });
const events = [exact, city, plane];

it('combines text, source and precision with type counts while retaining other categories', () => {
  function Harness() {
    const filters = useConflictFilters(events);
    return (
      <>
        <ConflictFilterPanel {...filters} />
        <output aria-label="Shown">{filters.filtered.map((event) => event.id).join(',')}</output>
      </>
    );
  }
  render(<Harness />);
  fireEvent.change(screen.getByLabelText('Search loaded reports'), {
    target: { value: 'KYIV bridge' },
  });
  expect(screen.getByLabelText('Shown')).toHaveTextContent('exact,plane');
  expect(screen.getByRole('radio', { name: 'All loaded reports 1 loaded reports' })).toBeChecked();
  fireEvent.change(screen.getByLabelText('Search loaded reports'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Report source'), { target: { value: 'gdelt' } });
  expect(screen.getByLabelText('Shown')).toHaveTextContent('city,plane');
  fireEvent.change(screen.getByLabelText('Location precision'), { target: { value: 'exact' } });
  expect(screen.getByLabelText('Shown').textContent).toBe('plane');
});

it('clears excluded selections without altering layer visibility or unrelated selections', () => {
  useEventsStore.getState().applyUpsert(events);
  useEventsStore.getState().select('exact');
  const { result } = renderHook(() => useConflictFilters(events));
  act(() => result.current.setPrecision('approximate'));
  expect(useEventsStore.getState().selectedId).toBeNull();
  act(() => useEventsStore.getState().select('plane'));
  act(() => result.current.setQuery('nothing matches'));
  expect(useEventsStore.getState().selectedId).toBe('plane');
  expect(result.current.sourceOptions).toHaveLength(2);
});

it('does not turn unknown or unlocated records into approximate or exact points', () => {
  const unknown = liveEvent({ ...city, geo_confidence: 'none' });
  const unlocated = liveEvent({ ...exact, point: null });
  for (const event of [unknown, unlocated]) {
    expect(matchesConflictDisplay(event, '', 'all', 'all')).toBe(true);
    expect(matchesConflictDisplay(event, '', 'all', 'exact')).toBe(false);
    expect(matchesConflictDisplay(event, '', 'all', 'approximate')).toBe(false);
  }
  expect(matchesConflictDisplay(city, 'kyiv protest', 'gdelt', 'approximate')).toBe(true);
});

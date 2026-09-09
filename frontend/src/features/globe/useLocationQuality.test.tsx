import { act, render, renderHook, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { GeographicPrecisionPanel } from './GeographicPrecisionPanel';
import { locationQuality, precisionLabel } from './geographicPrecision';
import { useLocationQuality } from './useLocationQuality';

const records = [
  liveEvent({ id: 'exact', title: 'Reported harbour' }),
  liveEvent({ id: 'city', title: 'Approximate city', geo_confidence: 'city' }),
  liveEvent({
    id: 'orbit',
    title: 'Orbital estimate',
    category: 'space',
    subtype: 'satellite_position',
  }),
  liveEvent({ id: 'country', title: 'Country only', geo_confidence: 'country' }),
];

it.each(['satellite', 'satellite_position'])(
  'recognises %s as propagated rather than exact',
  (subtype) => {
    const event = liveEvent({ category: 'space', subtype });
    expect(locationQuality(event)).toBe('propagated');
    expect(precisionLabel(event)).toContain('not an observed position');
    expect(locationQuality({ ...event, point: null })).toBe('unplotted');
  },
);

it('honours propagated metadata without misclassifying other categories or invalid points', () => {
  expect(
    locationQuality(
      liveEvent({
        category: 'space',
        subtype: 'orbital',
        attributes: { position_kind: 'propagated' },
      }),
    ),
  ).toBe('propagated');
  expect(locationQuality(liveEvent({ category: 'aviation', subtype: 'satellite' }))).toBe(
    'reported',
  );
  expect(locationQuality(liveEvent({ point: { lat: 91, lon: 0 } }))).toBe('unplotted');
});

it('returns the selected quality for map layers without changing source positions', () => {
  const { result, rerender } = renderHook(({ hidden }) => useLocationQuality(records, hidden), {
    initialProps: { hidden: [] as ('space' | 'disaster')[] },
  });
  expect(result.current.filtered).toEqual(records);
  act(() => result.current.setFilter('approximate'));
  expect(result.current.filtered).toEqual([records[1]]);
  expect(result.current.filtered[0]).toBe(records[1]);
  act(() => result.current.setFilter('propagated'));
  expect(result.current.filtered).toEqual([records[2]]);
  rerender({ hidden: ['space'] });
  expect(result.current.filtered).toEqual([]);
  act(() => result.current.setFilter('unplotted'));
  expect(result.current.filtered).toEqual([records[3]]);
});

it('searches every quality, selects original records and applies the controlled map filter', async () => {
  const onSelect = vi.fn();
  function Harness() {
    const quality = useLocationQuality(records, []);
    return (
      <>
        <output aria-label="Map records">{quality.filtered.map((row) => row.id).join(',')}</output>
        <GeographicPrecisionPanel
          events={quality.visible}
          hidden={[]}
          filter={quality.filter}
          onFilterChange={quality.setFilter}
          onSelect={onSelect}
        />
      </>
    );
  }
  render(<Harness />);
  const user = userEvent.setup();
  expect(screen.getByRole('region', { name: 'Location quality' })).toBeVisible();
  await user.type(screen.getByRole('searchbox', { name: 'Search loaded records' }), 'harbour');
  expect(screen.queryByRole('button', { name: /Approximate city/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: /Reported harbour/ }));
  expect(onSelect).toHaveBeenCalledWith(records[0]);
  expect(screen.getByLabelText('Map records')).toHaveTextContent('exact,city,orbit,country');
  await user.clear(screen.getByRole('searchbox'));
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Show on map or globe' }),
    'propagated',
  );
  expect(screen.getByLabelText('Map records')).toHaveTextContent(/^orbit$/);
  expect(screen.getByRole('button', { name: /Orbital estimate/ })).toBeVisible();
  expect(screen.queryByRole('button', { name: /Reported harbour/ })).not.toBeInTheDocument();
});

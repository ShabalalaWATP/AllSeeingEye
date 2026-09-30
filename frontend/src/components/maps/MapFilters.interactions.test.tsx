import { fireEvent, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useState } from 'react';
import { expect, it, vi } from 'vitest';
import type { MapState } from '@/lib/api/mapViews';
import { MapFilters } from './MapFilters';
import { initialMapState } from './savedMapState';

function mount(initial: Partial<MapState> = {}) {
  const changed = vi.fn();
  function Harness() {
    const [state, setState] = useState({ ...initialMapState(), ...initial });
    return (
      <MapFilters
        state={state}
        days={['2026-01-02']}
        sources={[
          ['one', 'First source'],
          ['two', 'Second source'],
        ]}
        onChange={(next) => {
          changed(next);
          setState(next);
        }}
      />
    );
  }
  render(<Harness />);
  return { changed, user: userEvent.setup() };
}

it('preserves a custom start when changing the time basis and clears it only for all dates', async () => {
  const { user, changed } = mount({ published_since: '2026-01-01T12:00:00Z' });
  expect(screen.getByLabelText('Publication timeline (UTC)')).toHaveValue('__since_only__');
  fireEvent.change(screen.getByLabelText('Publication timeline (UTC)'), {
    target: { value: '__since_only__' },
  });
  expect(changed).not.toHaveBeenCalled();
  await user.selectOptions(screen.getByLabelText('Timeline time basis'), 'recorded_time');
  const timeline = screen.getByLabelText('Project / acquisition / publication timeline (UTC)');
  expect(timeline).toHaveValue('__since_only__');
  expect(
    screen.getByRole('option', { name: 'Custom range: from a start date' }),
  ).toBeInTheDocument();
  await user.selectOptions(timeline, '2026-01-02');
  expect(changed).toHaveBeenLastCalledWith(
    expect.objectContaining({
      published_since: '2026-01-01T12:00:00Z',
      published_until: '2026-01-02T23:59:59.999Z',
      include_unknown_dates: false,
    }),
  );
  expect(screen.getByText(/Records without a valid project/)).toBeVisible();
  await user.selectOptions(timeline, '');
  expect(changed).toHaveBeenLastCalledWith(
    expect.objectContaining({
      published_since: null,
      published_until: null,
      include_unknown_dates: true,
    }),
  );
  await user.selectOptions(
    screen.getByLabelText('Timeline time basis'),
    'acquisition_or_publication',
  );
  expect(screen.getByLabelText('Acquisition / publication timeline (UTC)')).toHaveValue('');
  await user.selectOptions(screen.getByLabelText('Timeline time basis'), 'publication');
  expect(screen.getByLabelText('Publication timeline (UTC)')).toHaveValue('');
});

it('edits source subsets without interpreting the multiple-selection placeholder as a source', async () => {
  const { user, changed } = mount({ source_ids: ['one', 'two'] });
  const source = screen.getByLabelText('Evidence source');
  fireEvent.change(source, { target: { value: '__multiple__' } });
  expect(changed).not.toHaveBeenCalled();
  await user.selectOptions(source, 'one');
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ source_ids: ['one'] }));
  await user.selectOptions(source, '');
  await user.click(screen.getByText('Additional map filters and basemap'));
  await user.click(screen.getByLabelText('Second source'));
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ source_ids: ['two'] }));
  await user.click(screen.getByLabelText('Second source'));
  expect(changed).toHaveBeenLastCalledWith(expect.objectContaining({ source_ids: [] }));
});

it('round-trips UTC range fields and unknown-date inclusion independently', async () => {
  const { user, changed } = mount({ time_basis: 'recorded_time' });
  await user.click(screen.getByText('Additional map filters and basemap'));
  fireEvent.change(screen.getByLabelText('Time from (UTC)'), {
    target: { value: '2026-01-01T12:00:00' },
  });
  expect(changed).toHaveBeenLastCalledWith(
    expect.objectContaining({ published_since: '2026-01-01T12:00Z' }),
  );
  fireEvent.change(screen.getByLabelText('Time until (UTC)'), {
    target: { value: '2026-01-02T13:00:00' },
  });
  expect(changed).toHaveBeenLastCalledWith(
    expect.objectContaining({ published_until: '2026-01-02T13:00Z' }),
  );
  fireEvent.change(screen.getByLabelText('Time from (UTC)'), { target: { value: '' } });
  fireEvent.change(screen.getByLabelText('Time until (UTC)'), { target: { value: '' } });
  await user.click(screen.getByLabelText('Include unknown project/observation/reporting dates'));
  expect(changed).toHaveBeenLastCalledWith(
    expect.objectContaining({
      published_since: null,
      published_until: null,
      include_unknown_dates: false,
    }),
  );
});

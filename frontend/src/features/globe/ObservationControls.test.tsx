import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import {
  ObservationControls,
  filterObservations,
  observationKind,
  useObservationFilters,
} from './ObservationControls';
import { buildEventLayers } from './layers/registry';
import type { Category, LiveEvent } from '@/lib/api/eventSchemas';

const aircraft = liveEvent({ id: 'plane', category: 'aviation' });
const vessel = liveEvent({ id: 'boat', category: 'maritime', subtype: 'vessel_position' });
const thermal = liveEvent({
  id: 'thermal',
  category: 'disaster',
  source_id: 'firms_viirs_noaa20',
  subtype: 'thermal_detection',
});
const warning = liveEvent({ id: 'warning', category: 'maritime', subtype: 'hazard' });
const quake = liveEvent({ id: 'quake', category: 'disaster', subtype: 'earthquake' });
const events = [aircraft, vessel, thermal, warning, quake];

it('keeps unrelated warnings and disasters when every observation overlay is off', () => {
  expect(filterObservations(events, { aircraft: false, vessels: false, firms: false })).toEqual([
    warning,
    quake,
  ]);
  expect(filterObservations(events, { aircraft: true, vessels: true, firms: true })).toEqual(
    events,
  );
  expect(observationKind({ ...thermal, source_id: 'unknown' })).toBeNull();
  expect(observationKind({ ...thermal, source_id: 'firms' })).toBe('firms');
});

it('toggles each overlay independently while explaining loaded counts and hidden categories', async () => {
  function Panel() {
    const state = useObservationFilters(events);
    const [hidden, setHidden] = useState<Category[]>(['maritime']);
    return (
      <>
        <ObservationControls
          events={events}
          visibility={state.visibility}
          hidden={hidden}
          onToggleCategory={() => setHidden([])}
          onToggle={state.toggle}
        />
        <output aria-label="Visible records">
          {state.filtered.map((event) => event.id).join(',')}
        </output>
      </>
    );
  }
  render(<Panel />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('switch', { name: 'Aircraft positions' }));
  expect(screen.getByLabelText('Visible records')).toHaveTextContent('boat,thermal,warning,quake');
  await user.click(screen.getByRole('switch', { name: 'FIRMS thermal detections' }));
  expect(screen.getByLabelText('Visible records')).toHaveTextContent('boat,warning,quake');
  expect(screen.getByText(/category hidden/)).toBeInTheDocument();
  expect(screen.getByRole('switch', { name: 'Vessel positions' })).not.toBeChecked();
  await user.click(screen.getByRole('switch', { name: 'Vessel positions' }));
  expect(screen.getByRole('switch', { name: 'Vessel positions' })).toBeChecked();
  expect(screen.queryByText(/category hidden/)).not.toBeInTheDocument();
  await user.click(screen.getByRole('switch', { name: 'Vessel positions' }));
  expect(screen.getByLabelText('Visible records')).toHaveTextContent('warning,quake');
});

it('keeps selected traffic visible within the low-zoom sample and obeys category filters', () => {
  const traffic = Array.from({ length: 300 }, (_, i) =>
    liveEvent({
      id: `a${String(i)}`,
      category: 'aviation',
      geo_confidence: 'exact',
      point: { lon: 5, lat: 50 },
    }),
  );
  const layers = buildEventLayers(traffic, [], vi.fn(), 'a299', { zoom: 1, onCluster: vi.fn() });
  const icons = layers.find((layer) => layer.id === 'event-icons');
  const records = icons?.props.data as LiveEvent[];
  expect(records).toHaveLength(250);
  expect(records.some((event) => event.id === 'a299')).toBe(true);
  expect(layers.some((layer) => layer.id.includes('cluster'))).toBe(true);
  expect(
    buildEventLayers(traffic, ['aviation'], vi.fn(), 'a299', { zoom: 1, onCluster: vi.fn() }),
  ).toHaveLength(0);
});

import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { useMemo } from 'react';
import { MemoryRouter } from 'react-router';
import { beforeEach, expect, it, vi } from 'vitest';

import { ORDERED_CATEGORIES } from '@/lib/categories';
import { useEventsStore } from '@/stores/events';
import { useGlobeStore } from '@/stores/globe';

import { ControlPanel, GlobeControls } from './GlobeControls';
import { mapGuidePanel } from './MapGuidePanel';
import type { MapGuideSources } from './mapGuideControls';

const toggleFires = vi.fn();
const setCameras = vi.fn();

function guideSources(): MapGuideSources {
  return {
    events: {
      fires: { enabled: false, toggleEnabled: toggleFires },
      observations: {
        visibility: { aircraft: true, vessels: false, firms: false },
        toggle: vi.fn(),
      },
    },
    cameras: { enabled: false, setEnabled: setCameras },
    figures: { enabled: false, setEnabled: vi.fn() },
    regions: { showRegions: false, setShowRegions: vi.fn() },
    grid: { enabled: false, setEnabled: vi.fn() },
  } as unknown as MapGuideSources;
}

function Harness({ initial = null }: { initial?: string | null }) {
  const sources = useMemo(() => guideSources(), []);
  return (
    <MemoryRouter>
      <GlobeControls layers={null} initial={initial}>
        {(open) => [
          mapGuidePanel(open, sources),
          <ControlPanel
            key="conflict"
            side="left"
            label="Conflict reports"
            icon="conflict"
            entry={false}
          >
            <p>Conflict report filters</p>
          </ControlPanel>,
        ]}
      </GlobeControls>
    </MemoryRouter>
  );
}

beforeEach(() => {
  useEventsStore.setState({ hidden: ORDERED_CATEGORIES.filter((name) => name !== 'conflict') });
  useGlobeStore.setState({ interference: false });
  toggleFires.mockClear();
  setCameras.mockClear();
});

it('names every map layer, says what it is and opens the tool that filters it', async () => {
  const user = userEvent.setup();
  render(<Harness />);
  await user.click(screen.getByRole('button', { name: 'Map guide' }));
  const live = within(screen.getByRole('list', { name: 'Live events' }));
  expect(live.getByText('Conflict & unrest')).toBeInTheDocument();
  expect(
    live.getByText('Satellite thermal detections and reported wildfires.'),
  ).toBeInTheDocument();
  expect(screen.getByRole('list', { name: 'Reference layers' })).toBeInTheDocument();
  expect(screen.getByRole('list', { name: 'Map setup' })).toBeInTheDocument();
  expect(screen.getByRole('list', { name: 'Planning tools' })).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Open sources & data' })).toHaveAttribute(
    'href',
    '/sources',
  );
  await user.click(live.getByRole('button', { name: 'Open Conflict reports' }));
  expect(screen.getByText('Conflict report filters')).toBeInTheDocument();
});

it('switches layers on from the guide without leaving the map', async () => {
  const user = userEvent.setup();
  render(<Harness />);
  await user.click(screen.getByRole('button', { name: 'Map guide' }));
  const cyber = screen.getByRole('switch', { name: 'Cyber incidents on the map' });
  expect(cyber).not.toBeChecked();
  await user.click(cyber);
  expect(useEventsStore.getState().hidden).not.toContain('cyber');
  await user.click(screen.getByRole('switch', { name: 'GPS and GNSS interference on the map' }));
  expect(useGlobeStore.getState().interference).toBe(true);
  await user.click(screen.getByRole('switch', { name: 'Fires and thermal detections on the map' }));
  expect(toggleFires).toHaveBeenCalled();
  await user.click(screen.getByRole('switch', { name: 'Public cameras on the map' }));
  expect(setCameras).toHaveBeenCalledWith(true);
});

it('opens the guide directly when a link asks for it', () => {
  render(<Harness initial="Map guide" />);
  expect(screen.getByRole('list', { name: 'Live events' })).toBeInTheDocument();
});

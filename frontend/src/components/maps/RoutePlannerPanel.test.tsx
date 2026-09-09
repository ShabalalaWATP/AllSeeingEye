import { useState } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { calculateNavigationRoute, fetchNavigationCapabilities } from '@/lib/api/navigation';
import { searchNavigationPlaces } from '@/lib/api/navigationPlaces';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { RoutePlannerPanel } from './RoutePlannerPanel';
import { useRoutePlannerState } from './useRoutePlannerState';

vi.mock('@/lib/api/navigation', () => ({
  calculateNavigationRoute: vi.fn(),
  fetchNavigationCapabilities: vi.fn(),
}));
vi.mock('@/lib/api/navigationPlaces', () => ({ searchNavigationPlaces: vi.fn() }));
const route = {
  mode: 'walking' as const,
  distance_km: 2,
  duration_seconds: 600,
  coordinates: [
    [0, 0],
    [0.01, 0.01],
  ] as [number, number][],
  steps: [
    { instruction: 'Turn left at <script>street</script>.', distance_km: 2, duration_seconds: 600 },
  ],
  provider: 'FOSSGIS Valhalla' as const,
  attribution: 'OpenStreetMap',
  limitations: 'Planning estimate only.',
};
const points = [
  { lat: 0, lon: 0 },
  { lat: 0.01, lon: 0.01 },
];
beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ user: plainUser, status: 'authenticated' });
  vi.mocked(fetchNavigationCapabilities).mockResolvedValue({
    provider: 'FOSSGIS Valhalla',
    operator_contact: 'operator@example.com',
    available: true,
    privacy: 'Coordinates sent only on Calculate route.',
  });
  vi.mocked(calculateNavigationRoute).mockResolvedValue(route);
});

it('explains missing operator contact and does not allow provider requests', async () => {
  vi.mocked(fetchNavigationCapabilities).mockResolvedValue({
    provider: 'FOSSGIS Valhalla',
    operator_contact: '',
    available: false,
    configuration_message: 'Configure ASE_FEEDS_CONTACT before calculating routes.',
    privacy: 'No coordinates sent.',
  });
  render(<RoutePlannerPanel onRouteChange={vi.fn()} initialWaypoints={points} />);
  expect(await screen.findByRole('status')).toHaveTextContent('ASE_FEEDS_CONTACT');
  expect(screen.getByRole('button', { name: 'Calculate route' })).toBeDisabled();
  expect(calculateNavigationRoute).not.toHaveBeenCalled();
});

it('requires explicit Calculate, displays contact and inert directions, and clears on edit', async () => {
  const user = userEvent.setup();
  const changed = vi.fn();
  render(<RoutePlannerPanel onRouteChange={changed} initialWaypoints={points} />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  expect(calculateNavigationRoute).not.toHaveBeenCalled();
  await user.selectOptions(screen.getByRole('combobox', { name: 'Travel mode' }), 'walking');
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  expect(await screen.findByRole('status')).toHaveTextContent('2.0 km');
  expect(calculateNavigationRoute).toHaveBeenCalledWith(
    { mode: 'walking', waypoints: points },
    expect.any(AbortSignal),
  );
  expect(changed).toHaveBeenLastCalledWith(route);
  await user.click(screen.getByText('Directions (1)'));
  expect(screen.getByText('Turn left at <script>street</script>.')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  await user.type(screen.getByRole('textbox', { name: 'Waypoint 1 latitude' }), '1');
  expect(changed).toHaveBeenLastCalledWith(null);
  expect(screen.queryByRole('status')).not.toBeInTheDocument();
});

it('refuses blank coordinates and displays a safe API error', async () => {
  const user = userEvent.setup();
  const rendered = render(<RoutePlannerPanel onRouteChange={vi.fn()} />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Search and select a match');
  expect(calculateNavigationRoute).not.toHaveBeenCalled();
  rendered.unmount();
  vi.mocked(calculateNavigationRoute).mockRejectedValue(
    new ApiError(422, 'invalid_request', 'Route unavailable.'),
  );
  render(<RoutePlannerPanel onRouteChange={vi.fn()} initialWaypoints={points} />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Route unavailable.');
});

it('aborts an old account request and never releases its route', async () => {
  let finish: (value: typeof route) => void = vi.fn();
  vi.mocked(calculateNavigationRoute).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const user = userEvent.setup();
  const changed = vi.fn();
  render(<RoutePlannerPanel onRouteChange={changed} initialWaypoints={points} />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  const signal = vi.mocked(calculateNavigationRoute).mock.calls[0]![1];
  act(() => useAuthStore.setState({ user: { ...plainUser, id: 'another-account' } }));
  expect(signal.aborted).toBe(true);
  await act(async () => {
    finish(route);
    await Promise.resolve();
  });
  await waitFor(() => expect(changed).toHaveBeenLastCalledWith(null));
  expect(changed).not.toHaveBeenCalledWith(route);
});

it('searches only explicitly, requires choosing address matches and calculates resolved stops', async () => {
  vi.mocked(searchNavigationPlaces)
    .mockResolvedValueOnce([{ label: 'Oxford station, Oxford, UK', lat: 0, lon: 0 }])
    .mockResolvedValueOnce([{ label: 'Oxford museum, Oxford, UK', lat: 0.01, lon: 0.01 }]);
  const user = userEvent.setup();
  render(<RoutePlannerPanel onRouteChange={vi.fn()} />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  expect(screen.getByRole('combobox', { name: 'Enter stops using' })).toHaveValue('address');
  expect(screen.queryByRole('textbox', { name: 'Waypoint 1 latitude' })).toBeNull();
  await user.type(
    screen.getByRole('textbox', { name: 'Start address or place' }),
    'Oxford station',
  );
  expect(searchNavigationPlaces).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Search start' }));
  await user.click(await screen.findByRole('button', { name: /Oxford station, Oxford/ }));
  await user.type(
    screen.getByRole('textbox', { name: 'Destination address or place' }),
    'Oxford museum',
  );
  await user.click(screen.getByRole('button', { name: 'Search destination' }));
  await user.click(await screen.findByRole('button', { name: /Oxford museum, Oxford/ }));
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  expect(calculateNavigationRoute).toHaveBeenLastCalledWith(
    { mode: 'driving', waypoints: points },
    expect.any(AbortSignal),
  );
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Enter stops using' }),
    'coordinates',
  );
  expect(screen.getByRole('textbox', { name: 'Waypoint 2 latitude' })).toHaveValue('0.01');
});

it('cancels stale address results after input edits and explains empty results', async () => {
  let finish: (value: Awaited<ReturnType<typeof searchNavigationPlaces>>) => void = vi.fn();
  vi.mocked(searchNavigationPlaces).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const user = userEvent.setup();
  render(<RoutePlannerPanel onRouteChange={vi.fn()} />);
  const input = screen.getByRole('textbox', { name: 'Start address or place' });
  await user.type(input, 'Old place');
  await user.click(screen.getByRole('button', { name: 'Search start' }));
  const signal = vi.mocked(searchNavigationPlaces).mock.calls[0]![1];
  await user.type(input, ' new');
  expect(signal.aborted).toBe(true);
  await act(async () => {
    finish([{ label: 'Old match', lat: 0, lon: 0 }]);
    await Promise.resolve();
  });
  expect(screen.queryByText('Old match')).toBeNull();
  vi.mocked(searchNavigationPlaces).mockResolvedValueOnce([]);
  await user.click(screen.getByRole('button', { name: 'Search start' }));
  expect(await screen.findByText(/No matches. Add a city/)).toBeInTheDocument();
});

it('keeps stable stops when reversing and supports search failure with coordinate fallback', async () => {
  vi.mocked(searchNavigationPlaces).mockRejectedValueOnce(
    new ApiError(422, 'invalid_request', 'Address search unavailable.'),
  );
  const user = userEvent.setup();
  render(<RoutePlannerPanel onRouteChange={vi.fn()} />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  await user.type(screen.getByRole('textbox', { name: 'Start address or place' }), 'Oxford');
  await user.click(screen.getByRole('button', { name: 'Search start' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Address search unavailable');
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Enter stops using' }),
    'coordinates',
  );
  for (const [index, point] of points.entries()) {
    await user.type(
      screen.getByRole('textbox', { name: `Waypoint ${index + 1} latitude` }),
      String(point.lat),
    );
    await user.type(
      screen.getByRole('textbox', { name: `Waypoint ${index + 1} longitude` }),
      String(point.lon),
    );
  }
  await user.click(screen.getByRole('button', { name: 'Reverse stops' }));
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  expect(calculateNavigationRoute).toHaveBeenCalledWith(
    { mode: 'driving', waypoints: [...points].reverse() },
    expect.any(AbortSignal),
  );
  await user.click(screen.getByRole('button', { name: 'Add waypoint' }));
  expect(screen.getByRole('textbox', { name: 'Waypoint 2 latitude' })).toHaveValue('');
  await user.click(screen.getByRole('button', { name: 'Remove waypoint 2' }));
  expect(screen.queryByRole('textbox', { name: 'Waypoint 3 latitude' })).toBeNull();
});

function PersistentPlanner({ seed = false }: { seed?: boolean }) {
  const state = useRoutePlannerState();
  const [open, setOpen] = useState(true);
  return (
    <>
      <button onClick={() => setOpen(!open)}>Toggle route tool</button>
      <p>Overlay {state.route?.distance_km ?? 'none'}</p>
      {open && (
        <RoutePlannerPanel
          onRouteChange={state.setRoute}
          draft={state.draft}
          onDraftChange={state.setDraft}
          result={state.route}
          {...(seed ? { initialWaypoints: points } : {})}
        />
      )}
    </>
  );
}

it('keeps a closed tool route and its matching stops together, then resets on account change', async () => {
  const user = userEvent.setup();
  render(<PersistentPlanner seed />);
  await screen.findByRole('link', { name: 'operator@example.com' });
  await user.selectOptions(screen.getByRole('combobox', { name: 'Travel mode' }), 'walking');
  await user.click(screen.getByRole('button', { name: 'Calculate route' }));
  expect(await screen.findByText('Overlay 2')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Toggle route tool' }));
  expect(screen.queryByRole('region', { name: 'Route planner' })).toBeNull();
  expect(screen.getByText('Overlay 2')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Toggle route tool' }));
  expect(screen.getByRole('combobox', { name: 'Travel mode' })).toHaveValue('walking');
  expect(screen.getByRole('textbox', { name: 'Waypoint 2 latitude' })).toHaveValue('0.01');
  expect(screen.getByRole('status')).toHaveTextContent('2.0 km');
  await user.type(screen.getByRole('textbox', { name: 'Waypoint 1 latitude' }), '1');
  expect(screen.getByText('Overlay none')).toBeInTheDocument();
  act(() => useAuthStore.setState({ user: { ...plainUser, id: 'replacement-account' } }));
  expect(screen.getByRole('combobox', { name: 'Travel mode' })).toHaveValue('driving');
});

it('preserves an unfinished address query on close without automatically searching on reopen', async () => {
  const user = userEvent.setup();
  render(<PersistentPlanner />);
  await user.type(
    screen.getByRole('textbox', { name: 'Start address or place' }),
    'Oxford station',
  );
  await user.click(screen.getByRole('button', { name: 'Toggle route tool' }));
  await user.click(screen.getByRole('button', { name: 'Toggle route tool' }));
  expect(screen.getByRole('textbox', { name: 'Start address or place' })).toHaveValue(
    'Oxford station',
  );
  expect(searchNavigationPlaces).not.toHaveBeenCalled();
});

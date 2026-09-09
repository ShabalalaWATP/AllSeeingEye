import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/errors';
import { calculateNavigationRoute, fetchNavigationCapabilities } from '@/lib/api/navigation';
import { useAuthStore } from '@/stores/auth';
import { plainUser } from '@/test/fixtures';
import { RoutePlannerPanel } from './RoutePlannerPanel';

vi.mock('@/lib/api/navigation', () => ({
  calculateNavigationRoute: vi.fn(),
  fetchNavigationCapabilities: vi.fn(),
}));
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
  expect(screen.getByRole('alert')).toHaveTextContent('Enter valid latitude');
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

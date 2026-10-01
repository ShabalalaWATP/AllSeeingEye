import { act, render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { useEventsStore } from '@/stores/events';
import { liveEvent } from '@/test/fixtures';
import { MapLayerRail } from './MapLayerRail';
it('toggles observations and restores a hidden category when enabling its feed', async () => {
  const user = userEvent.setup();
  const onToggle = vi.fn();
  useEventsStore.setState({ hidden: ['aviation'] });
  render(
    <MapLayerRail
      events={[]}
      counts={{}}
      visibility={{ aircraft: false, vessels: true, firms: true }}
      onToggle={onToggle}
    />,
  );
  await user.click(screen.getByRole('switch', { name: 'Flights' }));
  expect(useEventsStore.getState().hidden).not.toContain('aviation');
  expect(onToggle).toHaveBeenCalledWith('aircraft');
  await user.click(screen.getByRole('switch', { name: 'Boats' }));
  expect(onToggle).toHaveBeenCalledWith('vessels');
});
it('reports loaded counts and separately toggles categories and context layers', async () => {
  const user = userEvent.setup();
  useEventsStore.setState({ hidden: [] });
  render(
    <MapLayerRail
      events={[liveEvent({ category: 'aviation' })]}
      counts={{ news: 2 }}
      visibility={{ aircraft: true, vessels: true, firms: true }}
      onToggle={vi.fn()}
    />,
  );
  expect(screen.getByRole('switch', { name: 'Flights' })).toHaveAttribute('aria-checked', 'true');
  expect(screen.getByText('Flights: 1 loaded')).toBeInTheDocument();
  expect(screen.getByText('News: 2 loaded')).toBeInTheDocument();
  await user.click(screen.getByRole('switch', { name: 'News' }));
  expect(screen.getByRole('switch', { name: 'News' })).toHaveAttribute('aria-checked', 'false');
  expect(screen.queryByRole('switch', { name: /Day and night/ })).not.toBeInTheDocument();
  expect(screen.queryByRole('switch', { name: /GNSS|GPS/ })).not.toBeInTheDocument();
});

it('keeps GPS interference out of the rail so the Cyber control owns it', () => {
  render(
    <MapLayerRail
      events={[]}
      counts={{}}
      visibility={{ aircraft: true, vessels: true, firms: true }}
      onToggle={vi.fn()}
      openPanel={vi.fn()}
    />,
  );
  expect(screen.queryByText('GNSS')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'GNSS filters' })).not.toBeInTheDocument();
  expect(screen.getAllByRole('switch')[0]).toHaveAccessibleName('Flights');
});

it('keeps a focused switch named and focused while synthetic events stream in', () => {
  useEventsStore.setState({ hidden: [] });
  const rail = (count: number) => (
    <MapLayerRail
      events={Array.from({ length: count }, (_, index) =>
        liveEvent({ id: `flight-${String(index)}`, category: 'aviation' }),
      )}
      counts={{ news: count }}
      visibility={{ aircraft: true, vessels: true, firms: true }}
      onToggle={vi.fn()}
    />
  );
  const view = render(rail(1));
  const flights = screen.getByRole('switch', { name: 'Flights' });
  act(() => flights.focus());
  for (const count of [2, 5, 40, 1200]) {
    view.rerender(rail(count));
    expect(flights).toHaveFocus();
    expect(flights).toHaveAccessibleName('Flights');
    expect(flights).toHaveAccessibleDescription('');
    expect(flights).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('switch', { name: 'News' })).toHaveAccessibleName('News');
  }
  // The count stays readable on demand, outside any live region.
  const count = screen.getByText('Flights: 1200 loaded');
  expect(count.closest('[aria-live], [role="status"], [role="log"]')).toBeNull();
  expect(flights).not.toContainElement(count);
});

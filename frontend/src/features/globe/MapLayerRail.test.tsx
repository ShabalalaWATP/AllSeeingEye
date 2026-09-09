import { render, screen } from '@testing-library/react';
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
  await user.click(screen.getByRole('switch', { name: 'Flights 0' }));
  expect(useEventsStore.getState().hidden).not.toContain('aviation');
  expect(onToggle).toHaveBeenCalledWith('aircraft');
  await user.click(screen.getByRole('switch', { name: 'Boats 0' }));
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
  expect(screen.getByRole('switch', { name: 'Flights 1' })).toHaveAttribute('aria-checked', 'true');
  await user.click(screen.getByRole('switch', { name: 'News 2' }));
  expect(screen.getByRole('switch', { name: 'News 2' })).toHaveAttribute('aria-checked', 'false');
  expect(screen.queryByRole('switch', { name: /Day and night/ })).not.toBeInTheDocument();
  await user.click(screen.getByRole('switch', { name: /GNSS interference/ }));
  expect(screen.getByRole('switch', { name: 'GNSS interference 0' })).toHaveAttribute(
    'aria-checked',
    'true',
  );
});

it('places the captioned GNSS control before traffic and opens its dedicated filters', async () => {
  const open = vi.fn();
  const user = userEvent.setup();
  render(
    <MapLayerRail
      events={[]}
      counts={{}}
      visibility={{ aircraft: true, vessels: true, firms: true }}
      onToggle={vi.fn()}
      openPanel={open}
      gnssCount={3}
    />,
  );
  expect(screen.getAllByRole('switch')[0]).toHaveAccessibleName('GNSS interference 3');
  expect(screen.getByText('GNSS')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'GNSS filters' }));
  expect(open).toHaveBeenCalledWith('GNSS interference', expect.any(HTMLButtonElement));
});

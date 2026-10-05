import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import * as traffic from '@/lib/traffic';
import * as flights from './flightFilters';
import { MapLayerRail } from './MapLayerRail';

const aircraft = liveEvent({ id: 'aircraft', category: 'aviation', subtype: 'military_aircraft' });
const vessel = liveEvent({
  id: 'vessel',
  category: 'maritime',
  subtype: 'vessel_position',
  tags: ['military'],
});

it('does not derive legacy traffic lists for controlled drawers while keeping visible counts current', async () => {
  const militaryAircraft = vi.spyOn(flights, 'isMilitaryFlight');
  const militaryVessels = vi.spyOn(traffic, 'isMilitaryVessel');
  const openPanel = vi.fn();
  const onSelect = vi.fn();
  const onFilter = vi.fn();
  const props = {
    counts: {},
    visibility: { aircraft: true, vessels: true, firms: true },
    onToggle: vi.fn(),
    onFlightFilter: onFilter,
    onTrafficSelect: onSelect,
    openPanel,
  };
  const view = render(<MapLayerRail {...props} events={[aircraft, vessel]} />);
  expect(screen.getByText('Flights: 1 loaded')).toBeVisible();
  expect(screen.getByText('Boats: 1 loaded')).toBeVisible();
  expect(militaryAircraft).not.toHaveBeenCalled();
  expect(militaryVessels).not.toHaveBeenCalled();
  view.rerender(<MapLayerRail {...props} events={[vessel]} />);
  expect(screen.getByText('Flights: 0 loaded')).toBeVisible();
  expect(screen.getByText('Boats: 1 loaded')).toBeVisible();
  const user = userEvent.setup();
  const opener = screen.getByRole('button', { name: 'Boat list' });
  await user.click(opener);
  expect(openPanel).toHaveBeenCalledWith('Boat list', opener);
  expect(screen.queryByRole('region', { name: 'Boat list' })).not.toBeInTheDocument();
  expect(militaryAircraft).not.toHaveBeenCalled();
  expect(militaryVessels).not.toHaveBeenCalled();
});

it('derives standalone portal content only when opened and uses current replacement records', async () => {
  const militaryAircraft = vi.spyOn(flights, 'isMilitaryFlight');
  const onSelect = vi.fn();
  const props = {
    counts: {},
    visibility: { aircraft: true, vessels: true, firms: true },
    onToggle: vi.fn(),
    onFlightFilter: vi.fn(),
    onTrafficSelect: onSelect,
  };
  const view = render(<MapLayerRail {...props} events={[aircraft]} />);
  expect(militaryAircraft).not.toHaveBeenCalled();
  const updated = { ...aircraft, title: 'Current aircraft' };
  view.rerender(<MapLayerRail {...props} events={[updated]} />);
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Flight filters' }));
  expect(militaryAircraft).toHaveBeenCalled();
  expect(screen.getByText('1 provider-labelled military aircraft loaded')).toBeVisible();
  expect(screen.getByText('Current aircraft')).toBeVisible();
  view.rerender(<MapLayerRail {...props} events={[]} />);
  expect(screen.getByText('Flights: 0 loaded')).toBeVisible();
  expect(screen.queryByText('Current aircraft')).not.toBeInTheDocument();
});

it.each([
  { record: aircraft, label: 'Flight filters' },
  { record: vessel, label: 'Boat list' },
])(
  'keeps $label selection guards and delivers the current object to the latest callback',
  async ({ record, label }) => {
    const oldSelect = vi.fn();
    const newSelect = vi.fn();
    const props = {
      counts: {},
      visibility: { aircraft: true, vessels: true, firms: true },
      onToggle: vi.fn(),
      onFlightFilter: vi.fn(),
      onVesselFilter: vi.fn(),
    };
    const view = render(<MapLayerRail {...props} events={[record]} onTrafficSelect={oldSelect} />);
    const user = userEvent.setup();
    const opener = screen.getByRole('button', { name: label });
    await user.click(opener);
    const updated = { ...record, title: 'Corrected position' };
    view.rerender(
      <MapLayerRail {...props} events={[updated]} onTrafficSelect={newSelect} selectionDisabled />,
    );
    const result = screen.getByRole('button', { name: /Corrected position/ });
    expect(result).toBeDisabled();
    await user.click(result);
    expect(oldSelect).not.toHaveBeenCalled();
    expect(newSelect).not.toHaveBeenCalled();
    view.rerender(<MapLayerRail {...props} events={[updated]} onTrafficSelect={newSelect} />);
    await user.click(screen.getByRole('button', { name: /Corrected position/ }));
    expect(newSelect).toHaveBeenCalledOnce();
    expect(newSelect.mock.calls[0]?.[0]).toBe(updated);
    expect(oldSelect).not.toHaveBeenCalled();
    expect(opener).toHaveFocus();
    expect(screen.queryByRole('region', { name: label })).not.toBeInTheDocument();
  },
);

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { liveEvent } from '@/test/fixtures';
import { TrafficList } from './TrafficList';

it('renders25rows at a time and searches all loaded aircraft identifiers with keyboard selection', async () => {
  const user = userEvent.setup();
  const events = Array.from({ length: 1500 }, (_, i) =>
    liveEvent({
      id: `plane-${i}`,
      title: `Flight ${i}`,
      category: 'aviation',
      attributes: { icao24: `hex${i}` },
    }),
  );
  const select = vi.fn();
  render(<TrafficList events={events} kind="aircraft" available={9000} onSelect={select} />);
  const list = screen.getByRole('list', { name: 'aircraft search results' });
  expect(within(list).getAllByRole('button')).toHaveLength(25);
  expect(screen.getByText(/1,500 loaded.*9,000 total category/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Next' }));
  expect(within(list).getByText('Flight 25')).toBeInTheDocument();
  await user.type(screen.getByRole('searchbox', { name: 'Search aircraft' }), 'hex1499');
  expect(await within(list).findByRole('button', { name: /Flight 1499/ })).toBeInTheDocument();
  await user.tab();
  await user.keyboard('{Enter}');
  expect(select).toHaveBeenCalledWith(events[1499]);
});

it('shows source position age and military-only vessels without claiming unknown positions', async () => {
  const user = userEvent.setup();
  const military = liveEvent({
    id: 'naval',
    title: 'Type35 vessel',
    category: 'maritime',
    subtype: 'vessel_position',
    attributes: { military: true, mmsi: 123456789 },
    published_at: null,
  });
  const unknown = liveEvent({
    id: 'unknown',
    title: 'No position',
    category: 'maritime',
    subtype: 'vessel_position',
    point: null,
  });
  render(<TrafficList events={[military, unknown]} kind="vessels" onSelect={vi.fn()} />);
  expect(screen.getByRole('button', { name: /No position/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: /Type35 vessel/ })).toHaveTextContent('Unknown');
  await user.type(screen.getByRole('searchbox', { name: 'Search vessels' }), 'not-found');
  expect(await screen.findByText('No matching vessels loaded.')).toBeInTheDocument();
});

it('disables position selection while the user is measuring', () => {
  render(
    <TrafficList
      events={[liveEvent({ title: 'Position' })]}
      kind="aircraft"
      onSelect={vi.fn()}
      selectionDisabled
    />,
  );
  expect(screen.getByRole('button', { name: /Position/ })).toBeDisabled();
  expect(screen.getByText('Finish measuring to select a position.')).toBeInTheDocument();
});

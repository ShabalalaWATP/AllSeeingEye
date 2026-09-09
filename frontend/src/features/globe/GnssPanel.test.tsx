import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import type { JamCell } from '@/lib/api/aviation';
import { GnssPanel } from './GnssPanel';
import { useGnssFilters } from './useGnssFilters';
import { MapDisplaySettings } from './MapDisplaySettings';

const RECEIVED = Date.UTC(2026, 8, 9, 12);
const amber: JamCell = {
  lon: 1,
  lat: 50,
  size: 1,
  good: 23,
  bad: 2,
  percent_bad: 4,
  level: 'amber',
};
const red: JamCell = { lon: 2, lat: 51, size: 1, good: 0, bad: 5, percent_bad: 80, level: 'red' };
const green: JamCell = { ...amber, lon: 3, bad: 0, percent_bad: 0, level: 'green' };
function Panel({
  cells = [amber, red, green],
  now = RECEIVED,
  enabled = true,
  loading = false,
  error = null,
  limited = false,
  selectionDisabled = false,
  onSelect = vi.fn(),
  refresh = vi.fn(),
}: {
  cells?: JamCell[];
  now?: number;
  enabled?: boolean;
  loading?: boolean;
  error?: string | null;
  limited?: boolean;
  selectionDisabled?: boolean;
  onSelect?: (cell: JamCell) => void;
  refresh?: () => void;
}) {
  const filters = useGnssFilters(cells, RECEIVED, now);
  return (
    <GnssPanel
      enabled={enabled}
      filters={filters}
      selected={amber}
      selectionDisabled={selectionDisabled}
      onSelect={onSelect}
      data={{
        cells,
        updated_at: new Date(RECEIVED).toISOString(),
        receivedAt: RECEIVED,
        loading,
        error,
        limited,
        refresh,
      }}
    />
  );
}

it('filters flagged cells by severity and sample size, locates selections and explains their limits', async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  const refresh = vi.fn();
  render(<Panel onSelect={onSelect} refresh={refresh} />);
  expect(screen.getByText('2 flagged cells')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Locate GNSS cell 50, 3' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Locate GNSS cell 50, 1' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await user.click(screen.getByRole('button', { name: 'Locate GNSS cell 51, 2' }));
  expect(onSelect).toHaveBeenCalledWith(red);
  await user.click(screen.getByRole('radio', { name: 'Red only' }));
  expect(screen.getByText('1 flagged cell')).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Minimum observations'), '10');
  expect(screen.getByText(/No flagged cells match/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Refresh GNSS' }));
  expect(refresh).toHaveBeenCalledOnce();
  expect(screen.getByText(/cannot confirm jamming or spoofing/)).toBeInTheDocument();
  await user.click(screen.getByText('Source and interpretation'));
  expect(screen.getByText(/not unique aircraft/)).toBeVisible();
});

it('bounds the cell list and prevents locating while another tool owns map picking', async () => {
  const user = userEvent.setup();
  const cells = Array.from({ length: 41 }, (_, i) => ({ ...red, lon: i }));
  const view = render(<Panel cells={cells} />);
  expect(screen.getAllByRole('button', { name: /Locate GNSS/ })).toHaveLength(20);
  await user.click(screen.getByRole('button', { name: 'Next' }));
  expect(screen.getByText('2 / 3')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Previous' }));
  view.rerender(<Panel cells={cells} selectionDisabled />);
  expect(
    screen
      .getAllByRole('button', { name: /Locate GNSS/ })
      .every((button) => button.hasAttribute('disabled')),
  ).toBe(true);
});

it('distinguishes disabled, loading, failed, limited and expired cached snapshots', () => {
  const view = render(<Panel enabled={false} />);
  expect(screen.getByText(/GNSS is off/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Refresh GNSS' })).not.toBeInTheDocument();
  view.rerender(<Panel loading />);
  expect(screen.getByRole('button', { name: 'Refresh GNSS' })).toBeDisabled();
  view.rerender(<Panel error="Unavailable" now={RECEIVED + 6 * 60_000} limited />);
  expect(screen.getByRole('alert')).toHaveTextContent('last successful snapshot');
  expect(screen.getByText(/cached snapshot is out of date/)).toBeInTheDocument();
  expect(screen.getByText(/GNSS memory limit was reached/)).toBeInTheDocument();
  view.rerender(<Panel now={RECEIVED + 15 * 60_000} />);
  expect(screen.getByText(/Cached cells are hidden/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Locate GNSS/ })).not.toBeInTheDocument();
});

it('keeps appearance controls together and explains the reduced graphics override', async () => {
  const user = userEvent.setup();
  const day = vi.fn();
  const lite = vi.fn();
  render(<MapDisplaySettings terminator lite onToggleTerminator={day} onToggleLite={lite} />);
  await user.click(screen.getByRole('switch', { name: 'Day and night' }));
  await user.click(screen.getByRole('switch', { name: 'Reduce graphics load' }));
  expect(day).toHaveBeenCalledOnce();
  expect(lite).toHaveBeenCalledOnce();
  expect(screen.getByRole('status')).toHaveTextContent('paused while reduced graphics is enabled');
});

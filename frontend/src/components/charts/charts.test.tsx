import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { BarList } from './BarList';
import { ShareBar } from './ShareBar';
import { Sparkline } from './Sparkline';
import { StackedColumns } from './StackedColumns';
import { formatCount } from './chartSlots';

describe('chart primitives', () => {
  it('renders a stacked column chart with a legend, hover titles and a table twin', async () => {
    const user = userEvent.setup();
    render(
      <StackedColumns
        days={['2026-09-11', '2026-09-12']}
        series={[
          { key: 'a', label: 'Advisories', slot: 1, values: [1, 2] },
          { key: 'b', label: 'Claims', slot: 2, values: [0, 3] },
        ]}
        label="Daily volume"
      />,
    );
    const chart = screen.getByRole('img', { name: 'Daily volume' });
    expect(chart).toBeVisible();
    expect(
      within(chart).getByText('2026-09-12: 5 records (Advisories 2, Claims 3)'),
    ).toBeInTheDocument();
    // The legend and the table twin both name the series; the legend is the visible one.
    expect(screen.getAllByText('Advisories')[0]).toBeVisible();
    await user.click(screen.getByText('Table view'));
    const table = screen.getByRole('table', { name: 'Daily volume, as a table' });
    expect(within(table).getAllByRole('row')).toHaveLength(3);
  });

  it('lists bars with values at the tip and forwards selection', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <BarList
        rows={[
          { key: 'GB', label: 'United Kingdom', value: 12000, note: 'NATO member' },
          { key: 'UA', label: 'Ukraine', value: 3 },
        ]}
        label="Countries"
        onSelect={onSelect}
      />,
    );
    expect(screen.getByText('12K')).toBeVisible();
    await user.click(screen.getByRole('button', { name: /Ukraine/ }));
    expect(onSelect).toHaveBeenCalledWith('UA');
    expect(formatCount(999)).toBe('999');
  });

  it('shows empty states instead of empty marks', () => {
    render(<BarList rows={[]} label="Empty" emptyText="Nothing yet." />);
    expect(screen.getByText('Nothing yet.')).toBeVisible();
    render(<ShareBar parts={[{ key: 'a', label: 'A', value: 0, slot: 1 }]} label="Share" />);
    expect(screen.getByText(/No records to apportion/)).toBeVisible();
  });

  it('apportions a share bar and draws a sparkline for the series', () => {
    render(
      <ShareBar
        parts={[
          { key: 'a', label: 'A', value: 3, slot: 1 },
          { key: 'b', label: 'B', value: 1, slot: 2 },
        ]}
        label="Share"
      />,
    );
    expect(screen.getByRole('img', { name: 'Share' })).toHaveAttribute('title', 'A 3, B 1');
    expect(screen.getByText('3 · 75%')).toBeVisible();
    render(<Sparkline values={[0, 2, 1]} label="Trend" />);
    expect(screen.getByRole('img', { name: 'Trend' })).toBeVisible();
  });
});

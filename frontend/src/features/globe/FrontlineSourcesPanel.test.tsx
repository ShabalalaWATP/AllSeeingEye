import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { ConflictOverviewPanel } from './ConflictOverviewPanel';
import { useConflictFilters } from './useConflictFilters';
import { useConflictRegions } from './useConflictRegions';

it('opens frontline access options without claiming a connected layer or losing report filters', () => {
  function Harness() {
    const reports = useConflictFilters([]);
    const regions = useConflictRegions(false, null);
    return <ConflictOverviewPanel regions={regions} reports={reports} onSelect={vi.fn()} />;
  }
  render(<Harness />);
  fireEvent.click(screen.getByRole('button', { name: 'Report filters' }));
  fireEvent.change(screen.getByRole('searchbox', { name: 'Search loaded reports' }), {
    target: { value: 'Kharkiv' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Frontlines' }));
  const panel = within(screen.getByRole('region', { name: 'Frontline data sources' }));
  expect(panel.getByText(/No boundary feed is connected/)).toBeInTheDocument();
  expect(panel.queryByRole('switch')).not.toBeInTheDocument();
  expect(panel.queryByRole('checkbox')).not.toBeInTheDocument();
  expect(panel.getByText('Humanitarian use only')).toBeInTheDocument();
  expect(panel.getByText(/ASE_UKRAINE_DEEPSTATE_ACCESS/)).toBeInTheDocument();
  for (const link of panel.getAllByRole('link')) {
    expect(link.getAttribute('href')).toMatch(/^https:\/\//);
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  }
  fireEvent.click(screen.getByRole('button', { name: 'Report filters' }));
  expect(screen.getByRole('searchbox', { name: 'Search loaded reports' })).toHaveValue('Kharkiv');
  fireEvent.click(screen.getByRole('button', { name: 'Region overview' }));
  expect(screen.getByRole('checkbox', { name: 'Show regional overview markers' })).toBeChecked();
});

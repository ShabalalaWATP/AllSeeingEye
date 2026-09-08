import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { MapDetailsInspector } from './MapDetailsInspector';
it('resolves current GNSS observations and explicitly reports a removed cell', () => {
  const cell = {
    lon: 1,
    lat: 2,
    size: 1,
    good: 8,
    bad: 2,
    percent_bad: 10,
    level: 'amber' as const,
  };
  const props = {
    details: { kind: 'jam' as const, cell },
    cells: [cell],
    events: [],
    updatedAt: null,
    onSelect: vi.fn(),
    onClose: vi.fn(),
  };
  const { rerender } = render(<MapDetailsInspector {...props} />);
  expect(screen.getByText('2 poor; 8 good')).toBeVisible();
  expect(screen.getByText('Adjusted poor-accuracy share')).toBeVisible();
  rerender(
    <MapDetailsInspector
      {...props}
      cells={[{ ...cell, bad: 5, percent_bad: 30.8 }]}
      updatedAt="2026-09-08T12:00:00Z"
    />,
  );
  expect(screen.getByText('5 poor; 8 good')).toBeVisible();
  expect(screen.queryByText('2 poor; 8 good')).not.toBeInTheDocument();
  rerender(<MapDetailsInspector {...props} cells={[]} updatedAt="2026-09-08T13:00:00Z" />);
  expect(screen.getByRole('status')).toHaveTextContent('no longer flagged');
  expect(screen.queryByText('5 poor; 8 good')).not.toBeInTheDocument();
});

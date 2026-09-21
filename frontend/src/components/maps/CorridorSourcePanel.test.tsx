import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { CorridorSourcePanel } from './CorridorSourcePanel';

vi.mock('./CorridorResearchPanel', () => ({
  CorridorResearchPanel: ({ points }: { points: number[][] }) => (
    <output>{JSON.stringify(points)}</output>
  ),
}));
it('selects a newly calculated route over an old drawing, and allows an explicit source choice', () => {
  const drawing = {
    id: 'drawing:1',
    label: 'Drawing: Coast path',
    points: [
      [0, 0],
      [1, 1],
    ] as [number, number][],
  };
  const route = {
    id: 'route',
    label: 'Calculated route',
    points: [
      [2, 2],
      [3, 3],
    ] as [number, number][],
  };
  const { rerender } = render(<CorridorSourcePanel sources={[drawing]} onResearchArea={vi.fn()} />);
  expect(screen.getByRole('combobox', { name: 'Corridor path source' })).toHaveValue(drawing.id);
  rerender(<CorridorSourcePanel sources={[route, drawing]} onResearchArea={vi.fn()} />);
  expect(screen.getByRole('combobox', { name: 'Corridor path source' })).toHaveValue('route');
  expect(screen.getByRole('status')).toHaveTextContent(JSON.stringify(route.points));
  fireEvent.change(screen.getByRole('combobox'), { target: { value: drawing.id } });
  expect(screen.getByRole('status')).toHaveTextContent(JSON.stringify(drawing.points));
  rerender(
    <CorridorSourcePanel
      sources={[
        {
          ...route,
          points: [
            [4, 4],
            [5, 5],
          ],
        },
        drawing,
      ]}
      onResearchArea={vi.fn()}
    />,
  );
  expect(screen.getByRole('combobox')).toHaveValue('route');
});
it('falls back safely when a chosen source disappears and explains the empty state', () => {
  const source = {
    id: 'sketch',
    label: 'Current sketch',
    points: [
      [0, 0],
      [1, 1],
    ] as [number, number][],
  };
  const { rerender } = render(<CorridorSourcePanel sources={[source]} onResearchArea={vi.fn()} />);
  rerender(<CorridorSourcePanel sources={[]} onResearchArea={vi.fn()} />);
  expect(screen.getByText(/Draw or measure a path/)).toBeInTheDocument();
  expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
});

import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { newDrawingObject } from '@/lib/map/drawingCollection';
import { DrawingCoordinateEditor } from './DrawingCoordinateEditor';

it('validates coordinate edits before applying one operation and inserts/removes vertices', () => {
  const apply = vi.fn();
  render(
    <DrawingCoordinateEditor
      object={newDrawingObject(
        'path',
        [
          [0, 0],
          [1, 1],
        ],
        0,
      )}
      onApply={apply}
    />,
  );
  fireEvent.click(screen.getByText('Edit coordinates'));
  fireEvent.change(screen.getByLabelText('Longitude 1'), { target: { value: '181' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply coordinates' }));
  expect(apply).not.toHaveBeenCalled();
  expect(screen.getByRole('alert')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Longitude 1'), { target: { value: '-2' } });
  fireEvent.click(screen.getByRole('button', { name: 'Insert vertex after 1' }));
  fireEvent.change(screen.getByLabelText('Longitude 2'), { target: { value: '0.5' } });
  fireEvent.click(screen.getByRole('button', { name: 'Apply coordinates' }));
  expect(apply).toHaveBeenLastCalledWith([
    [-2, 0],
    [0.5, 0],
    [1, 1],
  ]);
  fireEvent.click(screen.getByRole('button', { name: 'Remove vertex 2' }));
  expect(screen.queryByLabelText('Longitude 3')).not.toBeInTheDocument();
});
it('accepts a bounded numeric circle radius and disables edits on locked objects', () => {
  const apply = vi.fn();
  const object = newDrawingObject(
    'circle',
    [
      [0, 0],
      [1, 0],
    ],
    0,
  );
  const { rerender } = render(<DrawingCoordinateEditor object={object} onApply={apply} />);
  fireEvent.click(screen.getByText('Edit coordinates'));
  fireEvent.change(screen.getByLabelText('Circle radius in kilometres'), {
    target: { value: '1001' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Apply coordinates' }));
  expect(apply).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Circle radius in kilometres'), {
    target: { value: '10' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Apply coordinates' }));
  expect(apply).toHaveBeenCalledOnce();
  rerender(<DrawingCoordinateEditor object={{ ...object, locked: true }} onApply={apply} />);
  expect(screen.getByRole('button', { name: 'Apply coordinates' })).toBeDisabled();
});

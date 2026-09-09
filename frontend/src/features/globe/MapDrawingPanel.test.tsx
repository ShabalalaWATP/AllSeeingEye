import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { MapDrawingPanel } from './MapDrawingPanel';
import { useMapDrawing } from './useMapDrawing';
import type { CursorHandler } from '@/lib/map/MapEngine';

it('draws a bounded two-click circle, stops collecting, then undoes and clears it', () => {
  let click: CursorHandler = () => undefined;
  const off = vi.fn();
  const engine = {
    onClick: (handler: CursorHandler) => {
      click = handler;
      return off;
    },
  };
  function Harness() {
    const drawing = useMapDrawing(engine, true);
    return (
      <>
        <MapDrawingPanel value={drawing} />
        <output aria-label="Vertex count">{drawing.points.length}</output>
      </>
    );
  }
  const { unmount } = render(<Harness />);
  fireEvent.click(screen.getByRole('button', { name: 'Radius circle' }));
  fireEvent.click(screen.getByRole('button', { name: 'Draw with map clicks' }));
  act(() => click({ lon: 0, lat: 0 }));
  act(() => click({ lon: 0.1, lat: 0 }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('32');
  expect(screen.getByRole('button', { name: 'Shape complete' })).toBeDisabled();
  act(() => click({ lon: 1, lat: 1 }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('32');
  fireEvent.click(screen.getByRole('button', { name: 'Undo point' }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('1');
  fireEvent.click(screen.getByRole('button', { name: 'Clear drawing' }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('0');
  unmount();
  expect(off).toHaveBeenCalled();
});

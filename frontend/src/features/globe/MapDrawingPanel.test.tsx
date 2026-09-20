import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { MapDrawingPanel } from './MapDrawingPanel';
import { useMapDrawing } from './useMapDrawing';
import type { CursorHandler } from '@/lib/map/MapEngine';
import type { SketchDrag, SketchDragHandler } from '@/lib/map/MapEngine';
import { MemoryRouter } from 'react-router';
import { useAuthStore } from '@/stores/auth';
import { plainUser, tokenFor } from '@/test/fixtures';
import { readAreaWatchDraft } from '@/lib/areaWatchDraft';

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
  const { unmount } = render(
    <MemoryRouter>
      <Harness />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByRole('button', { name: 'Radius circle' }));
  fireEvent.click(screen.getByRole('button', { name: 'Draw with map clicks' }));
  act(() => click({ lon: 0, lat: 0 }));
  act(() => click({ lon: 0.1, lat: 0 }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('32');
  expect(screen.getByRole('button', { name: 'Shape complete' })).toBeDisabled();
  act(() => click({ lon: 1, lat: 1 }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('32');
  fireEvent.click(screen.getByRole('button', { name: 'Undo sketch' }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('1');
  fireEvent.click(screen.getByRole('button', { name: 'Clear drawing' }));
  expect(screen.getByLabelText('Vertex count')).toHaveTextContent('0');
  unmount();
  expect(off).toHaveBeenCalled();
});

it('offers drag creation, moving existing geometry, cancellation and the click alternative', () => {
  const handlers = new Set<SketchDragHandler>();
  const engine = {
    onClick: () => () => undefined,
    onDrag: (handler: SketchDragHandler) => {
      handlers.add(handler);
      return () => {
        handlers.delete(handler);
      };
    },
    getZoom: () => 10,
  };
  function Harness() {
    const drawing = useMapDrawing(engine, true);
    return (
      <>
        <MapDrawingPanel value={drawing} />
        <output aria-label="Saved anchors">{JSON.stringify(drawing.anchors)}</output>
        <output aria-label="Preview anchors">{JSON.stringify(drawing.displayedAnchors)}</output>
      </>
    );
  }
  const { unmount } = render(
    <MemoryRouter>
      <Harness />
    </MemoryRouter>,
  );
  const emit = (phase: SketchDrag['phase'], lon: number, lat: number) =>
    act(() => {
      for (const handler of handlers)
        handler({ phase, start: { lon: 1, lat: 1 }, current: { lon, lat } });
    });
  fireEvent.click(screen.getByRole('button', { name: 'Rectangle' }));
  expect(screen.getByRole('button', { name: 'Drag shape' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  fireEvent.click(screen.getByRole('button', { name: 'Drag to draw shape' }));
  emit('start', 1, 1);
  emit('move', 3, 3);
  expect(screen.getByLabelText('Saved anchors')).toHaveTextContent('[]');
  expect(screen.getByLabelText('Preview anchors')).toHaveTextContent('[[1,1],[3,3]]');
  emit('end', 4, 4);
  expect(screen.getByLabelText('Saved anchors')).toHaveTextContent('[[1,1],[4,4]]');
  fireEvent.click(screen.getByRole('button', { name: 'Move sketch' }));
  emit('start', 1, 1);
  emit('move', 2, 3);
  emit('cancel', 2, 3);
  expect(screen.getByLabelText('Saved anchors')).toHaveTextContent('[[1,1],[4,4]]');
  emit('start', 1, 1);
  emit('end', 2, 3);
  expect(screen.getByLabelText('Saved anchors')).toHaveTextContent('[[2,3],[5,6]]');
  fireEvent.click(screen.getByRole('button', { name: 'Click points' }));
  expect(screen.getByRole('button', { name: 'Shape complete' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Clear drawing' }));
  expect(screen.getByRole('button', { name: 'Draw with map clicks' })).toBeEnabled();
  unmount();
  expect(handlers.size).toBe(0);
});

it('only hands completed area sketches to the editable Warning draft', () => {
  useAuthStore.getState().setSession(tokenFor(plainUser));
  let click: CursorHandler = () => undefined;
  const engine = {
    onClick: (handler: CursorHandler) => {
      click = handler;
      return () => undefined;
    },
  };
  function Harness() {
    return <MapDrawingPanel value={useMapDrawing(engine, true)} />;
  }
  render(
    <MemoryRouter>
      <Harness />
    </MemoryRouter>,
  );
  const watch = screen.getByRole('button', { name: 'Watch this area' });
  expect(watch).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Draw with map clicks' }));
  act(() => click({ lon: 0, lat: 0 }));
  act(() => click({ lon: 1, lat: 0 }));
  act(() => click({ lon: 1, lat: 1 }));
  expect(watch).toBeDisabled();
  expect(readAreaWatchDraft()).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Finish drawing' }));
  expect(watch).toBeEnabled();
  fireEvent.click(watch);
  expect(readAreaWatchDraft()?.source).toBe('shape');
  expect(readAreaWatchDraft()?.geometry?.features[0]?.geometry.type).toBe('Polygon');
  expect(readAreaWatchDraft()?.bounds.west).toBeLessThan(0);
  fireEvent.click(screen.getByRole('button', { name: 'Path' }));
  expect(watch).toBeDisabled();
});

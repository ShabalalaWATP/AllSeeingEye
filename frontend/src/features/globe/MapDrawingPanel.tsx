import { DRAWING_SHAPES } from '@/lib/map/drawingGeometry';
import type { DrawingShape } from '@/lib/map/drawingGeometry';
import type { MapDrawing } from './useMapDrawing';
import { useMemo } from 'react';
import { WatchAreaButton } from '@/components/maps/WatchAreaButton';
import { drawingWatchArea } from '@/lib/map/areaWatchGeometry';

const icons: Record<DrawingShape, string> = {
  path: 'M3 18 9 5l6 10 6-12M2 18h2M8 5h2M14 15h2M20 3h2',
  polygon: 'M4 6 17 3l4 13-13 5L4 6Z',
  rectangle: 'M3 5h18v14H3Z',
  circle: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 12h9',
};

export function MapDrawingPanel({ value }: { value: MapDrawing }) {
  const watch = useMemo(() => {
    // Envelope calculations run once a sketch is finished, never on live drag/click frames.
    if (value.picking) return { area: null, error: 'Finish drawing before watching this area.' };
    try {
      return { area: drawingWatchArea(value.shape, value.anchors), error: null };
    } catch (failure) {
      return {
        area: null,
        error: failure instanceof Error ? failure.message : 'Finish a valid area sketch.',
      };
    }
  }, [value.shape, value.anchors, value.picking]);
  const twoPoint = value.shape === 'rectangle' || value.shape === 'circle';
  const complete = value.anchors.length >= (twoPoint ? 2 : 32);
  const moving = value.interaction === 'move';
  const dragging = value.interaction === 'drag';
  const instruction = moving
    ? 'Press inside the shape or near its line, drag it to a new position, then release. Escape cancels the move.'
    : dragging
      ? value.shape === 'circle'
        ? 'Press at the centre, drag out the radius, then release. Escape cancels this drag.'
        : 'Press at one corner, drag to the opposite corner, then release. Escape cancels this drag.'
      : DRAWING_SHAPES.find((item) => item.value === value.shape)?.instruction;
  const cannotStart = !value.canPick || (value.interaction === 'click' && complete);
  const action = value.picking
    ? moving
      ? 'Finish moving'
      : 'Finish drawing'
    : moving
      ? 'Drag sketch to move'
      : dragging
        ? complete
          ? 'Draw replacement shape'
          : 'Drag to draw shape'
        : complete
          ? 'Shape complete'
          : 'Draw with map clicks';
  return (
    <section aria-label="Map drawing tools" className="space-y-3 text-xs">
      <header>
        <h2 className="font-mono uppercase tracking-widest text-cyan">Draw on map</h2>
        <p className="mt-1 text-muted">Sketch an area or trace a path. Your drawing stays local.</p>
      </header>
      <div className="grid grid-cols-2 gap-2" role="group" aria-label="Drawing shape">
        {DRAWING_SHAPES.map((item) => (
          <button
            key={item.value}
            type="button"
            aria-pressed={value.shape === item.value}
            onClick={() => value.setShape(item.value)}
            className="flex min-h-14 items-center gap-3 rounded border border-line bg-ground px-3 text-left hover:bg-surface-2 aria-pressed:border-cyan aria-pressed:bg-cyan/10 aria-pressed:text-cyan"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="size-6 shrink-0"
            >
              <path d={icons[item.value]} />
            </svg>
            {item.label}
          </button>
        ))}
      </div>
      {twoPoint && value.canDrag && (
        <div role="group" aria-label="Drawing input" className="flex gap-2">
          <button
            type="button"
            aria-pressed={dragging}
            onClick={() => value.setInteraction('drag')}
            className="min-h-9 flex-1 rounded border border-line px-2 aria-pressed:border-cyan aria-pressed:text-cyan"
          >
            Drag shape
          </button>
          <button
            type="button"
            aria-pressed={value.interaction === 'click'}
            onClick={() => value.setInteraction('click')}
            className="min-h-9 flex-1 rounded border border-line px-2 aria-pressed:border-cyan aria-pressed:text-cyan"
          >
            Click points
          </button>
        </div>
      )}
      <div className="rounded border border-line bg-ground p-3">
        <p className="mb-3 leading-relaxed">{instruction}</p>
        <button
          type="button"
          disabled={cannotStart}
          aria-pressed={value.picking}
          onClick={() => value.setPicking(!value.picking)}
          className="min-h-11 w-full rounded border border-cyan bg-cyan/10 px-3 font-medium text-cyan hover:bg-cyan/20 disabled:opacity-50"
        >
          {action}
        </button>
        {value.picking && (
          <p role="status" className="mt-2 text-cyan">
            Drawing active. Keep this panel open; closing it stops drawing.
          </p>
        )}
      </div>
      <output
        aria-label="Drawing measurement"
        className="block rounded border border-line bg-ground p-3 font-mono text-cyan"
      >
        {value.result}
      </output>
      {value.error && (
        <p role="alert" className="text-amber-300">
          {value.error}
        </p>
      )}
      {value.canDrag && (
        <button
          type="button"
          disabled={!value.canPick || value.anchors.length < 2}
          aria-pressed={moving}
          onClick={() => {
            value.setInteraction('move');
            value.setPicking(true);
          }}
          className="min-h-10 w-full rounded border border-line px-3 aria-pressed:border-cyan aria-pressed:text-cyan disabled:opacity-50"
        >
          Move sketch
        </button>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!value.anchors.length}
          onClick={value.undo}
          className="min-h-9 flex-1 rounded border border-line px-3 disabled:opacity-50"
        >
          Undo point
        </button>
        <button
          type="button"
          onClick={value.clear}
          className="min-h-9 flex-1 rounded border border-line px-3"
        >
          Clear drawing
        </button>
      </div>
      <WatchAreaButton
        area={watch.area}
        disabled={value.picking}
        hint={
          value.picking
            ? 'Finish drawing or moving before preparing an area indicator.'
            : (watch.error ??
              'Watch an approximate bounding rectangle around this sketch, including its curved edges and areas outside the shape. Review the bounds in Warning before adding an indicator.')
        }
      />
      <details className="text-muted">
        <summary className="cursor-pointer py-1">How drawings and measurements work</summary>
        <p className="mt-2 leading-relaxed">
          One sketch, cleared when you leave this page. Selecting another shape replaces it.
          Dragging a replacement keeps the old sketch until release. WGS84 surface measurements
          exclude terrain and altitude. Circles have a maximum 1,000 km radius and use 32 perimeter
          vertices. Other shapes retain their longitude/latitude offsets when moved, so their
          measured size can change with latitude. Polygon crossings cancel in the net area;
          rectangles use the shorter dateline crossing.
        </p>
      </details>
    </section>
  );
}

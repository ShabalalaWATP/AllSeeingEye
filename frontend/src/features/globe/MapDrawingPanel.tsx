import { DRAWING_SHAPES } from '@/lib/map/drawingGeometry';
import type { DrawingShape } from '@/lib/map/drawingGeometry';
import type { MapDrawing } from './useMapDrawing';
import { useMemo } from 'react';
import { WatchAreaButton } from '@/components/maps/WatchAreaButton';
import { drawingWatchArea } from '@/lib/map/areaWatchGeometry';
import { MapToolIntro } from '@/components/maps/MapToolIntro';

const icons: Record<DrawingShape, string> = {
  path: 'M3 18 9 6l6 10 6-12',
  polygon: 'M4 6 17 3l4 13-13 5L4 6Z',
  rectangle: 'M4 5h16v14H4Z',
  circle: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 12h9',
};
const iconPoints: Record<DrawingShape, readonly (readonly [number, number])[]> = {
  path: [
    [3, 18],
    [9, 6],
    [15, 16],
    [21, 4],
  ],
  polygon: [
    [4, 6],
    [17, 3],
    [21, 16],
    [8, 21],
  ],
  rectangle: [
    [4, 5],
    [20, 19],
  ],
  circle: [
    [12, 12],
    [21, 12],
  ],
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
    <section aria-label="Map drawing tools" className="map-tool-workspace">
      <MapToolIntro
        title="Draw on map"
        description="Sketch an area or trace a path. Your drawing stays local."
        status={value.picking ? (moving ? 'Moving sketch' : 'Drawing active') : 'Ready'}
        statusActive={value.picking}
      />
      <div className="map-tool-choice-grid" role="group" aria-label="Drawing shape">
        {DRAWING_SHAPES.map((item) => (
          <button
            key={item.value}
            type="button"
            aria-pressed={value.shape === item.value}
            onClick={() => value.setShape(item.value)}
            className="map-tool-choice"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="size-6 shrink-0"
            >
              <path d={icons[item.value]} />
              {iconPoints[item.value].map(([x, y], index) => (
                <circle key={index} cx={x} cy={y} r="1.5" fill="currentColor" stroke="none" />
              ))}
            </svg>
            {item.label}
          </button>
        ))}
      </div>
      {twoPoint && value.canDrag && (
        <div role="group" aria-label="Drawing input" className="map-tool-choice-grid">
          <button
            type="button"
            aria-pressed={dragging}
            onClick={() => value.setInteraction('drag')}
            className="map-tool-choice"
          >
            Drag shape
          </button>
          <button
            type="button"
            aria-pressed={value.interaction === 'click'}
            onClick={() => value.setInteraction('click')}
            className="map-tool-choice"
          >
            Click points
          </button>
        </div>
      )}
      <div className="map-tool-section">
        <p className="map-tool-help">{instruction}</p>
        <button
          type="button"
          disabled={cannotStart}
          aria-pressed={value.picking}
          onClick={() => value.setPicking(!value.picking)}
          className="map-tool-primary w-full"
        >
          {action}
        </button>
        {value.picking && (
          <p role="status" className="map-tool-notice">
            {moving ? 'Moving' : 'Drawing'} active. Keep this panel open; closing it stops drawing.
          </p>
        )}
      </div>
      <output aria-label="Drawing measurement" className="map-tool-result font-mono text-base">
        {value.result}
      </output>
      {value.error && (
        <p role="alert" className="map-tool-notice">
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
          className="map-tool-secondary w-full"
        >
          Move sketch
        </button>
      )}
      <div className="map-tool-actions">
        <button
          type="button"
          disabled={!value.anchors.length}
          onClick={value.undo}
          className="map-tool-secondary"
        >
          Undo point
        </button>
        <button type="button" onClick={value.clear} className="map-tool-text-button">
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
      <details className="map-tool-disclosure">
        <summary>How drawings and measurements work</summary>
        <p className="map-tool-help">
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

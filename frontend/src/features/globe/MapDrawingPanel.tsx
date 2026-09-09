import { DRAWING_SHAPES } from '@/lib/map/drawingGeometry';
import type { MapDrawing } from './useMapDrawing';

export function MapDrawingPanel({ value }: { value: MapDrawing }) {
  const choice = DRAWING_SHAPES.find((item) => item.value === value.shape);
  const complete =
    value.shape === 'rectangle' || value.shape === 'circle'
      ? value.anchors.length >= 2
      : value.anchors.length >= 32;
  return (
    <section aria-label="Map drawing tools" className="space-y-3 text-xs">
      <h2 className="font-mono uppercase tracking-widest text-cyan">Draw on map</h2>
      <div className="grid grid-cols-2 gap-2">
        {DRAWING_SHAPES.map((item) => (
          <button
            key={item.value}
            type="button"
            aria-pressed={value.shape === item.value}
            onClick={() => value.setShape(item.value)}
            className="min-h-10 rounded border border-line px-2 aria-pressed:border-cyan aria-pressed:text-cyan"
          >
            {item.label}
          </button>
        ))}
      </div>
      <p>{choice?.instruction}</p>
      <button
        type="button"
        disabled={!value.canPick || complete}
        aria-pressed={value.picking}
        onClick={() => value.setPicking(!value.picking)}
        className="min-h-10 w-full rounded border border-line px-2 text-cyan disabled:opacity-50"
      >
        {value.picking ? 'Finish drawing' : complete ? 'Shape complete' : 'Draw with map clicks'}
      </button>
      <p className="text-muted">
        Keep this panel open and click the map to place points. Closing stops drawing.
      </p>
      <output aria-label="Drawing measurement" className="block font-mono text-cyan">
        {value.result}
      </output>
      {value.error && (
        <p role="alert" className="text-amber-300">
          {value.error}
        </p>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!value.anchors.length}
          onClick={value.undo}
          className="min-h-9 rounded border border-line px-3 disabled:opacity-50"
        >
          Undo point
        </button>
        <button
          type="button"
          onClick={value.clear}
          className="min-h-9 rounded border border-line px-3"
        >
          Clear drawing
        </button>
      </div>
      <p className="text-muted">
        One local sketch, cleared when you leave this page. WGS84 surface paths exclude terrain and
        altitude. Circles use 32 vertices, so their displayed area and perimeter are approximations.
        Polygon crossings cancel in the net area; rectangles use the shorter dateline crossing.
      </p>
    </section>
  );
}

import type { MapDrawing } from './useMapDrawing';

const shapes = [
  { value: 'polygon', label: 'Polygon', path: 'M4 6 17 3l4 13-13 5L4 6Z' },
  { value: 'rectangle', label: 'Rectangle', path: 'M4 5h16v14H4Z' },
  { value: 'circle', label: 'Circle', path: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 12h9' },
] as const;

export function MapResearchDrawingControls({ value }: { value: MapDrawing }) {
  const twoPoint = value.shape === 'rectangle' || value.shape === 'circle';
  const complete = value.anchors.length >= (twoPoint ? 2 : 32);
  const moving = value.interaction === 'move';
  return (
    <section className="map-tool-section" aria-label="Research boundary">
      <div className="map-tool-choice-grid" role="group" aria-label="Research area shape">
        {shapes.map((shape) => (
          <button
            key={shape.value}
            type="button"
            className="map-tool-choice flex-col"
            aria-pressed={value.shape === shape.value}
            disabled={!value.canPick}
            onClick={() => {
              value.setShape(shape.value);
              value.setPicking(true);
            }}
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
              className="size-5 shrink-0"
            >
              <path d={shape.path} />
            </svg>
            {shape.label}
          </button>
        ))}
      </div>
      <p className="map-tool-help">
        {moving
          ? 'Drag inside the boundary to move the area.'
          : value.interaction === 'drag'
            ? value.shape === 'circle'
              ? 'Drag from the centre to set the radius.'
              : 'Drag between two opposite corners.'
            : twoPoint
              ? value.shape === 'circle'
                ? 'Click the centre, then the radius.'
                : 'Click two opposite corners.'
              : 'Click each corner on the map, then choose Finish boundary.'}
      </p>
      {twoPoint && value.canDrag && (
        <div className="map-tool-actions" role="group" aria-label="Research drawing input">
          {(['drag', 'click'] as const).map((interaction) => (
            <button
              key={interaction}
              type="button"
              className="map-tool-secondary"
              aria-pressed={value.interaction === interaction}
              onClick={() => {
                value.setInteraction(interaction);
                value.setPicking(true);
              }}
            >
              {interaction === 'drag' ? 'Drag area' : 'Click points'}
            </button>
          ))}
        </div>
      )}
      <button
        type="button"
        className="map-tool-primary w-full"
        disabled={!value.canPick}
        aria-pressed={value.picking}
        onClick={() => {
          if (!value.picking && value.interaction === 'click' && complete) value.clear();
          value.setPicking(!value.picking);
        }}
      >
        {value.picking
          ? 'Finish boundary'
          : moving
            ? 'Move area'
            : complete
              ? 'Redraw area'
              : 'Draw boundary'}
      </button>
      {value.anchors.length > 0 && (
        <div className="map-tool-actions">
          {value.canDrag && value.anchors.length >= (twoPoint ? 2 : 3) && (
            <button
              type="button"
              className="map-tool-secondary"
              onClick={() => {
                value.setInteraction('move');
                value.setPicking(true);
              }}
            >
              Move area
            </button>
          )}
          <button type="button" className="map-tool-text-button" onClick={value.undo}>
            Undo point
          </button>
          <button type="button" className="map-tool-text-button" onClick={value.clear}>
            Clear area
          </button>
        </div>
      )}
      {value.error && (
        <p role="alert" className="map-tool-notice">
          {value.error}
        </p>
      )}
      <p className="map-tool-help">
        Circle boundaries use 32 points, up to a 1,000 km radius. For areas crossing 180° longitude,
        choose a rectangle.
      </p>
    </section>
  );
}

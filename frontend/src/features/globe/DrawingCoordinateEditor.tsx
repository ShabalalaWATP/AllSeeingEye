import { useState } from 'react';
import { Geodesic } from 'geographiclib-geodesic';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { DrawingObject } from '@/lib/map/drawingCollection';
import { validateDrawingObject } from '@/lib/map/drawingCollection';

export function DrawingCoordinateEditor({
  object,
  onApply,
}: {
  object: DrawingObject;
  onApply: (anchors: Position[]) => void;
}) {
  const [rows, setRows] = useState(object.anchors.map(([lon, lat]) => [String(lon), String(lat)]));
  const [error, setError] = useState<string | null>(null);
  const [radius, setRadius] = useState('');
  const flexible = object.shape === 'path' || object.shape === 'polygon';
  const submit = () => {
    try {
      const anchors = rows.map((row) => {
        if (row.some((value) => !value.trim()))
          throw new Error('Enter both longitude and latitude.');
        return row.map(Number) as Position;
      });
      if (object.shape === 'circle' && radius.trim()) {
        const km = Number(radius);
        if (!Number.isFinite(km) || km <= 0 || km > 1000)
          throw new Error('Radius must be greater than zero and at most 1,000 km.');
        const centre = anchors[0];
        if (!centre) throw new Error('Enter the circle centre.');
        const edge = Geodesic.WGS84.Direct(centre[1], centre[0], 90, km * 1000);
        anchors[1] = [edge.lon2 ?? NaN, edge.lat2 ?? NaN];
      }
      onApply(validateDrawingObject({ ...object, anchors }).anchors);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Invalid coordinates.');
    }
  };
  return (
    <details className="map-tool-disclosure">
      <summary>Edit coordinates</summary>
      <p className="map-tool-help">
        WGS84 longitude, latitude in decimal degrees. Apply saves one undoable edit.
      </p>
      {rows.map((row, index) => (
        <div key={index} className="map-tool-actions">
          {(['Longitude', 'Latitude'] as const).map((label, axis) => (
            <label key={label} className="min-w-0 flex-1 text-xs">
              {label} {index + 1}
              <input
                aria-label={`${label} ${index + 1}`}
                type="number"
                step="any"
                value={row[axis]}
                disabled={object.locked}
                className="map-tool-input w-full"
                onChange={(event) =>
                  setRows((previous) =>
                    previous.map((pair, i) =>
                      i === index
                        ? pair.map((value, j) => (j === axis ? event.target.value : value))
                        : pair,
                    ),
                  )
                }
              />
            </label>
          ))}
          {flexible && (
            <button
              type="button"
              aria-label={`Remove vertex ${index + 1}`}
              disabled={object.locked || rows.length <= (object.shape === 'polygon' ? 3 : 2)}
              onClick={() => setRows((previous) => previous.filter((_, i) => i !== index))}
            >
              Remove
            </button>
          )}
          {flexible && (
            <button
              type="button"
              aria-label={`Insert vertex after ${index + 1}`}
              disabled={object.locked || rows.length >= 32}
              onClick={() =>
                setRows((previous) => [
                  ...previous.slice(0, index + 1),
                  [...row],
                  ...previous.slice(index + 1),
                ])
              }
            >
              Insert
            </button>
          )}
        </div>
      ))}
      {object.shape === 'circle' && (
        <label className="map-tool-help">
          New radius (km), optional
          <input
            aria-label="Circle radius in kilometres"
            type="number"
            min="0"
            max="1000"
            step="any"
            value={radius}
            disabled={object.locked}
            onChange={(event) => setRadius(event.target.value)}
            className="map-tool-input w-full"
          />
        </label>
      )}
      <button
        type="button"
        disabled={object.locked}
        onClick={submit}
        className="map-tool-secondary"
      >
        Apply coordinates
      </button>
      {error && <p role="alert">{error}</p>}
    </details>
  );
}

import { useState } from 'react';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { MeasurementMode } from '@/lib/map/measurements';

export interface MeasurementControls {
  points: readonly Position[];
  mode: MeasurementMode;
  setMode: (mode: MeasurementMode) => void;
  picking: boolean;
  setPicking: (picking: boolean) => void;
  error: string | null;
  result: string;
  canPick: boolean;
  add: (longitude: number, latitude: number) => void;
  undo: () => void;
  clear: () => void;
}

export function MapMeasurementPanel({
  value,
  persistenceNote = 'Local only, cleared when you leave this page.',
}: {
  value: MeasurementControls;
  persistenceNote?: string;
}) {
  const [longitude, setLongitude] = useState('');
  const [latitude, setLatitude] = useState('');
  return (
    <section
      aria-label="Map measurement"
      className="rounded-md border border-line bg-surface/90 p-3 text-xs backdrop-blur"
    >
      <h2 className="mb-2 font-mono text-[10px] uppercase tracking-widest text-cyan">Measure</h2>
      <label className="block">
        Measurement
        <select
          aria-label="Measurement type"
          value={value.mode}
          onChange={(event) => value.setMode(event.target.value === 'area' ? 'area' : 'distance')}
          className="my-2 w-full rounded border border-line bg-ground p-2"
        >
          <option value="distance">Path distance</option>
          <option value="area">Net enclosed area</option>
        </select>
      </label>
      <output
        aria-label="Measurement result"
        className="block font-mono text-cyan"
        aria-live="polite"
      >
        {value.result}
      </output>
      <button
        type="button"
        aria-pressed={value.picking}
        disabled={!value.canPick}
        onClick={() => value.setPicking(!value.picking)}
        className="my-2 min-h-11 w-full rounded border border-line p-2 hover:bg-surface-2"
      >
        {value.picking ? 'Stop picking points' : 'Pick points on map'}
      </button>
      {value.picking && (
        <p>Click empty map space. Close this tool panel to expose more of the map.</p>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          value.add(
            longitude.trim() ? Number(longitude) : NaN,
            latitude.trim() ? Number(latitude) : NaN,
          );
        }}
        className="mt-2 space-y-2"
      >
        <label className="block">
          Longitude
          <input
            value={longitude}
            onChange={(event) => setLongitude(event.target.value)}
            type="number"
            min="-180"
            max="180"
            step="any"
            required
            className="w-full rounded border border-line bg-ground p-2"
          />
        </label>
        <label className="block">
          Latitude
          <input
            value={latitude}
            onChange={(event) => setLatitude(event.target.value)}
            type="number"
            min="-90"
            max="90"
            step="any"
            required
            className="w-full rounded border border-line bg-ground p-2"
          />
        </label>
        <button
          disabled={value.points.length >= 32}
          className="min-h-11 rounded border border-line px-2 disabled:opacity-50"
        >
          Add coordinate
        </button>
      </form>
      {value.error && <p role="alert">{value.error}</p>}
      <p className="my-2">{value.points.length}/32 points</p>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={!value.points.length}
          onClick={value.undo}
          className="min-h-11 rounded border border-line px-2 disabled:opacity-50"
        >
          Undo point
        </button>
        <button
          type="button"
          onClick={value.clear}
          className="min-h-11 rounded border border-line px-2"
        >
          Clear measure
        </button>
      </div>
      <details className="mt-2">
        <summary>Coordinates</summary>
        <ol>
          {value.points.map(([lon, lat], index) => (
            <li key={index}>
              {index + 1}: {lon.toFixed(5)}, {lat.toFixed(5)}
            </li>
          ))}
        </ol>
      </details>
      <p className="mt-2 text-[10px] text-muted">
        WGS84 surface measurement, excluding terrain and altitude. Area closes the last point to the
        first; crossing edges cancel. Shortest paths are used. {persistenceNote} Flat maps omit
        paths above 85° latitude; calculations retain the original coordinates. Areas are the
        smaller net region, not shapes covering more than half the Earth. The drawn line is sampled;
        numeric results use the full geodesic calculation.
      </p>
    </section>
  );
}

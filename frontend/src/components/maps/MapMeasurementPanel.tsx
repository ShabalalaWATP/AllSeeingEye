import { useState } from 'react';
import type { Position } from '@/lib/map/geoJsonTypes';
import type { MeasurementMode } from '@/lib/map/measurements';
import { MapToolIntro } from './MapToolIntro';

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
    <section aria-label="Map measurement" className="map-tool-workspace">
      <MapToolIntro
        title="Measure"
        description="Connect points to measure a route or enclose an area."
        status={value.picking ? 'Measuring' : 'Ready'}
        statusActive={value.picking}
      />
      <div role="group" aria-label="Measurement type" className="map-tool-choice-grid">
        {(['distance', 'area'] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            aria-pressed={value.mode === mode}
            onClick={() => value.setMode(mode)}
            className="map-tool-choice"
          >
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="size-5 shrink-0"
            >
              {mode === 'distance' ? (
                <>
                  <path d="m6 18 6-12 6 12" />
                  <circle cx="5" cy="19" r="2" />
                  <circle cx="12" cy="5" r="2" />
                  <circle cx="19" cy="19" r="2" />
                </>
              ) : (
                <path d="m4 7 12-4 5 12-11 6-6-14Z" />
              )}
            </svg>
            {mode === 'distance' ? 'Distance' : 'Area'}
          </button>
        ))}
      </div>
      <p className="map-tool-help">
        {value.mode === 'distance'
          ? 'Each point extends the measured path.'
          : 'Use at least three points. The last point connects to the first.'}
      </p>
      <output
        aria-label="Measurement result"
        className="map-tool-result font-mono text-xl font-medium"
        aria-live="polite"
      >
        {value.result}
      </output>
      <button
        type="button"
        aria-pressed={value.picking}
        disabled={!value.canPick}
        onClick={() => value.setPicking(!value.picking)}
        className="map-tool-primary w-full"
      >
        {value.picking ? 'Finish measuring' : 'Pick points on map'}
      </button>
      {value.picking && (
        <p className="map-tool-notice">
          Click anywhere on the map, including markers, to add numbered points. You can close this
          panel while measuring. Enter or Escape finishes; Backspace undoes the last point.
        </p>
      )}
      <div className="map-tool-actions">
        <button
          type="button"
          disabled={!value.points.length}
          onClick={value.undo}
          className="map-tool-secondary"
        >
          Undo point
        </button>
        <button type="button" onClick={value.clear} className="map-tool-text-button">
          Clear measure
        </button>
      </div>
      <p className="map-tool-help">{value.points.length}/32 points</p>
      {value.error && (
        <p className="map-tool-notice" role="alert">
          {value.error}
        </p>
      )}
      <details className="map-tool-disclosure">
        <summary>Enter coordinates manually</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            value.add(
              longitude.trim() ? Number(longitude) : NaN,
              latitude.trim() ? Number(latitude) : NaN,
            );
          }}
          className="space-y-3"
        >
          <p className="map-tool-help">Use decimal degrees in WGS84.</p>
          <label className="map-tool-field">
            Longitude
            <input
              value={longitude}
              onChange={(event) => setLongitude(event.target.value)}
              type="number"
              min="-180"
              max="180"
              step="any"
              required
              className="map-tool-input"
            />
          </label>
          <label className="map-tool-field">
            Latitude
            <input
              value={latitude}
              onChange={(event) => setLatitude(event.target.value)}
              type="number"
              min="-90"
              max="90"
              step="any"
              required
              className="map-tool-input"
            />
          </label>
          <button disabled={value.points.length >= 32} className="map-tool-secondary">
            Add coordinate
          </button>
        </form>
      </details>
      <details className="map-tool-disclosure">
        <summary>Coordinates</summary>
        <ol className="space-y-1 font-mono text-xs text-muted">
          {value.points.map(([lon, lat], index) => (
            <li key={index}>
              {index + 1}: {lon.toFixed(5)}, {lat.toFixed(5)}
            </li>
          ))}
        </ol>
      </details>
      <details className="map-tool-disclosure">
        <summary>Accuracy and storage</summary>
        <p className="map-tool-help">
          WGS84 surface measurement, excluding terrain and altitude. Area closes the last point to
          the first; crossing edges cancel. Shortest paths are used. {persistenceNote} Flat maps
          omit paths above 85° latitude; calculations retain the original coordinates. Areas are the
          smaller net region, not shapes covering more than half the Earth. The drawn line is
          sampled; numeric results use the full geodesic calculation.
        </p>
      </details>
    </section>
  );
}

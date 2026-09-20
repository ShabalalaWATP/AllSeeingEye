import { useState } from 'react';
import { formatDms, fromUtm, parseCoordinatePair, toUtm } from '@/lib/map/coordinateWorkbench';
import type { Position } from '@/lib/map/geoJsonTypes';

export function CoordinateWorkbench({ onNavigate }: { onNavigate: (position: Position) => void }) {
  const [format, setFormat] = useState('degrees');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [zone, setZone] = useState('30');
  const [hemisphere, setHemisphere] = useState<'N' | 'S'>('N');
  const [easting, setEasting] = useState('');
  const [northing, setNorthing] = useState('');
  const [point, setPoint] = useState<Position | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const utm = point ? toUtm(point) : null;
  const text = point ? `${point[1].toFixed(6)}, ${point[0].toFixed(6)}` : '';
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
    } catch {
      setError('Copy is unavailable. Select and copy the displayed coordinates.');
    }
  }
  function convert() {
    setCopied(false);
    setError(null);
    setPoint(null);
    try {
      if (format === 'utm' && [zone, easting, northing].some((value) => !value.trim()))
        throw new Error('Enter the zone, easting and northing.');
      const next =
        format === 'utm'
          ? fromUtm({
              zone: Number(zone),
              hemisphere,
              easting: Number(easting),
              northing: Number(northing),
            })
          : parseCoordinatePair(latitude, longitude);
      setPoint(next);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Invalid coordinate.');
    }
  }
  return (
    <section className="map-tool-workspace" aria-label="Coordinate workbench">
      <p>Convert a WGS84 location, then centre the map or copy latitude, longitude.</p>
      <label className="block">
        Input format
        <select
          className="mt-1 w-full rounded border border-white/20 bg-black p-2"
          value={format}
          onChange={(event) => {
            setFormat(event.target.value);
            setPoint(null);
          }}
        >
          <option value="degrees">Decimal degrees or DMS</option>
          <option value="utm">WGS84 UTM</option>
        </select>
      </label>
      {format === 'degrees' ? (
        <>
          <label className="block">
            Latitude
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              value={latitude}
              placeholder="51.5 or 51 30 0 N"
              maxLength={100}
              onChange={(event) => {
                setLatitude(event.target.value);
                setPoint(null);
              }}
            />
          </label>
          <label className="block">
            Longitude
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              value={longitude}
              placeholder="-0.12 or 0 7 12 W"
              maxLength={100}
              onChange={(event) => {
                setLongitude(event.target.value);
                setPoint(null);
              }}
            />
          </label>
        </>
      ) : (
        <>
          <label className="block">
            UTM zone
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              type="number"
              min="1"
              max="60"
              value={zone}
              onChange={(event) => {
                setZone(event.target.value);
                setPoint(null);
              }}
            />
          </label>
          <label className="block">
            Hemisphere
            <select
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              value={hemisphere}
              onChange={(event) => {
                setHemisphere(event.target.value as 'N' | 'S');
                setPoint(null);
              }}
            >
              <option value="N">North</option>
              <option value="S">South</option>
            </select>
          </label>
          <label className="block">
            Easting (m)
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              type="number"
              value={easting}
              onChange={(event) => {
                setEasting(event.target.value);
                setPoint(null);
              }}
            />
          </label>
          <label className="block">
            Northing (m)
            <input
              className="mt-1 w-full rounded border border-white/20 bg-black p-2"
              type="number"
              value={northing}
              onChange={(event) => {
                setNorthing(event.target.value);
                setPoint(null);
              }}
            />
          </label>
        </>
      )}
      <button type="button" className="rounded border border-cyan/50 px-3 py-2" onClick={convert}>
        Convert coordinates
      </button>
      {error && (
        <p role="alert" className="text-red-300">
          {error}
        </p>
      )}
      {point && (
        <div className="space-y-2" aria-live="polite">
          <p className="font-mono">{text}</p>
          <p>
            {formatDms(point[1], 'latitude')}
            <br />
            {formatDms(point[0], 'longitude')}
          </p>
          <p>
            {utm
              ? `UTM ${utm.zone}${utm.hemisphere} · E ${utm.easting.toFixed(1)} · N ${utm.northing.toFixed(1)} m`
              : 'UTM is unavailable outside 80°S to 84°N.'}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded border border-white/20 px-3 py-2"
              onClick={() => onNavigate(point)}
            >
              Go to location
            </button>
            <button
              type="button"
              className="rounded border border-white/20 px-3 py-2"
              onClick={() => {
                void copy();
              }}
            >
              Copy coordinates
            </button>
          </div>
          {copied && <p role="status">Coordinates copied.</p>}
        </div>
      )}
      <p className="text-muted">
        Order is latitude, longitude in this panel. GeoJSON exports use longitude, latitude.
        Displayed precision does not establish positional accuracy.
      </p>
    </section>
  );
}

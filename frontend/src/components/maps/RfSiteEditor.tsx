import { useEffect, useState } from 'react';
import { subscribeRfWorkspaceReset } from '@/lib/map/rfWorkspaceAccess';
import type { Position } from '@/lib/map/geoJsonTypes';
import { parseSiteCoordinate, type RfSiteKind } from '@/lib/map/rfSites';
export function RfSiteEditor({
  kind,
  position,
  name,
  onSet,
}: {
  kind: RfSiteKind;
  position: Position | null;
  name: string;
  onSet: (kind: RfSiteKind, point: Position, name?: string) => void;
}) {
  const [latitude, setLatitude] = useState(position ? String(position[1]) : '');
  const [longitude, setLongitude] = useState(position ? String(position[0]) : '');
  const [siteName, setName] = useState(name);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const clear = () => {
      setLatitude('');
      setLongitude('');
      setName('');
      setError(null);
    };
    return subscribeRfWorkspaceReset(clear);
  }, []);
  const label = kind === 'origin' ? 'Transmitter' : 'Receiver';
  return (
    <fieldset className="rf-field-grid">
      <legend>{label} coordinates</legend>
      <label className="rf-field">
        <span>{label} name</span>
        <input value={siteName} maxLength={80} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="rf-field">
        <span>{label} latitude</span>
        <input
          value={latitude}
          onChange={(e) => setLatitude(e.target.value)}
          placeholder="51.5 or 51°30′0″N"
        />
      </label>
      <label className="rf-field">
        <span>{label} longitude</span>
        <input
          value={longitude}
          onChange={(e) => setLongitude(e.target.value)}
          placeholder="-0.12 or 0°7′12″W"
        />
      </label>
      <button
        type="button"
        className="rf-secondary-button"
        onClick={() => {
          try {
            onSet(
              kind,
              [
                parseSiteCoordinate(longitude, 'longitude'),
                parseSiteCoordinate(latitude, 'latitude'),
              ],
              siteName.trim(),
            );
            setError(null);
          } catch (e) {
            setError(e instanceof Error ? e.message : 'Check coordinates.');
          }
        }}
      >
        Apply {label.toLowerCase()} site
      </button>
      {error && <p role="alert">{error}</p>}
    </fieldset>
  );
}

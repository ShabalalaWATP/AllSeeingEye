import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { createAoi } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import { geometryBounds } from '@/lib/map/geometryBounds';
import { validateAreaBounds } from '@/lib/map/areaGeometry';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';

/** Map research is personal. Reusable areas retain that scope and require an explicit save. */
export function SaveResearchArea({ area }: { area: LocalCollection }) {
  const [name, setName] = useState('');
  const [saved, setSaved] = useState(false);
  const bounds = useMemo(() => {
    if (area.features.length !== 1) return null;
    const feature = area.features[0];
    if (!feature) return null;
    try {
      return validateAreaBounds(geometryBounds(feature.geometry));
    } catch {
      return null;
    }
  }, [area]);
  const save = useAsyncAction(async () => {
    if (!bounds || !name.trim()) return;
    await createAoi({
      name: name.trim(),
      description: 'Enclosing bounding box saved from map research.',
      kind: 'bbox',
      bbox: [bounds.west, bounds.south, bounds.east, bounds.north],
      team_id: null,
    });
    setName('');
    setSaved(true);
  });
  if (!bounds) return null;
  return (
    <details className="mt-3 border-t border-line pt-3">
      <summary className="cursor-pointer text-xs text-ember">Save as a reusable area</summary>
      <p className="map-tool-help">
        Save the enclosing rectangle to your personal Plans & areas for subscriptions and future
        research. This includes any space outside your drawn shape within its bounds.
      </p>
      <label className="map-tool-field">
        Reusable area name
        <input
          className="map-tool-input"
          value={name}
          maxLength={120}
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <button
        type="button"
        className="map-tool-secondary mt-2"
        disabled={save.busy || !name.trim()}
        onClick={() => void save.run()}
      >
        {save.busy ? 'Saving…' : 'Save reusable area'}
      </button>
      {save.error && (
        <p role="alert" className="map-tool-notice">
          {describeError(save.error)}
        </p>
      )}
      {saved && (
        <p role="status" className="map-tool-help">
          Area saved to your personal Plans & areas.
        </p>
      )}
      <Link className="map-tool-text-button mt-2 block" to="/direction">
        View Plans & areas
      </Link>
    </details>
  );
}

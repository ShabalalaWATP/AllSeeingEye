import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import { createAoi } from '@/lib/api/direction';
import { describeError } from '@/lib/api/errors';
import { useAsyncAction } from '@/lib/hooks/useAsyncAction';
import type { LocalCollection } from '@/lib/map/geoJsonTypes';

/** Map research is personal. Reusable areas retain that scope and require an explicit save. */
export function SaveResearchArea({ area }: { area: LocalCollection }) {
  const [name, setName] = useState('');
  const [saved, setSaved] = useState<LocalCollection | null>(null);
  const geometry = useMemo(() => {
    const feature = area.features[0];
    return area.features.length === 1 &&
      feature &&
      ['Polygon', 'MultiPolygon'].includes(feature.geometry.type)
      ? area
      : null;
  }, [area]);
  const save = useAsyncAction(async () => {
    if (!geometry || !name.trim()) return;
    await createAoi({
      name: name.trim(),
      description: 'Exact boundary saved from map research.',
      kind: 'geometry',
      research_area: { geometry: { ...geometry } },
      team_id: null,
    });
    setName('');
    setSaved(geometry);
  });
  if (!geometry) return null;
  return (
    <details className="mt-3 border-t border-line pt-3">
      <summary className="cursor-pointer text-xs text-ember">Save as a reusable area</summary>
      <p className="map-tool-help">
        Save this exact boundary to your personal Plans and areas for future research. Its geometry
        and content hash are retained; it is not widened to a rectangle.
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
      {saved === geometry && (
        <p role="status" className="map-tool-help">
          Area saved to your personal Plans and areas.
        </p>
      )}
      <Link className="map-tool-text-button mt-2 block" to="/direction">
        View Plans and areas
      </Link>
    </details>
  );
}

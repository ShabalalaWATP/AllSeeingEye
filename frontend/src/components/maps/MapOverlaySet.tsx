import { useMemo, useState } from 'react';
import type { SetStateAction } from 'react';
import { Button } from '@/components/ui/Button';
import type { MapState } from '@/lib/api/mapViews';
import { LocalGeoJsonOverlay } from './LocalGeoJsonOverlay';
import { localOverlay, savedOverlay } from './savedMapState';

export function MapOverlaySet({
  overlays,
  onChange,
}: {
  overlays: MapState['overlays'];
  onChange: (value: SetStateAction<MapState['overlays']>) => void;
}) {
  const [adding, setAdding] = useState(false);
  const first = useMemo(() => (overlays[0] ? localOverlay(overlays[0]) : null), [overlays]);
  return (
    <div className="space-y-3">
      <LocalGeoJsonOverlay
        overlay={first}
        visible={overlays[0]?.visible ?? true}
        onChange={(value) =>
          onChange((previous) =>
            value
              ? [savedOverlay(value, previous[0]?.visible ?? true), ...previous.slice(1)]
              : previous.slice(1),
          )
        }
        onVisible={(visible) =>
          onChange((previous) =>
            previous.map((entry, index) => (index === 0 ? { ...entry, visible } : entry)),
          )
        }
      />
      {overlays.slice(1).map((entry, index) => (
        <div key={index} className="space-y-1 rounded border border-line p-3">
          <label className="flex gap-2 text-sm">
            <input
              type="checkbox"
              checked={entry.visible}
              onChange={(event) =>
                onChange(
                  overlays.map((value, i) =>
                    i === index + 1 ? { ...value, visible: event.target.checked } : value,
                  ),
                )
              }
            />
            Show overlay {index + 2}: {entry.source}
          </label>
          <p className="text-xs text-muted">
            {entry.dataset_date} · {entry.attribution} · {entry.precision}
          </p>
          <Button
            variant="ghost"
            onClick={() => onChange(overlays.filter((_, i) => i !== index + 1))}
          >
            Remove overlay {index + 2}
          </Button>
        </div>
      ))}
      {overlays.length > 0 && overlays.length < 8 && !adding && (
        <Button variant="ghost" onClick={() => setAdding(true)}>
          Add another local overlay
        </Button>
      )}
      {adding && (
        <fieldset className="rounded border border-line p-3">
          <legend>Additional local overlay</legend>
          <LocalGeoJsonOverlay
            overlay={null}
            visible
            onVisible={() => undefined}
            onChange={(value) => {
              if (value) {
                onChange((previous) => [...previous, savedOverlay(value, true)]);
                setAdding(false);
              }
            }}
          />
          <Button variant="ghost" onClick={() => setAdding(false)}>
            Cancel additional overlay
          </Button>
        </fieldset>
      )}
    </div>
  );
}

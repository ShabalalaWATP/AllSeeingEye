import { useState } from 'react';
import type { DrawingWorkspace } from './useDrawingWorkspace';
import type { DrawingShape } from '@/lib/map/drawingGeometry';
import type { Position } from '@/lib/map/geoJsonTypes';
import { DrawingCoordinateEditor } from './DrawingCoordinateEditor';
import { exportDrawingGeoJson } from '@/lib/map/drawingCollection';
import { workspaceRevision } from '@/lib/workspaceAccess';
import { useAuthStore } from '@/stores/auth';
import { drawingAuthority } from '@/lib/map/drawingAuthority';

export interface DrawingCollectionControlsProps {
  workspace: DrawingWorkspace;
  onResearch?: ((shape: DrawingShape, anchors: Position[]) => void) | undefined;
  onRadioSite?: ((position: Position) => void) | undefined;
}
export function DrawingCollectionControls({
  workspace: value,
  onResearch,
  onRadioSite,
}: DrawingCollectionControlsProps) {
  const [point, setPoint] = useState(['', '']);
  const [pointError, setPointError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const selected = value.selected;
  const download = () => {
    const url = URL.createObjectURL(
      new Blob([exportDrawingGeoJson(value)], { type: 'application/geo+json' }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = 'map-drawings.geojson';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };
  return (
    <section aria-label="Drawing collection" className="map-tool-section">
      <h3 className="map-tool-label">Drawing collection ({value.objects.length}/50)</h3>
      <p className="map-tool-help">
        Add a finished sketch, then save the collection to keep it between visits.
      </p>
      <div className="map-tool-actions">
        <button
          type="button"
          onClick={value.addSketch}
          disabled={!value.canAddSketch}
          className="map-tool-secondary"
        >
          Add sketch to collection
        </button>
        <button
          type="button"
          onClick={value.undo}
          disabled={!value.canUndo}
          className="map-tool-text-button"
        >
          Undo collection
        </button>
        <button
          type="button"
          onClick={value.redo}
          disabled={!value.canRedo}
          className="map-tool-text-button"
        >
          Redo collection
        </button>
      </div>
      <label className="map-tool-help">
        Selected drawing
        <select
          aria-label="Selected drawing"
          value={value.selectedId ?? ''}
          onChange={(event) => value.select(event.target.value || null)}
          className="map-tool-input w-full"
        >
          <option value="">Choose drawing</option>
          {value.objects.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
              {item.locked ? ' (locked)' : ''}
            </option>
          ))}
        </select>
      </label>
      {selected && (
        <div key={selected.id} className="map-tool-section">
          <label className="map-tool-help">
            Name
            <input
              aria-label="Drawing name"
              key={selected.name}
              maxLength={120}
              disabled={selected.locked}
              defaultValue={selected.name}
              onBlur={(event) => {
                if (event.target.value !== selected.name)
                  value.updateObject(selected.id, { name: event.target.value });
              }}
              className="map-tool-input w-full"
            />
          </label>
          <label className="map-tool-help">
            Notes
            <textarea
              aria-label="Drawing notes"
              key={selected.notes}
              maxLength={2000}
              disabled={selected.locked}
              defaultValue={selected.notes}
              onBlur={(event) => {
                if (event.target.value !== selected.notes)
                  value.updateObject(selected.id, { notes: event.target.value });
              }}
              className="map-tool-input w-full"
            />
          </label>
          <div className="map-tool-actions">
            <label>
              Colour{' '}
              <input
                aria-label="Drawing colour"
                type="color"
                value={selected.colour}
                disabled={selected.locked}
                onChange={(event) =>
                  value.updateObject(selected.id, { colour: event.target.value })
                }
              />
            </label>
            <label>
              <input
                type="checkbox"
                checked={selected.visible}
                onChange={(event) =>
                  value.updateObject(selected.id, { visible: event.target.checked })
                }
              />{' '}
              Visible
            </label>
            <label>
              <input
                type="checkbox"
                checked={selected.locked}
                onChange={(event) =>
                  value.updateObject(selected.id, { locked: event.target.checked })
                }
              />{' '}
              Locked
            </label>
          </div>
          <DrawingCoordinateEditor
            key={`${selected.id}:${JSON.stringify(selected.anchors)}`}
            object={selected}
            onApply={(anchors) => value.updateObject(selected.id, { anchors })}
          />
          <div className="map-tool-actions">
            {selected.shape !== 'point' && (
              <button
                type="button"
                disabled={selected.locked || !value.canApplySketch}
                onClick={value.applySketch}
                className="map-tool-secondary"
              >
                Apply sketch edits
              </button>
            )}
            <button
              type="button"
              onClick={() => value.duplicate(selected.id)}
              className="map-tool-secondary"
            >
              Duplicate
            </button>
            <button
              type="button"
              disabled={selected.locked}
              onClick={() => value.remove(selected.id)}
              className="map-tool-text-button"
            >
              Remove
            </button>
          </div>
          {onResearch && selected.shape !== 'point' && selected.shape !== 'path' && (
            <button
              type="button"
              onClick={() => {
                try {
                  onResearch(selected.shape as DrawingShape, selected.anchors);
                  setActionError(null);
                } catch (error) {
                  setActionError(
                    error instanceof Error ? error.message : 'Unable to research this boundary.',
                  );
                }
              }}
              className="map-tool-primary"
            >
              Research selected area
            </button>
          )}
          {onRadioSite && selected.shape === 'point' && (
            <button
              type="button"
              onClick={() => {
                const point = selected.anchors[0];
                if (point) onRadioSite(point);
              }}
              className="map-tool-secondary"
            >
              Use as radio site
            </button>
          )}
        </div>
      )}
      <details className="map-tool-disclosure">
        <summary>Add a named point</summary>
        {['Longitude', 'Latitude'].map((label, index) => (
          <label key={label} className="map-tool-help">
            {label}
            <input
              aria-label={`New point ${label.toLowerCase()}`}
              type="number"
              step="any"
              value={point[index]}
              onChange={(event) =>
                setPoint((previous) =>
                  previous.map((v, i) => (i === index ? event.target.value : v)),
                )
              }
              className="map-tool-input w-full"
            />
          </label>
        ))}
        <button
          type="button"
          className="map-tool-secondary"
          onClick={() => {
            if (point.some((v) => !v.trim())) {
              setPointError('Enter longitude and latitude.');
              return;
            }
            setPointError(null);
            value.addPoint(point.map(Number) as Position);
          }}
        >
          Add point
        </button>
        {pointError && <p role="alert">{pointError}</p>}
      </details>
      <div className="map-tool-actions">
        <button
          type="button"
          disabled={!value.objects.length}
          onClick={download}
          className="map-tool-secondary"
        >
          Export GeoJSON
        </button>
        <label className="map-tool-secondary">
          Import GeoJSON
          <input
            aria-label="Import drawing GeoJSON"
            type="file"
            accept=".json,.geojson,application/geo+json,application/json"
            className="sr-only"
            onChange={(event) => {
              void (async () => {
                const file = event.target.files?.[0];
                const revision = workspaceRevision();
                const actor = drawingAuthority(useAuthStore.getState());
                try {
                  if (file) {
                    if (file.size > 128 * 1024) value.importGeoJson(' '.repeat(128 * 1024 + 1));
                    else {
                      const text = await file.text();
                      if (
                        revision === workspaceRevision() &&
                        actor === drawingAuthority(useAuthStore.getState())
                      )
                        value.importGeoJson(text);
                    }
                  }
                } catch {
                  setPointError('Unable to read this GeoJSON file.');
                }
                event.target.value = '';
              })();
            }}
          />
        </label>
      </div>
      <p className="map-tool-help">
        Imports add up to 50 total objects, 32 vertices each. Points, lines and single-ring polygons
        only. Circles and rectangles export as polygons.
      </p>
      {value.error && <p role="alert">{value.error}</p>}
      {actionError && <p role="alert">{actionError}</p>}
    </section>
  );
}

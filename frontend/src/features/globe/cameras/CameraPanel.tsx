import type { Camera } from '@/lib/api/cameras';
import { useState } from 'react';
import type { CameraState } from './useCameras';
import { CameraSources } from './CameraSources';

export function CameraPanel({
  cameras,
  onSelect,
}: {
  cameras: CameraState;
  onSelect?: (camera: Camera) => void;
}) {
  const [page, setPage] = useState(0);
  const current = Math.min(page, Math.max(0, Math.ceil(cameras.visible.length / 50) - 1));
  return (
    <section aria-label="Public camera catalogue" className="space-y-3 text-xs">
      <button
        type="button"
        role="switch"
        aria-checked={cameras.enabled}
        onClick={() => cameras.setEnabled(!cameras.enabled)}
        className="min-h-11 w-full text-left text-cyan"
      >
        Show public cameras <span className="float-right">{cameras.enabled ? 'ON' : 'OFF'}</span>
      </button>
      <p className="text-muted">
        Worldwide public camera sources. Enable a region to load its catalogue. Snapshots, video and
        provider links are labelled separately.
      </p>
      {cameras.enabled && (
        <>
          <button
            type="button"
            disabled={cameras.loading}
            onClick={cameras.refresh}
            className="min-h-11 underline"
          >
            Refresh catalogue
          </button>
          {cameras.loading && (
            <p role="status">Loading selected sources… Completed cameras appear as they arrive.</p>
          )}
          {cameras.error && <p role="alert">{cameras.error}</p>}
          <CameraSources cameras={cameras} />
          <label className="block">
            Find a camera
            <input
              value={cameras.query}
              onChange={(event) => cameras.setQuery(event.target.value)}
              maxLength={200}
              className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2"
            />
          </label>
          <p role="status">{cameras.visible.length} cameras in enabled catalogues</p>
          <ul>
            {cameras.visible.slice(current * 50, (current + 1) * 50).map((camera) => (
              <li key={camera.id}>
                <button
                  type="button"
                  onClick={() => (onSelect ?? cameras.select)(camera)}
                  className="min-h-11 w-full border-b border-line py-2 text-left hover:text-cyan"
                >
                  {camera.title}
                </button>
              </li>
            ))}
          </ul>
          {cameras.visible.length > 50 && (
            <div className="flex justify-between gap-2">
              <button
                disabled={current === 0}
                onClick={() => setPage(current - 1)}
                className="min-h-11"
              >
                Previous cameras
              </button>
              <span>Page {current + 1}</span>
              <button
                disabled={(current + 1) * 50 >= cameras.visible.length}
                onClick={() => setPage(current + 1)}
                className="min-h-11"
              >
                Next cameras
              </button>
            </div>
          )}
          <p className="text-muted">
            Click a numbered map cluster to zoom in. Search this list to select any camera,
            including overlapping cameras.
          </p>
        </>
      )}
    </section>
  );
}

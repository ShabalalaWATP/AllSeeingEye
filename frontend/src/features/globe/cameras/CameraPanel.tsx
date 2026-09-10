import type { Camera } from '@/lib/api/cameras';
import { useState } from 'react';
import type { CameraState } from './useCameras';
import { MapControlIcon } from '../MapControlIcon';
import { CameraSources } from './CameraSources';
import { CameraMediaFilter } from './CameraMediaFilter';
import { cameraMedia } from './cameraMediaFilters';

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
    <section aria-label="Public camera catalogue" className="space-y-4 p-1 text-xs">
      <button
        type="button"
        role="switch"
        aria-label="Show public cameras"
        aria-checked={cameras.enabled}
        onClick={() => cameras.setEnabled(!cameras.enabled)}
        className="flex min-h-16 w-full items-center gap-3 rounded-lg border border-line px-3 py-3 text-left hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-cyan"
      >
        <span className="text-cyan">
          <MapControlIcon name="camera" />
        </span>
        <span className="flex-1 text-sm font-medium">Show public cameras</span>
        <span
          aria-hidden="true"
          className={`flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 ${cameras.enabled ? 'bg-cyan/70' : 'bg-white/15'}`}
        >
          <span
            className={`h-4 w-4 rounded-full bg-white transition-transform ${cameras.enabled ? 'translate-x-4' : ''}`}
          />
        </span>
      </button>
      <p className="text-muted">
        Worldwide public camera sources. Enable a region to load its catalogue. Snapshots, video and
        provider links are labelled separately. Open camera details to request an image or playback.
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
          <CameraMediaFilter
            kind={cameras.mediaKind}
            setKind={(value) => {
              setPage(0);
              cameras.setMediaKind(value);
            }}
          />
          <label className="block">
            Find a camera
            <input
              type="search"
              placeholder="Camera name or provider"
              value={cameras.query}
              onChange={(event) => {
                setPage(0);
                cameras.setQuery(event.target.value);
              }}
              maxLength={200}
              className="mt-2 min-h-11 w-full rounded border border-line bg-surface p-2"
            />
          </label>
          <p role="status" className="text-muted">
            {cameras.visible.length.toLocaleString('en-GB')} matching cameras in enabled catalogues
          </p>
          {!cameras.loading && !cameras.visible.length && (
            <p className="rounded border border-line p-3 text-muted">
              {cameras.mediaKind !== 'all'
                ? 'No cameras match this media filter. Try All media or enable another source.'
                : cameras.query.trim()
                  ? 'No cameras match this search. Try another name or provider.'
                  : 'No cameras to display. Enable a source below or refresh its catalogue.'}
            </p>
          )}
          <ul className="max-h-80 overflow-y-auto">
            {cameras.visible.slice(current * 50, (current + 1) * 50).map((camera) => (
              <li key={camera.id}>
                <button
                  type="button"
                  aria-label={camera.title}
                  aria-pressed={cameras.selected?.id === camera.id}
                  onClick={() => (onSelect ?? cameras.select)(camera)}
                  className="min-h-16 w-full border-b border-line px-2 py-3 text-left hover:bg-white/5 aria-pressed:bg-cyan/10 focus-visible:outline-2 focus-visible:outline-cyan"
                >
                  <span className="block font-medium">{camera.title}</span>
                  <span className="mt-1 block text-[11px] text-muted">
                    {cameras.catalogue?.providers.find(
                      (provider) => provider.id === camera.provider,
                    )?.name ?? camera.provider}
                  </span>
                  <span className="mt-1 block text-[10px] text-cyan">
                    {cameraMedia(camera).label}
                    {camera.coordinate_precision === 'approximate' ? ' / Approximate location' : ''}
                  </span>
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

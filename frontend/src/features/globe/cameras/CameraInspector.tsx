import { CameraStream } from './CameraStream';
import { loadCameraFrame, releaseCameraFrame } from './cameraFrames';
import { useEffect, useRef, useState } from 'react';
import { isCameraFramePath, isCameraImageUrl, type Camera } from '@/lib/api/cameras';

/** Remount for a different camera so one facility never inherits another's image. */
export function CameraInspector({ camera, onClose }: { camera: Camera; onClose: () => void }) {
  return <CameraDetails key={camera.id} camera={camera} onClose={onClose} />;
}
function CameraDetails({ camera, onClose }: { camera: Camera; onClose: () => void }) {
  const closeButton = useRef<HTMLButtonElement>(null);
  const activeRequest = useRef(0);
  const frameAbort = useRef<AbortController | null>(null);
  const [request, setRequest] = useState<{ id: number; url: string | null } | null>(null);
  const [state, setState] = useState<'idle' | 'loading' | 'loaded' | 'error' | 'expired'>('idle');
  useEffect(() => {
    const opener = document.activeElement;
    closeButton.current?.focus();
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', escape);
    return () => {
      window.removeEventListener('keydown', escape);
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [onClose]);
  useEffect(() => () => releaseCameraFrame(request?.url), [request]);
  useEffect(
    () => () => {
      // A late relayed frame must be released, never stored, once the inspector has gone.
      activeRequest.current = 0;
      frameAbort.current?.abort();
      frameAbort.current = null;
    },
    [],
  );
  useEffect(() => {
    if (!request) return;
    // TfL images must not remain displayed beyond 15 minutes after request.
    const timeout = window.setTimeout(
      () => {
        activeRequest.current = 0;
        setState('expired');
      },
      15 * 60 * 1000,
    );
    return () => window.clearTimeout(timeout);
  }, [request]);
  useEffect(() => {
    if (state !== 'loading') return;
    const timeout = window.setTimeout(() => {
      activeRequest.current = 0;
      setState('error');
    }, 20_000);
    return () => window.clearTimeout(timeout);
  }, [request, state]);
  const safe = isCameraImageUrl(camera.snapshot_url);
  return (
    <aside
      aria-label="Map details"
      className="absolute top-32 right-3 bottom-24 z-10 flex w-[calc(100%-1.5rem)] flex-col rounded-md border border-line bg-surface/95 p-4 backdrop-blur sm:w-80 lg:top-16"
    >
      <header className="flex items-start justify-between gap-2">
        <h2 className="font-medium">{camera.title}</h2>
        <button
          ref={closeButton}
          type="button"
          onClick={onClose}
          aria-label="Close camera details"
          className="min-h-11 px-2"
        >
          Close
        </button>
      </header>
      <div className="mt-3 space-y-3 overflow-y-auto text-xs">
        <p className="text-cyan">
          Public camera · {camera.snapshot_url ? 'Snapshot available' : 'Provider video or website'}
        </p>
        <CameraStream key={camera.id} camera={camera} />
        {camera.snapshot_url && (
          <button
            type="button"
            disabled={!safe}
            onClick={() => {
              if (!safe || !camera.snapshot_url) return;
              const id = (request?.id ?? 0) + 1;
              activeRequest.current = id;
              setState('loading');
              if (isCameraFramePath(camera.snapshot_url)) {
                // Relayed frames arrive through the session as a blob, then load like any image.
                // Superseded requests finish and are released; closing aborts them all.
                frameAbort.current ??= new AbortController();
                setRequest({ id, url: null });
                loadCameraFrame(camera.snapshot_url, id, {
                  signal: frameAbort.current.signal,
                }).then(
                  (objectUrl) => {
                    if (activeRequest.current === id) setRequest({ id, url: objectUrl });
                    else releaseCameraFrame(objectUrl);
                  },
                  () => {
                    if (activeRequest.current !== id) return;
                    activeRequest.current = 0;
                    setState('error');
                  },
                );
                return;
              }
              // Only append a locally generated value after canonical URL validation.
              const url = new URL(camera.snapshot_url);
              url.searchParams.set('_ase_refresh', `${Date.now()}-${id}`);
              setRequest({ id, url: url.href });
            }}
            className="min-h-11 rounded border border-line px-3 text-cyan"
          >
            {request ? 'Refresh image' : 'Load image'}
          </button>
        )}
        {camera.snapshot_url && !safe && (
          <p role="alert">This image address is not an approved camera source.</p>
        )}
        {safe && request?.url && (state === 'loading' || state === 'loaded') && (
          <img
            key={request.id}
            src={request.url}
            alt={`Camera view: ${camera.title}`}
            referrerPolicy="no-referrer"
            className="w-full rounded border border-line"
            onLoad={() => {
              if (activeRequest.current === request.id)
                setState((previous) => (previous === 'loading' ? 'loaded' : previous));
            }}
            onError={() => {
              if (activeRequest.current === request.id) {
                activeRequest.current = 0;
                setState('error');
              }
            }}
          />
        )}
        {state === 'loading' && <p role="status">Loading image…</p>}
        {state === 'loaded' && (
          <p className="text-muted">
            Image received by this browser. Capture age may still be unknown.
          </p>
        )}
        {state === 'error' && (
          <p role="alert">
            Image unavailable. The provider may be offline or restrict image access. Open the
            provider page below.
          </p>
        )}
        {state === 'expired' && (
          <p role="status">Image hidden after 15 minutes. Request a fresh image to continue.</p>
        )}
        <p>
          {camera.latitude.toFixed(5)}, {camera.longitude.toFixed(5)}
          {camera.coordinate_precision === 'approximate' &&
            ' · Approximate area, not a verified camera position'}
        </p>
        <p>
          Capture time: {camera.captured_at ?? 'Unknown'}. Catalogue refresh time does not establish
          image age.
        </p>
        <p className="text-muted">
          Loading media contacts the camera provider directly. Media loads only when requested.
        </p>
        <p>{camera.attribution}</p>
        <a
          href={camera.external_url ?? camera.source_url}
          target="_blank"
          rel="noreferrer"
          className="inline-block min-h-11 underline"
        >
          Open provider website
        </a>
      </div>
    </aside>
  );
}

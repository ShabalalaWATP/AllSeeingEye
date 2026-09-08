import { useEffect, useState } from 'react';
import type { GlobeEngineHandle } from './useGlobeEngine';

/** Small explicit controls for operators who cannot use map gestures. */
export function MapNavigationTools({
  engine,
  enabled,
}: {
  engine: GlobeEngineHandle;
  enabled: boolean;
}) {
  const [fullscreen, setFullscreen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const changed = () => setFullscreen(document.fullscreenElement !== null);
    document.addEventListener('fullscreenchange', changed);
    return () => document.removeEventListener('fullscreenchange', changed);
  }, []);
  const move = (kind: 'in' | 'out' | 'north' | 'home') => {
    const camera = engine.getCamera?.();
    if (!camera) return;
    if (kind === 'home') {
      engine.restoreCamera?.({ center: [0, 20], zoom: 1.5, bearing: 0, pitch: 0 });
    } else if (kind === 'north') {
      engine.restoreCamera?.({ ...camera, bearing: 0, pitch: 0 });
    } else {
      engine.flyTo({
        center: camera.center,
        zoom: Math.max(0, Math.min(22, camera.zoom + (kind === 'in' ? 1 : -1))),
      });
    }
  };
  const toggleFullscreen = async () => {
    setError(null);
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      setError('Fullscreen is unavailable in this browser.');
    }
  };
  const buttonClass =
    'flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-muted hover:bg-surface-2 hover:text-text focus-visible:outline-2 focus-visible:outline-cyan disabled:opacity-40';
  return (
    <div
      role="group"
      aria-label="Map navigation"
      className="flex flex-col gap-0.5 border-t border-line pt-1"
    >
      {(
        [
          ['in', 'Zoom in', 'M12 5v14M5 12h14'],
          ['out', 'Zoom out', 'M5 12h14'],
          ['north', 'Reset north-up', 'm12 3 7 17-7-4-7 4 7-17Z'],
          ['home', 'Reset world view', 'M21 12a9 9 0 1 1-3-6.7M21 3v6h-6'],
        ] as const
      ).map(([kind, label, path]) => (
        <button
          key={kind}
          type="button"
          aria-label={label}
          title={label}
          disabled={!enabled}
          onClick={() => move(kind)}
          className={buttonClass}
        >
          <svg
            aria-hidden="true"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d={path} />
          </svg>
        </button>
      ))}
      {document.fullscreenEnabled && (
        <button
          type="button"
          aria-label={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          title={fullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          aria-pressed={fullscreen}
          onClick={() => {
            void toggleFullscreen();
          }}
          className={buttonClass}
        >
          <svg
            aria-hidden="true"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          >
            <path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" />
          </svg>
        </button>
      )}
      {error && (
        <p
          role="alert"
          className="absolute right-14 bottom-0 w-48 rounded bg-ground p-2 text-xs text-text"
        >
          {error}
        </p>
      )}
    </div>
  );
}

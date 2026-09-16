/**
 * Mounts the WebGL journey beside the reading list. The scene module is imported lazily, and
 * only once the stage has scrolled into view, so the rest of the application never pays for
 * three.js. Rendering stops when the stage leaves the viewport or the tab is hidden, and the
 * scene releases its geometries, materials and context on unmount.
 */
import { useEffect, useRef, useState } from 'react';

import type { JourneyScene } from './journeyScene';

interface Props {
  /** One colour per stop, in travel order; changing the journey remounts through a key. */
  colours: string[];
  index: number;
  playing: boolean;
  background: string;
}

/** Observers are optional in older browsers and absent in jsdom; fall back to always-on. */
function observeVisibility(element: Element, onChange: (visible: boolean) => void): () => void {
  if (typeof IntersectionObserver !== 'function') {
    onChange(true);
    return () => undefined;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) onChange(entry.isIntersecting);
    },
    { rootMargin: '120px' },
  );
  observer.observe(element);
  return () => {
    observer.disconnect();
  };
}

export function JourneyCanvas({ colours, index, playing, background }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const sceneRef = useRef<JourneyScene | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas === null) return undefined;
    let live = true;
    let onScreen = false;
    let building = false;

    const running = (): boolean => onScreen && document.visibilityState === 'visible';

    const build = (): void => {
      if (building || sceneRef.current !== null) return;
      building = true;
      void import('./journeyScene')
        .then(({ createJourneyScene }) => {
          const box = canvas.getBoundingClientRect();
          if (!live) return;
          sceneRef.current = createJourneyScene({
            canvas,
            colours,
            background,
            width: Math.max(Math.round(box.width), 1),
            height: Math.max(Math.round(box.height), 1),
          });
          sceneRef.current.travelTo(index);
          sceneRef.current.setPlaying(playing);
          sceneRef.current.setRunning(running());
        })
        .catch(() => {
          if (live) setFailed(true);
        });
    };

    const sync = (): void => {
      if (running()) build();
      sceneRef.current?.setRunning(running());
    };

    const stopObserving = observeVisibility(canvas, (visible) => {
      onScreen = visible;
      sync();
    });
    document.addEventListener('visibilitychange', sync);

    const resize = (): void => {
      const box = canvas.getBoundingClientRect();
      sceneRef.current?.resize(
        Math.max(Math.round(box.width), 1),
        Math.max(Math.round(box.height), 1),
      );
    };
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(resize) : null;
    observer?.observe(canvas);
    window.addEventListener('resize', resize);

    return () => {
      live = false;
      stopObserving();
      document.removeEventListener('visibilitychange', sync);
      window.removeEventListener('resize', resize);
      observer?.disconnect();
      sceneRef.current?.dispose();
      sceneRef.current = null;
    };
    // The journey is rebuilt through a key when the stops change; index and playing are pushed below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    sceneRef.current?.travelTo(index);
  }, [index]);

  useEffect(() => {
    sceneRef.current?.setPlaying(playing);
  }, [playing]);

  if (failed) return null;
  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      data-testid="journey-canvas"
      className="absolute inset-0 h-full w-full"
    />
  );
}

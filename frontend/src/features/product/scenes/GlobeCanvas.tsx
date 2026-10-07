/**
 * The story globe. A 2D canvas (no WebGL needed, so it works everywhere) that draws
 * only while on screen and the story may move, at no more than twice the device
 * pixel ratio. The parent steers it through a ref, so scrolling never re-renders
 * React. The renderer is built once; pausing or hiding the tab only stops and
 * restarts its loop, so the Earth keeps its place. A still story draws one frame.
 */
import { useEffect, useMemo, useRef, type RefObject } from 'react';

import { useStoryMotion } from '../motion/useStoryMotion';
import { drawGlobe } from './drawGlobe';
import { landPoints } from './globeMath';
import { buildScene } from './sceneData';

export interface GlobeControls {
  revealed: number;
  active: number;
  /** 0 shows the whole Earth slowly turning; 1 settles on the Red Sea for the Ask chapter. */
  focus: number;
}

export interface GlobeCanvasProps {
  controls: RefObject<GlobeControls>;
  label: string;
}

interface Renderer {
  /** Repaint now and keep animating while allowed. */
  wake: () => void;
}

const FOCUS = { lon: 42, lat: 16 };
const SPIN_DEGREES_PER_SECOND = 5;

export function GlobeCanvas({ controls, label }: GlobeCanvasProps) {
  const { still, idle } = useStoryMotion();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const motion = useRef({ still, idle });
  const renderer = useRef<Renderer | null>(null);
  const land = useMemo(() => landPoints(16000), []);
  const layers = useMemo(() => buildScene(), []);

  useEffect(() => {
    motion.current = { still, idle };
    renderer.current?.wake();
  }, [still, idle]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (canvas === null || ctx === null || ctx === undefined) return undefined;
    let frame = 0;
    let onScreen = true;
    let spin = 20;
    let width = 0;
    let height = 0;
    let last = performance.now();
    const started = last;

    const resize = () => {
      const ratio = Math.min(2, window.devicePixelRatio || 1);
      ({ width, height } = canvas.getBoundingClientRect());
      canvas.width = Math.max(1, Math.round(width * ratio));
      canvas.height = Math.max(1, Math.round(height * ratio));
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const paint = (now: number) => {
      const { revealed, active, focus } = controls.current;
      const { still: frozen } = motion.current;
      const eased = focus * focus * (3 - 2 * focus);
      const radius = (Math.min(width, height) / 2.3) * (1 + eased * 0.3);
      ctx.clearRect(0, 0, width, height);
      drawGlobe(ctx, land, layers, {
        view: {
          lon: spin + (FOCUS.lon - spin) * eased,
          lat: 12 + (FOCUS.lat - 12) * eased,
          radius,
          cx: width / 2,
          cy: height / 2,
        },
        revealed: frozen ? layers.length : revealed,
        active: frozen ? -1 : active,
        time: (now - started) / 1000,
      });
    };

    const loop = (now: number) => {
      frame = 0;
      const elapsed = Math.min(0.1, (now - last) / 1000);
      last = now;
      const turn = elapsed * SPIN_DEGREES_PER_SECOND * (1 - controls.current.focus);
      spin = ((spin + turn + 180) % 360) - 180;
      paint(now);
      if (onScreen && !motion.current.idle) frame = requestAnimationFrame(loop);
    };

    const wake = () => {
      paint(performance.now());
      if (frame === 0 && onScreen && !motion.current.idle) {
        last = performance.now();
        frame = requestAnimationFrame(loop);
      }
    };
    renderer.current = { wake };

    resize();
    wake();
    const resizer =
      typeof ResizeObserver === 'function'
        ? new ResizeObserver(() => {
            resize();
            paint(performance.now());
          })
        : null;
    resizer?.observe(canvas);
    const watcher =
      typeof IntersectionObserver === 'function'
        ? new IntersectionObserver((entries) => {
            onScreen = entries.some((entry) => entry.isIntersecting);
            if (onScreen) wake();
          })
        : null;
    watcher?.observe(canvas);

    return () => {
      renderer.current = null;
      if (frame !== 0) cancelAnimationFrame(frame);
      resizer?.disconnect();
      watcher?.disconnect();
    };
  }, [controls, land, layers]);

  return (
    <div className="story-globe" role="img" aria-label={label}>
      <canvas ref={canvasRef} aria-hidden="true" />
    </div>
  );
}

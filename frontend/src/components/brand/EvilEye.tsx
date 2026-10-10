/*
 * EvilEye: the React Bits "Evil Eye" background component, used as the
 * brand mark of The All Seeing Eye.
 *
 * Source:     https://reactbits.dev/backgrounds/evil-eye
 * Registry:   https://reactbits.dev/r/EvilEye-TS-TW.json (TypeScript + Tailwind variant)
 * Retrieved:  4 September 2026
 * Licence:    MIT + Commons Clause License Condition v1.0, Copyright (c) 2026 David Haz.
 *             Full text in frontend/THIRD_PARTY_NOTICES.md.
 *
 * Modifications from the registry copy (kept to the minimum needed by the small
 * shell instance of the mark; existing colours and defaults are untouched):
 *   1. Two optional props were added to EvilEyeProps: `maxFps` caps the
 *      requestAnimationFrame loop by skipping frames, and `paused` stops the loop
 *      while true. Both are read through refs so changing them does not rebuild
 *      the WebGL context.
 *   2. The `update` loop honours those two props and a `start` helper resumes the
 *      loop when `paused` returns to false. The cleanup also clears the resume ref.
 *   3. Observe responsive resizing; stop/release graphics resources on failures.
 *      The existing original frame capture remains visible without creating a recovery loop.
 *   4. Shader/noise helpers are extracted unchanged into evilEyeShader.ts.
 *   5. Opt-in transparent compositing preserves the original eye/flame pattern
 *      for the assistant launcher. The captured fallback hides after a good frame.
 *   6. The captured fallback offers downscaled captures of this component (64,
 *      128, 192 and 512 px, WebP with PNG fallback) and an optional `fallbackSizes`
 *      prop, so small marks never request the 512 px capture.
 *   7. Reuse the original deterministic noise pixels across instances. Each WebGL
 *      context still owns its texture and disposes it independently.
 *   8. Optionally initialise only when visible, retaining the original capture until then.
 *   9. Public eyes can render the same engine in a worker; DOM timing and input stay here.
 */
import { useEffect, useRef, useState } from 'react';
import type { EyeOptions, EyeSurface } from './evilEyeProtocol';
import { createEyeRenderer } from './evilEyeRenderer';
import { createEyeWorker } from './evilEyeWorkerClient';

// Added for The All Seeing Eye: real captures of this component at several widths.
const CAPTURE_WIDTHS = [64, 128, 192, 512] as const;
function captureSet(format: 'png' | 'webp'): string {
  return CAPTURE_WIDTHS.map((width) => `/brand/eye-${width}.${format} ${width}w`).join(', ');
}
const PNG_CAPTURES = captureSet('png');
const WEBP_CAPTURES = captureSet('webp');

interface EvilEyeProps {
  eyeColor?: string;
  intensity?: number;
  pupilSize?: number;
  irisWidth?: number;
  glowIntensity?: number;
  scale?: number;
  noiseScale?: number;
  pupilFollow?: number;
  flameSpeed?: number;
  backgroundColor?: string;
  lightMode?: boolean;
  /** Added for The All Seeing Eye: cap the frame rate by skipping frames. */
  maxFps?: number;
  /** Added for The All Seeing Eye: stop rendering while true. */
  paused?: boolean;
  /** Render the original eye energy on a transparent surface, without a background. */
  transparent?: boolean;
  /** Added for The All Seeing Eye: the `sizes` hint for the captured fallback image. */
  fallbackSizes?: string;
  /** Prioritise a visible hero capture without changing other brand instances. */
  fallbackPriority?: 'high';
  /** Keep the capture until first viewport entry, without constructing an off-screen context. */
  deferUntilVisible?: boolean;
  /** Public eyes use an offscreen worker when supported, with a synchronous fallback. */
  workerRendering?: boolean;
}

export default function EvilEye({
  eyeColor = '#FF6F37',
  intensity = 1.5,
  pupilSize = 0.6,
  irisWidth = 0.25,
  glowIntensity = 0.35,
  scale = 0.8,
  noiseScale = 1.0,
  pupilFollow = 1.0,
  flameSpeed = 1.0,
  backgroundColor = '#000000',
  lightMode = false,
  maxFps,
  paused = false,
  transparent = false,
  fallbackSizes,
  fallbackPriority,
  deferUntilVisible = false,
  workerRendering = false,
}: EvilEyeProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fallbackRef = useRef<HTMLImageElement>(null);
  const [unavailable, setUnavailable] = useState(false);
  // Added for The All Seeing Eye: frame cap and pause are read through refs so
  // that toggling them never tears down the WebGL context.
  const maxFpsRef = useRef<number | undefined>(maxFps);
  const pausedRef = useRef<boolean>(paused);
  const resumeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    maxFpsRef.current = maxFps;
  }, [maxFps]);

  useEffect(() => {
    pausedRef.current = paused;
    if (!paused) resumeRef.current?.();
  }, [paused]);

  useEffect(() => {
    if (unavailable || !containerRef.current) return;
    const container = containerRef.current;
    const fallback = fallbackRef.current;
    if (fallback) fallback.hidden = false;
    const disposers: Array<() => void> = [];
    let stopped = false;
    const dispose = () => {
      if (stopped) return;
      stopped = true;
      if (fallback) fallback.hidden = false;
      resumeRef.current = null;
      for (const release of disposers.reverse()) {
        try {
          release();
        } catch {
          /* A lost context may already have released the resource. */
        }
      }
    };
    const fail = () => {
      dispose();
      setUnavailable(true);
    };
    const initialise = () => {
      try {
        const options: EyeOptions = {
          eyeColor, intensity, pupilSize, irisWidth, glowIntensity, scale, noiseScale,
          pupilFollow, flameSpeed, backgroundColor, lightMode, transparent,
        };
        const size = () => ({ width: container.offsetWidth, height: container.offsetHeight });
        let canvas = document.createElement('canvas');
        let surface: EyeSurface | null = null;
        const rendered = () => {
          if (!stopped && fallback) fallback.hidden = true;
        };
        const synchronous = () => {
          if (stopped) return;
          surface?.dispose();
          // A transferred canvas cannot acquire a main-thread context, even if
          // the worker failed before rendering. Always use a fresh DOM canvas.
          canvas.remove();
          canvas = document.createElement('canvas');
          try {
            const renderer = createEyeRenderer(canvas, options, size(), fail);
            surface = {
              resize: renderer.resize,
              render(frame) {
                renderer.render(frame);
                rendered();
                return true;
              },
              dispose: renderer.dispose,
            };
            container.appendChild(canvas);
          } catch {
            fail();
          }
        };
        disposers.push(() => {
          surface?.dispose();
          canvas.remove();
        });
        if (workerRendering) {
          surface = createEyeWorker(canvas, options, size(), rendered, synchronous, fail);
        }
        if (surface) container.appendChild(canvas);
        else synchronous();
        if (stopped) return dispose;

        const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
        function onMouseMove(e: MouseEvent) {
          const rect = container.getBoundingClientRect();
          mouse.tx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
          mouse.ty = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
        }
        function onMouseLeave() {
          mouse.tx = 0;
          mouse.ty = 0;
        }
        container.addEventListener('mousemove', onMouseMove);
        container.addEventListener('mouseleave', onMouseLeave);
        disposers.push(() => {
          container.removeEventListener('mousemove', onMouseMove);
          container.removeEventListener('mouseleave', onMouseLeave);
        });
        function resize() {
          // OffscreenCanvas dimensions belong to the worker, but its placeholder's
          // CSS dimensions remain the DOM owner's responsibility (OGL dpr stays 1).
          canvas.style.width = `${container.offsetWidth}px`;
          canvas.style.height = `${container.offsetHeight}px`;
          surface?.resize(size());
        }
        window.addEventListener('resize', resize);
        disposers.push(() => window.removeEventListener('resize', resize));
        const resizeObserver =
          typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
        disposers.push(() => resizeObserver?.disconnect());
        resizeObserver?.observe(container);
        resize();

        // Added for The All Seeing Eye: the loop stops while paused and skips frames
        // above maxFps. Zero means "no frame scheduled".
        let animationFrameId = 0;
        disposers.push(() => cancelAnimationFrame(animationFrameId));
        let lastFrameTime = -Infinity;

        function update(time: number) {
          if (stopped || pausedRef.current) {
            animationFrameId = 0;
            return;
          }
          animationFrameId = requestAnimationFrame(update);
          const cap = maxFpsRef.current;
          if (cap !== undefined && cap > 0 && time - lastFrameTime < 1000 / cap) return;
          const x = mouse.x + (mouse.tx - mouse.x) * 0.05;
          const y = mouse.y + (mouse.ty - mouse.y) * 0.05;
          try {
            // Advance interpolation only for accepted frames. A worker has at most
            // one frame in flight, so a slow context cannot accumulate stale input.
            if (surface?.render({ time, mouse: [x, y] })) {
              mouse.x = x;
              mouse.y = y;
              lastFrameTime = time;
            }
          } catch {
            fail();
          }
        }

        function start() {
          if (!stopped && animationFrameId === 0 && !pausedRef.current) {
            animationFrameId = requestAnimationFrame(update);
          }
        }
        resumeRef.current = start;
        start();

        return dispose;
      } catch {
        fail();
        return dispose;
      }
    };
    if (!deferUntilVisible || typeof IntersectionObserver !== 'function') return initialise();
    let initialised = false;
    const observer = new IntersectionObserver((entries) => {
      if (stopped || initialised || !entries.some((entry) => entry.isIntersecting)) return;
      initialised = true;
      observer.disconnect();
      initialise();
    });
    disposers.push(() => observer.disconnect());
    observer.observe(container);
    return dispose;
  }, [
    unavailable,
    eyeColor,
    intensity,
    pupilSize,
    irisWidth,
    glowIntensity,
    scale,
    noiseScale,
    pupilFollow,
    flameSpeed,
    backgroundColor,
    lightMode,
    transparent,
    deferUntilVisible,
    workerRendering,
  ]);

  return (
    <div className="relative h-full w-full">
      <picture>
        <source type="image/webp" srcSet={WEBP_CAPTURES} sizes={fallbackSizes} />
        <img
          ref={fallbackRef}
          src="/brand/eye-512.png"
          srcSet={PNG_CAPTURES}
          sizes={fallbackSizes}
          fetchPriority={fallbackPriority}
          decoding="async"
          alt=""
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-contain"
          style={
            transparent
              ? {
                  mixBlendMode: 'screen',
                  maskImage: 'radial-gradient(ellipse at center, black 35%, transparent 72%)',
                }
              : undefined
          }
        />
      </picture>
      <div ref={containerRef} className="relative h-full w-full" hidden={unavailable} />
    </div>
  );
}

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
 */
import { Renderer, Program, Mesh, Triangle, Texture } from 'ogl';
import { useEffect, useRef, useState } from 'react';
import { generateNoiseTexture, hexToVec3, vertexShader, fragmentShader } from './evilEyeShader';

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
    try {
      const renderer = new Renderer({ alpha: true, premultipliedAlpha: false, dpr: 1 });
      const gl = renderer.gl;
      disposers.push(() => {
        gl.getExtension('WEBGL_lose_context')?.loseContext();
      });
      const onLost = (event: Event) => {
        event.preventDefault();
        // Keep the captured original eye instead of competing with the map for recovery.
        fail();
      };
      gl.canvas.addEventListener('webglcontextlost', onLost);
      disposers.push(() => gl.canvas.removeEventListener('webglcontextlost', onLost));
      gl.clearColor(0, 0, 0, 0);

      const noiseData = generateNoiseTexture(256);
      const noiseTexture = new Texture(gl, {
        image: noiseData,
        width: 256,
        height: 256,
        generateMipmaps: false,
        flipY: false,
      });
      disposers.push(() => gl.deleteTexture(noiseTexture.texture));
      noiseTexture.minFilter = gl.LINEAR;
      noiseTexture.magFilter = gl.LINEAR;
      noiseTexture.wrapS = gl.REPEAT;
      noiseTexture.wrapT = gl.REPEAT;

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

      let program: Program;

      function resize() {
        renderer.setSize(container.offsetWidth, container.offsetHeight);
        if (program) {
          program.uniforms.uResolution.value = [
            gl.canvas.width,
            gl.canvas.height,
            gl.canvas.width / gl.canvas.height,
          ];
        }
      }
      window.addEventListener('resize', resize);
      disposers.push(() => window.removeEventListener('resize', resize));
      const resizeObserver =
        typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(resize);
      disposers.push(() => resizeObserver?.disconnect());
      resizeObserver?.observe(container);
      resize();

      const geometry = new Triangle(gl);
      disposers.push(() => geometry.remove());
      program = new Program(gl, {
        vertex: vertexShader,
        fragment: fragmentShader,
        uniforms: {
          uTime: { value: 0 },
          uResolution: {
            value: [gl.canvas.width, gl.canvas.height, gl.canvas.width / gl.canvas.height],
          },
          uNoiseTexture: { value: noiseTexture },
          uPupilSize: { value: pupilSize },
          uIrisWidth: { value: irisWidth },
          uGlowIntensity: { value: glowIntensity },
          uIntensity: { value: intensity },
          uScale: { value: scale },
          uNoiseScale: { value: noiseScale },
          uMouse: { value: [0, 0] },
          uPupilFollow: { value: pupilFollow },
          uFlameSpeed: { value: flameSpeed },
          uEyeColor: { value: hexToVec3(eyeColor) },
          uBgColor: { value: hexToVec3(backgroundColor) },
          uLightMode: { value: lightMode },
          uTransparent: { value: transparent },
        },
      });

      disposers.push(() => program.remove());
      const mesh = new Mesh(gl, { geometry, program });
      container.appendChild(gl.canvas);
      disposers.push(() => gl.canvas.remove());

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
        lastFrameTime = time;
        mouse.x += (mouse.tx - mouse.x) * 0.05;
        mouse.y += (mouse.ty - mouse.y) * 0.05;
        program.uniforms.uMouse.value = [mouse.x, mouse.y];
        program.uniforms.uTime.value = time * 0.001;
        try {
          renderer.render({ scene: mesh });
          // Hide the captured matte once a real frame exists, especially when
          // the live canvas is transparent. Restore it only on graphics failure.
          if (fallback && !fallback.hidden) fallback.hidden = true;
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
  ]);

  return (
    <div className="relative h-full w-full">
      <img
        ref={fallbackRef}
        src="/brand/eye-512.png"
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
      <div ref={containerRef} className="relative h-full w-full" hidden={unavailable} />
    </div>
  );
}

import type { EyeOptions, EyeReply, EyeRequest, EyeSize, EyeSurface } from './evilEyeProtocol';
import { eyeNoise } from './evilEyeRenderer';

// This is failure detection, not an animation delay. Rendering starts as soon as ready arrives.
const STARTUP_TIMEOUT_MS = 5_000;
const DISPOSE_TIMEOUT_MS = 250;

export function createEyeWorker(
  canvas: HTMLCanvasElement,
  options: EyeOptions,
  size: EyeSize,
  onFrame: () => void,
  onStartupFailure: () => void,
  onFailure: () => void,
): EyeSurface | null {
  if (typeof Worker !== 'function' || typeof canvas.transferControlToOffscreen !== 'function')
    return null;
  let worker: Worker;
  try {
    worker = new Worker(new URL('./evilEye.worker.ts', import.meta.url), { type: 'module' });
  } catch {
    return null;
  }
  let stopped = false;
  let ready = false;
  let busy: 'frame' | 'resize' | null = null;
  let lastSize = size;
  let pendingSize: EyeSize | undefined;
  let disposeTimer: ReturnType<typeof setTimeout> | undefined;
  const post = (message: EyeRequest, transfer: Transferable[] = []) =>
    worker.postMessage(message, transfer);
  const terminate = () => {
    clearTimeout(startupTimer);
    clearTimeout(disposeTimer);
    worker.onmessage = null;
    worker.onerror = null;
    worker.onmessageerror = null;
    worker.terminate();
  };
  const fail = (startup: boolean) => {
    if (stopped) return;
    stopped = true;
    terminate();
    if (startup) onStartupFailure();
    else onFailure();
  };
  const startupTimer = setTimeout(() => fail(true), STARTUP_TIMEOUT_MS);
  const flushResize = () => {
    if (stopped || !ready || busy !== null || !pendingSize) return;
    const next = pendingSize;
    pendingSize = undefined;
    lastSize = next;
    busy = 'resize';
    try {
      post({ type: 'resize', size: next });
    } catch {
      fail(false);
    }
  };
  worker.onerror = () => fail(!ready);
  worker.onmessageerror = () => fail(!ready);
  worker.onmessage = ({ data }: MessageEvent<EyeReply>) => {
    if (data.type === 'disposed') {
      terminate();
      return;
    }
    if (stopped) return;
    if (data.type === 'failed') {
      fail(data.phase === 'startup');
    } else if (data.type === 'ready') {
      clearTimeout(startupTimer);
      ready = true;
      flushResize();
    } else if (data.type === 'frame' && busy === 'frame') {
      busy = null;
      onFrame();
      flushResize();
    } else if (data.type === 'resized' && busy === 'resize') {
      busy = null;
      flushResize();
    }
  };
  try {
    const offscreen = canvas.transferControlToOffscreen();
    // Structured clone the immutable CPU pixels. Transferring their buffer would
    // detach the shared noise used by synchronous eyes and subsequent workers.
    post({ type: 'init', canvas: offscreen, options, size, noise: eyeNoise() }, [offscreen]);
  } catch {
    stopped = true;
    terminate();
    // The caller always replaces this canvas before synchronous fallback, even
    // when transfer succeeded but posting the initial message failed.
    return null;
  }
  return {
    resize(next) {
      pendingSize =
        next.width === lastSize.width && next.height === lastSize.height ? undefined : next;
      flushResize();
    },
    render(frame) {
      if (stopped || !ready || busy) return false;
      busy = 'frame';
      try {
        post({ type: 'frame', frame });
        return true;
      } catch {
        fail(false);
        return false;
      }
    },
    dispose() {
      if (stopped) return;
      stopped = true;
      clearTimeout(startupTimer);
      // Give the shared engine an opportunity to release GPU resources. A worker
      // that failed to start cannot acknowledge; termination still bounds its lifetime.
      disposeTimer = setTimeout(terminate, DISPOSE_TIMEOUT_MS);
      try {
        post({ type: 'dispose' });
      } catch {
        terminate();
      }
    },
  };
}

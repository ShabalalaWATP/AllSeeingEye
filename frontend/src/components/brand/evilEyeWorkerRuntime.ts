import type { EyeReply, EyeRequest } from './evilEyeProtocol';
import { createEyeRenderer } from './evilEyeRenderer';

/** A small structural worker type avoids mixing the DOM and WebWorker ambient libraries. */
export interface EyeWorkerScope {
  onmessage: ((event: MessageEvent<EyeRequest>) => void) | null;
  postMessage: (message: EyeReply) => void;
}

export function installEyeWorker(scope: EyeWorkerScope): void {
  let renderer: ReturnType<typeof createEyeRenderer> | undefined;
  let stopped = false;
  const dispose = () => {
    stopped = true;
    renderer?.dispose();
    renderer = undefined;
  };
  const failed = (phase: 'startup' | 'render' | 'lost') => {
    dispose();
    scope.postMessage({ type: 'failed', phase });
  };
  scope.onmessage = ({ data }) => {
    if (data.type === 'dispose') {
      dispose();
      scope.postMessage({ type: 'disposed' });
      return;
    }
    if (stopped) return;
    try {
      if (data.type === 'init' && !renderer) {
        renderer = createEyeRenderer(
          data.canvas,
          data.options,
          data.size,
          () => failed('lost'),
          data.noise,
        );
        scope.postMessage({ type: 'ready' });
      } else if (data.type === 'resize' && renderer) {
        renderer.resize(data.size);
        scope.postMessage({ type: 'resized' });
      } else if (data.type === 'frame' && renderer) {
        renderer.render(data.frame);
        scope.postMessage({ type: 'frame' });
      }
    } catch {
      failed(renderer ? 'render' : 'startup');
    }
  };
}

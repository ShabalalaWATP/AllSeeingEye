import type { Ref } from 'react';
import type { GlobeEngineHandle } from './useGlobeEngine';
import { WebGlFallback } from './WebGlFallback';

/** Own the map host geometry independently of dashboard controls. */
export function MapCanvas({
  containerRef,
  supported,
  mode,
  engine,
}: {
  containerRef: Ref<HTMLDivElement>;
  supported: boolean;
  mode: 'globe' | 'map';
  engine?: GlobeEngineHandle;
}) {
  return supported ? (
    <>
      <div
        ref={containerRef}
        role="region"
        aria-label={mode === 'globe' ? '3D globe' : 'Map'}
        data-testid="map-container"
        // MapLibre forces position: relative, so the host needs explicit height.
        className="h-full w-full"
      />
      {engine?.renderState && engine.renderState.status !== 'ready' && (
        <section
          role="status"
          aria-live="polite"
          aria-label="Map graphics status"
          className="absolute bottom-20 left-1/2 z-40 w-[min(28rem,calc(100%-6rem))] -translate-x-1/2 rounded-lg border border-line bg-ground/95 p-4 text-sm text-text shadow-xl"
        >
          <p>{engine.renderState.message}</p>
          {engine.renderState.status === 'failed' && (
            <button
              type="button"
              onClick={engine.reload}
              className="mt-3 rounded border border-cyan px-3 py-2 text-cyan focus-visible:outline-2 focus-visible:outline-cyan"
            >
              Reload map
            </button>
          )}
        </section>
      )}
    </>
  ) : (
    <WebGlFallback />
  );
}

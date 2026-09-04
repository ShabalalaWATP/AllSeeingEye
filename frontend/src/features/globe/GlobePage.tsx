/**
 * The root view: a full-bleed 3D globe (default) with an explicit Map mode
 * toggle. When WebGL2 is unavailable the engine is not mounted and the page
 * explains why.
 */
import { useRef, useState } from 'react';

import { Alert } from '@/components/ui/Alert';
import { useGlobeStore } from '@/stores/globe';

import { ModeToolbar } from './ModeToolbar';
import { useGlobeEngine } from './useGlobeEngine';
import { hasWebGl2 } from './webgl';

export default function GlobePage() {
  const mode = useGlobeStore((state) => state.mode);
  const setMode = useGlobeStore((state) => state.setMode);
  const [supported] = useState(() => hasWebGl2());
  const containerRef = useRef<HTMLDivElement>(null);

  useGlobeEngine(containerRef, mode, supported);

  return (
    <div className="relative h-full w-full bg-ground">
      {supported ? (
        <div
          ref={containerRef}
          role="region"
          aria-label={mode === 'globe' ? '3D globe' : 'Map'}
          data-testid="map-container"
          className="absolute inset-0"
        />
      ) : (
        <div className="flex h-full items-center justify-center p-6">
          <Alert tone="warning" title="WebGL2 is required" className="max-w-md">
            The globe needs WebGL2, which this browser or device does not provide. Enable hardware
            acceleration or use a current version of Chrome, Edge, Firefox or Safari.
          </Alert>
        </div>
      )}
      <ModeToolbar mode={mode} onChange={setMode} />
    </div>
  );
}

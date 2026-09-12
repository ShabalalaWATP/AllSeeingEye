import { useRef, useState } from 'react';
import type { BaseLayer, ViewMode } from '@/stores/globe';
import { createEngine } from './globeEngineFactory';
import { useGlobeEngine } from './useGlobeEngine';
import { hasWebGl2 } from './webgl';

/** Create one guarded engine while leaving the controls usable without WebGL. */
export function useDashboardEngine(options: {
  mode: ViewMode;
  baseLayer: BaseLayer;
  lite: boolean;
}) {
  const [supported] = useState(() => hasWebGl2());
  const containerRef = useRef<HTMLDivElement>(null);
  const engine = useGlobeEngine(containerRef, { ...options, enabled: supported, createEngine });
  return { supported, containerRef, engine };
}

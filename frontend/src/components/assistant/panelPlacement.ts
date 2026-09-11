import type { CSSProperties } from 'react';
import { LAUNCHER_WIDTH } from './useAssistantPosition';

/** Keep both panel sizes inside the viewport, independently of the movable launcher. */
export function panelPlacement(
  position: { x: number; y: number },
  expanded: boolean,
  viewport = { width: window.innerWidth, height: window.innerHeight },
): CSSProperties {
  if (expanded) {
    const insetX = Math.max(12, Math.min(48, viewport.width * 0.03));
    const insetY = Math.max(16, Math.min(44, viewport.height * 0.04));
    return {
      left: insetX,
      top: insetY,
      width: viewport.width - 2 * insetX,
      height: viewport.height - 2 * insetY,
    };
  }
  const width = Math.min(420, viewport.width - 24);
  const height = Math.min(600, viewport.height - 32);
  return {
    left: Math.max(12, Math.min(viewport.width - width - 12, position.x + LAUNCHER_WIDTH - width)),
    top: Math.max(16, Math.min(viewport.height - height - 16, position.y - height - 10)),
    width,
    height,
  };
}

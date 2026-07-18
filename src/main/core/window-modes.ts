import type { WindowMode } from '../../shared/types'

export interface Size {
  width: number
  height: number
}

export interface Rect extends Size {
  x: number
  y: number
}

export const WINDOW_MODES: Record<WindowMode, Size> = {
  eye: { width: 200, height: 150 },
  compact: { width: 520, height: 200 },
  expanded: { width: 560, height: 620 }
}

/** Centre of the eye graphic relative to the window's top-left, in pixels. */
export const EYE_CENTRE = { x: 100, y: 55 }

/** Content-driven height bounds for the auto-sizing panel windows. */
export const CONTENT_HEIGHT_LIMITS: Record<'compact' | 'expanded', { min: number; max: number }> =
  {
    compact: { min: 150, max: 480 },
    expanded: { min: 340, max: 860 }
  }

const WORK_AREA_HEIGHT_MARGIN = 24

/**
 * Clamp a measured content height into the mode's bounds and the work area.
 * Returns null for the eye window, which never auto-sizes.
 */
export function clampContentHeight(
  mode: WindowMode,
  height: number,
  workAreaHeight: number
): number | null {
  if (mode === 'eye') return null
  const { min, max } = CONTENT_HEIGHT_LIMITS[mode]
  return Math.max(min, Math.min(Math.round(height), max, workAreaHeight - WORK_AREA_HEIGHT_MARGIN))
}

const SCREEN_EDGE_MARGIN = 24

/**
 * Keep the window's top-left anchored (the eye stays put) while clamping the
 * whole target rectangle into the given work area.
 */
export function placeWindow(current: { x: number; y: number }, target: Size, workArea: Rect): Rect {
  const maxX = workArea.x + workArea.width - target.width
  const maxY = workArea.y + workArea.height - target.height
  return {
    x: Math.max(workArea.x, Math.min(current.x, maxX)),
    y: Math.max(workArea.y, Math.min(current.y, maxY)),
    width: target.width,
    height: target.height
  }
}

/** Default first-run position: bottom-right of the work area with a margin. */
export function defaultPosition(workArea: Rect, size: Size): { x: number; y: number } {
  return {
    x: workArea.x + workArea.width - size.width - SCREEN_EDGE_MARGIN,
    y: workArea.y + workArea.height - size.height - SCREEN_EDGE_MARGIN
  }
}

const MIN_VISIBLE_PIXELS = 40

/** True when at least a usable corner of the window overlaps any work area. */
export function isVisibleOnAny(pos: { x: number; y: number }, size: Size, workAreas: Rect[]): boolean {
  return workAreas.some((wa) => {
    const overlapX = Math.min(pos.x + size.width, wa.x + wa.width) - Math.max(pos.x, wa.x)
    const overlapY = Math.min(pos.y + size.height, wa.y + wa.height) - Math.max(pos.y, wa.y)
    return overlapX >= MIN_VISIBLE_PIXELS && overlapY >= MIN_VISIBLE_PIXELS
  })
}

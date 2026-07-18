import { describe, expect, it } from 'vitest'
import {
  EYE_TRAY_SIZE,
  WINDOW_MODES,
  clampContentHeight,
  defaultPosition,
  isVisibleOnAny,
  placeWindow
} from '../src/main/core/window-modes'

const workArea = { x: 0, y: 0, width: 1920, height: 1040 }

describe('WINDOW_MODES', () => {
  it('defines the three approved sizes', () => {
    expect(WINDOW_MODES.eye).toEqual({ width: 216, height: 120 })
    expect(EYE_TRAY_SIZE).toEqual({ width: 216, height: 258 })
    expect(WINDOW_MODES.compact).toEqual({ width: 520, height: 200 })
    expect(WINDOW_MODES.expanded).toEqual({ width: 560, height: 620 })
  })
})

describe('clampContentHeight', () => {
  it('never auto-sizes the eye window', () => {
    expect(clampContentHeight('eye', 500, 1040)).toBeNull()
  })

  it('respects the per-mode minimum', () => {
    expect(clampContentHeight('compact', 60, 1040)).toBe(150)
    expect(clampContentHeight('expanded', 100, 1040)).toBe(340)
  })

  it('respects the per-mode maximum', () => {
    expect(clampContentHeight('compact', 2000, 1040)).toBe(480)
    expect(clampContentHeight('expanded', 2000, 1040)).toBe(860)
  })

  it('passes through content heights inside the bounds', () => {
    expect(clampContentHeight('compact', 236, 1040)).toBe(236)
    expect(clampContentHeight('expanded', 555.4, 1040)).toBe(555)
  })

  it('never exceeds the work area', () => {
    expect(clampContentHeight('expanded', 800, 600)).toBe(576)
  })
})

describe('placeWindow', () => {
  it('keeps a fitting window anchored at its current top-left', () => {
    const rect = placeWindow({ x: 100, y: 100 }, WINDOW_MODES.expanded, workArea)
    expect(rect).toEqual({ x: 100, y: 100, width: 560, height: 620 })
  })

  it('clamps when growth would overflow the right edge', () => {
    const rect = placeWindow({ x: 1800, y: 100 }, WINDOW_MODES.compact, workArea)
    expect(rect.x).toBe(1920 - 520)
  })

  it('clamps when growth would overflow the bottom edge', () => {
    const rect = placeWindow({ x: 100, y: 1000 }, WINDOW_MODES.expanded, workArea)
    expect(rect.y).toBe(1040 - 620)
  })

  it('handles negative multi-monitor coordinates', () => {
    const leftMonitor = { x: -1920, y: 0, width: 1920, height: 1040 }
    const rect = placeWindow({ x: -100, y: 900 }, WINDOW_MODES.expanded, leftMonitor)
    expect(rect.x).toBe(-560)
    expect(rect.y).toBe(1040 - 620)
    expect(rect.x).toBeGreaterThanOrEqual(leftMonitor.x)
  })

  it('pins to the work-area origin when the window is larger than the area', () => {
    const tiny = { x: 0, y: 0, width: 400, height: 300 }
    const rect = placeWindow({ x: 50, y: 50 }, WINDOW_MODES.expanded, tiny)
    expect(rect.x).toBe(0)
    expect(rect.y).toBe(0)
  })
})

describe('defaultPosition', () => {
  it('sits in the bottom-right with a margin', () => {
    const pos = defaultPosition(workArea, WINDOW_MODES.eye)
    expect(pos).toEqual({
      x: 1920 - WINDOW_MODES.eye.width - 24,
      y: 1040 - WINDOW_MODES.eye.height - 24
    })
  })

  it('reserves enough room for the tray to unfold without moving the eye', () => {
    const pos = defaultPosition(workArea, EYE_TRAY_SIZE)
    const opened = placeWindow(pos, EYE_TRAY_SIZE, workArea)
    expect(opened).toEqual({ ...pos, ...EYE_TRAY_SIZE })
    expect(pos.y).toBe(1040 - EYE_TRAY_SIZE.height - 24)
  })
})

describe('isVisibleOnAny', () => {
  const areas = [workArea, { x: -1920, y: 0, width: 1920, height: 1040 }]

  it('accepts a position fully inside a display', () => {
    expect(isVisibleOnAny({ x: 500, y: 500 }, WINDOW_MODES.eye, areas)).toBe(true)
  })

  it('accepts a position on a secondary display', () => {
    expect(isVisibleOnAny({ x: -1000, y: 200 }, WINDOW_MODES.eye, areas)).toBe(true)
  })

  it('rejects a position on a disconnected display', () => {
    expect(isVisibleOnAny({ x: 4000, y: 200 }, WINDOW_MODES.eye, areas)).toBe(false)
  })

  it('rejects a sliver of overlap smaller than the threshold', () => {
    // Only 20px of the window remains on-screen.
    expect(isVisibleOnAny({ x: 1900, y: 500 }, WINDOW_MODES.eye, areas)).toBe(false)
  })
})

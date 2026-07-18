import { screen, type BrowserWindow } from 'electron'

const TICK_MS = 16
const CLICK_THRESHOLD_PX = 5
const MAX_DRAG_MS = 20_000

/**
 * Grab-anywhere dragging for the eye itself. CSS app-region drag swallows
 * clicks, so the visible eye uses manual dragging instead: the renderer
 * reports pointer down/up, main moves the window with the global cursor, and
 * a release that never moved past the threshold counts as a click.
 */
export class DragController {
  private timer: ReturnType<typeof setInterval> | null = null
  private startedAt = 0
  private startCursor = { x: 0, y: 0 }
  private startWindow = { x: 0, y: 0 }
  private maxDelta = 0

  constructor(private win: BrowserWindow) {
    win.on('blur', () => this.stop())
  }

  begin(): void {
    this.stop()
    const cursor = screen.getCursorScreenPoint()
    const [x, y] = this.win.getPosition()
    this.startCursor = { x: cursor.x, y: cursor.y }
    this.startWindow = { x, y }
    this.maxDelta = 0
    this.startedAt = Date.now()
    this.timer = setInterval(() => {
      if (this.win.isDestroyed() || Date.now() - this.startedAt > MAX_DRAG_MS) {
        this.stop()
        return
      }
      const p = screen.getCursorScreenPoint()
      const dx = p.x - this.startCursor.x
      const dy = p.y - this.startCursor.y
      this.maxDelta = Math.max(this.maxDelta, Math.abs(dx), Math.abs(dy))
      // Stay put until the threshold passes so a click never jitters the eye.
      if (this.maxDelta >= CLICK_THRESHOLD_PX) {
        this.win.setPosition(this.startWindow.x + dx, this.startWindow.y + dy)
      }
    }, TICK_MS)
  }

  end(): { wasClick: boolean } {
    const wasClick = this.timer !== null && this.maxDelta < CLICK_THRESHOLD_PX
    this.stop()
    return { wasClick }
  }

  private stop(): void {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  }
}

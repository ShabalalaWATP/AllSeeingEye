import { screen, type BrowserWindow } from 'electron'
import { EYE_CENTRE } from './core/window-modes'

// Electron has no global mouse-move event, so the desktop-wide gaze is fed by
// polling the cursor position. 30 Hz is plenty for a smoothed pupil and costs
// effectively nothing.
const POLL_MS = 33
const MIN_DELTA_PX = 2

export function startCursorFeed(win: BrowserWindow): () => void {
  let lastDx = Number.NaN
  let lastDy = Number.NaN
  const timer = setInterval(() => {
    if (win.isDestroyed() || !win.isVisible()) return
    const p = screen.getCursorScreenPoint()
    const b = win.getBounds()
    const dx = p.x - (b.x + EYE_CENTRE.x)
    const dy = p.y - (b.y + EYE_CENTRE.y)
    if (Math.abs(dx - lastDx) < MIN_DELTA_PX && Math.abs(dy - lastDy) < MIN_DELTA_PX) return
    lastDx = dx
    lastDy = dy
    win.webContents.send('cursor:pos', { dx, dy })
  }, POLL_MS)
  return () => clearInterval(timer)
}

import { desktopCapturer, screen, type BrowserWindow } from 'electron'
import { CaptureError } from './core/errors'

const SETTLE_MS = 150
const MAX_LONG_EDGE = 2000
const JPEG_QUALITY = 75

export const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Ephemeral capture of the display under the cursor.
 *
 * The companion window is made invisible with setOpacity(0) rather than
 * hide(): opacity changes never touch focus, z-order or the taskbar, so the
 * foreground app keeps focus throughout. The image lives only in memory as a
 * JPEG data URL; nothing is written to disk and image bytes are never logged.
 */
export async function captureDisplayUnderCursor(win: BrowserWindow): Promise<string> {
  const point = screen.getCursorScreenPoint()
  const display = screen.getDisplayNearestPoint(point)
  try {
    win.setOpacity(0)
    await delay(SETTLE_MS)
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      // DPI-correct size, otherwise text on scaled displays captures blurry.
      thumbnailSize: {
        width: Math.round(display.size.width * display.scaleFactor),
        height: Math.round(display.size.height * display.scaleFactor)
      }
    })
    // display_id can be empty on some Windows configurations; fall back to
    // index order, then to the first source.
    const byId = sources.find((s) => s.display_id === String(display.id))
    const index = screen.getAllDisplays().findIndex((d) => d.id === display.id)
    const source = byId ?? sources[index] ?? sources[0]
    if (!source || source.thumbnail.isEmpty()) throw new CaptureError('no screen source')

    let img = source.thumbnail
    const size = img.getSize()
    if (Math.max(size.width, size.height) > MAX_LONG_EDGE) {
      img =
        size.width >= size.height
          ? img.resize({ width: MAX_LONG_EDGE })
          : img.resize({ height: MAX_LONG_EDGE })
    }
    const jpeg = img.toJPEG(JPEG_QUALITY)
    if (jpeg.length === 0) throw new CaptureError('jpeg encode failed')
    console.log(`[capture] display ${display.id} captured (${jpeg.length} bytes)`)
    return `data:image/jpeg;base64,${jpeg.toString('base64')}`
  } catch (err) {
    throw err instanceof CaptureError ? err : new CaptureError(String(err))
  } finally {
    // Restore before the (slow) OpenAI call so the thinking state is visible.
    if (!win.isDestroyed()) win.setOpacity(1)
  }
}

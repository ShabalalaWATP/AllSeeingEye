import { randomUUID } from 'node:crypto'
import { desktopCapturer, screen, type BrowserWindow, type NativeImage } from 'electron'
import type {
  CaptureSourceBatch,
  CaptureSourceKind,
  CaptureSourceOption,
  CaptureTarget
} from '../shared/types'
import { CaptureError } from './core/errors'

const SETTLE_MS = 150
const MAX_LONG_EDGE = 2560
const MAX_CAPTURE_BYTES = 8 * 1024 * 1024
const JPEG_QUALITY = 75
const PREVIEW_QUALITY = 55
const BATCH_TTL_MS = 60_000
const MAX_LIVE_BATCHES = 6
const PREVIEW_SIZE = { width: 320, height: 180 }

interface StoredSource {
  sourceId: string
  kind: CaptureSourceKind
}

interface StoredBatch {
  expiresAt: number
  sources: Map<string, StoredSource>
}

const batches = new Map<string, StoredBatch>()

export const delay = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

function cleanLabel(value: string): string {
  return value
    .normalize('NFKC')
    .replace(/[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, '')
    .trim()
    .slice(0, 120) || 'Untitled source'
}

function previewDataUrl(image: NativeImage): string | null {
  if (image.isEmpty()) return null
  const jpeg = image.toJPEG(PREVIEW_QUALITY)
  return jpeg.length > 0 ? `data:image/jpeg;base64,${jpeg.toString('base64')}` : null
}

function removeExpiredBatches(now = Date.now()): void {
  for (const [batchId, batch] of batches) {
    if (batch.expiresAt <= now) batches.delete(batchId)
  }
}

/** Enumerates small, local-only previews and replaces raw Electron IDs with expiring tokens. */
export async function listCaptureSources(
  win: BrowserWindow,
  kind: CaptureSourceKind
): Promise<CaptureSourceBatch> {
  removeExpiredBatches()
  const ownSourceId = win.getMediaSourceId()
  const sources = await desktopCapturer.getSources({
    types: [kind === 'display' ? 'screen' : 'window'],
    thumbnailSize: PREVIEW_SIZE,
    fetchWindowIcons: kind === 'window'
  })
  const batchId = randomUUID()
  const expiresAt = Date.now() + BATCH_TTL_MS
  const stored = new Map<string, StoredSource>()
  const options: CaptureSourceOption[] = []
  for (const source of sources) {
    if (source.id === ownSourceId) continue
    const token = randomUUID()
    stored.set(token, { sourceId: source.id, kind })
    options.push({
      token,
      kind,
      label: cleanLabel(source.name),
      previewDataUrl: previewDataUrl(source.thumbnail)
    })
  }
  while (batches.size >= MAX_LIVE_BATCHES) {
    const oldest = batches.keys().next().value as string | undefined
    if (!oldest) break
    batches.delete(oldest)
  }
  batches.set(batchId, { expiresAt, sources: stored })
  return { batchId, expiresAt, sources: options }
}

function encodeCapture(image: NativeImage): string {
  if (image.isEmpty()) throw new CaptureError('selected source returned no image')
  let bounded = image
  const size = image.getSize()
  if (Math.max(size.width, size.height) > MAX_LONG_EDGE) {
    bounded = size.width >= size.height
      ? image.resize({ width: MAX_LONG_EDGE })
      : image.resize({ height: MAX_LONG_EDGE })
  }
  const jpeg = bounded.toJPEG(JPEG_QUALITY)
  if (jpeg.length === 0) throw new CaptureError('jpeg encode failed')
  if (jpeg.length > MAX_CAPTURE_BYTES) throw new CaptureError('captured image exceeds memory limit')
  console.log(`[capture] source captured (${jpeg.length} bytes)`)
  return `data:image/jpeg;base64,${jpeg.toString('base64')}`
}

async function captureSelected(win: BrowserWindow, batchId: string, token: string): Promise<string> {
  removeExpiredBatches()
  const batch = batches.get(batchId)
  batches.delete(batchId)
  if (!batch || batch.expiresAt <= Date.now()) throw new CaptureError('capture selection expired')
  const selected = batch.sources.get(token)
  if (!selected) throw new CaptureError('invalid capture selection')

  try {
    if (selected.kind === 'display') {
      win.setOpacity(0)
      await delay(SETTLE_MS)
    }
    const sources = await desktopCapturer.getSources({
      types: [selected.kind === 'display' ? 'screen' : 'window'],
      thumbnailSize: { width: MAX_LONG_EDGE, height: MAX_LONG_EDGE }
    })
    const source = sources.find((item) => item.id === selected.sourceId)
    if (!source) throw new CaptureError('selected source is no longer available')
    return encodeCapture(source.thumbnail)
  } catch (error) {
    throw error instanceof CaptureError ? error : new CaptureError(String(error))
  } finally {
    if (!win.isDestroyed()) win.setOpacity(1)
  }
}

/** Ephemeral capture of the display under the cursor. */
export async function captureDisplayUnderCursor(win: BrowserWindow): Promise<string> {
  const point = screen.getCursorScreenPoint()
  const display = screen.getDisplayNearestPoint(point)
  try {
    win.setOpacity(0)
    await delay(SETTLE_MS)
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: {
        width: Math.round(display.size.width * display.scaleFactor),
        height: Math.round(display.size.height * display.scaleFactor)
      }
    })
    const source = sources.find((item) => item.display_id === String(display.id))
    if (!source) throw new CaptureError('display under pointer is unavailable')
    return encodeCapture(source.thumbnail)
  } catch (error) {
    throw error instanceof CaptureError ? error : new CaptureError(String(error))
  } finally {
    if (!win.isDestroyed()) win.setOpacity(1)
  }
}

export function captureTarget(win: BrowserWindow, target: CaptureTarget): Promise<string> {
  return target.type === 'display-under-pointer'
    ? captureDisplayUnderCursor(win)
    : captureSelected(win, target.batchId, target.token)
}

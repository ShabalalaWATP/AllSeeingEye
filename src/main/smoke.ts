import { app, desktopCapturer, screen } from 'electron'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { captureDisplayUnderCursor, delay } from './capture'
import { WINDOW_MODES } from './core/window-modes'
import { hasApiKey } from './openai-client'
import type { AnalysisController } from './analysis'
import type { WindowManager } from './window'

/**
 * DEV-ONLY verification harness, never active in packaged builds and only
 * when CRITICAL_EYE_SMOKE=1 is set explicitly. It writes verification
 * captures to a temp directory so a developer can confirm that (a) the eye
 * renders transparently over the desktop, (b) the real pipeline excludes the
 * eye from its own screenshot, and optionally (c) the complete analysis flow
 * produces a finding bubble. Normal app operation never writes any capture
 * to disk.
 */

async function capturePrimaryPng(): Promise<Buffer | null> {
  const display = screen.getPrimaryDisplay()
  const sources = await desktopCapturer.getSources({
    types: ['screen'],
    thumbnailSize: {
      width: Math.round(display.size.width * display.scaleFactor),
      height: Math.round(display.size.height * display.scaleFactor)
    }
  })
  const source = sources.find((s) => s.display_id === String(display.id)) ?? sources[0]
  return source && !source.thumbnail.isEmpty() ? source.thumbnail.toPNG() : null
}

export async function maybeRunSmoke(wm: WindowManager, controller: AnalysisController): Promise<void> {
  if (process.env.CRITICAL_EYE_SMOKE !== '1' || app.isPackaged) return
  const dir = process.env.CRITICAL_EYE_SMOKE_DIR ?? tmpdir()
  console.log(`[smoke] writing verification captures to ${dir}`)

  // Surface renderer console output (e.g. shader compile errors) in stdout.
  wm.win.webContents.on('console-message', (...args: unknown[]) => {
    const details = args[args.length - 1]
    console.log('[renderer]', typeof details === 'string' ? details : JSON.stringify(details))
  })

  // Predictable position on the primary display so the eye is easy to find.
  wm.win.setBounds({ x: 120, y: 120, ...WINDOW_MODES.eye })

  // Wait until the WebGL canvas is actually mounted, then a little longer for
  // the first frames. A fixed delay races the cold dev-server load.
  const deadline = Date.now() + 20_000
  let canvasInfo = 'never appeared'
  while (Date.now() < deadline) {
    try {
      const info = (await wm.win.webContents.executeJavaScript(
        `(() => { const c = document.querySelector('.evil-eye-container canvas');
           return c ? c.width + 'x' + c.height : null })()`
      )) as string | null
      if (info) {
        canvasInfo = info
        break
      }
    } catch {
      // page still loading
    }
    await delay(500)
  }
  console.log(`[smoke] eye canvas: ${canvasInfo}`)
  await delay(2000)

  // 1. Eye visible: proves transparent rendering over the desktop.
  const eyePng = await capturePrimaryPng()
  if (eyePng) {
    writeFileSync(join(dir, 'smoke-eye-visible.png'), eyePng)
    console.log('[smoke] wrote smoke-eye-visible.png')
  }

  try {
    // 2. Real pipeline: the eye must be absent from its own capture.
    const dataUrl = await captureDisplayUnderCursor(wm.win)
    const jpeg = Buffer.from(dataUrl.split(',')[1], 'base64')
    writeFileSync(join(dir, 'smoke-pipeline.jpg'), jpeg)
    console.log(`[smoke] wrote smoke-pipeline.jpg (${jpeg.length} bytes)`)

    // 3. Optional: the complete user-facing flow, ending with the bubble on
    // screen, captured for visual verification of the result window.
    if (process.env.CRITICAL_EYE_SMOKE_OPENAI === '1' && hasApiKey()) {
      console.log('[smoke] running the full analysis flow...')
      const started = Date.now()
      await controller.runScreen()
      const snapshot = controller.snapshot()
      console.log(`[smoke] flow finished in ${Date.now() - started}ms state=${snapshot.state}`)
      console.log(`[smoke] payload: ${JSON.stringify(snapshot.finding ?? snapshot.error)}`)
      await delay(2500) // bubble render plus auto-height fit
      const resultPng = await capturePrimaryPng()
      if (resultPng) {
        writeFileSync(join(dir, 'smoke-result.png'), resultPng)
        console.log('[smoke] wrote smoke-result.png')
      }
    } else if (process.env.CRITICAL_EYE_SMOKE_OPENAI === '1') {
      console.log('[smoke] skipped analysis flow: no API key configured')
    }
  } catch (err) {
    console.error(`[smoke] pipeline failed: ${(err as Error).name}: ${(err as Error).message}`)
  }

  console.log('[smoke] done, quitting')
  app.quit()
}

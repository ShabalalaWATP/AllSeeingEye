import { app, desktopCapturer, screen } from 'electron'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'
import { captureDisplayUnderCursor, delay } from './capture'
import { analyseImage, hasApiKey } from './openai-client'
import type { WindowManager } from './window'

/**
 * DEV-ONLY verification harness, never active in packaged builds and only
 * when CRITICAL_EYE_SMOKE=1 is set explicitly. It writes two verification
 * captures to a temp directory so a developer can confirm that (a) the eye
 * renders transparently over the desktop and (b) the real pipeline excludes
 * the eye from its own screenshot. Normal app operation never writes any
 * capture to disk.
 */
export async function maybeRunSmoke(wm: WindowManager): Promise<void> {
  if (process.env.CRITICAL_EYE_SMOKE !== '1' || app.isPackaged) return
  const dir = process.env.CRITICAL_EYE_SMOKE_DIR ?? tmpdir()
  console.log(`[smoke] writing verification captures to ${dir}`)

  // Surface renderer console output (e.g. shader compile errors) in stdout.
  wm.win.webContents.on('console-message', (...args: unknown[]) => {
    const details = args[args.length - 1]
    console.log('[renderer]', typeof details === 'string' ? details : JSON.stringify(details))
  })

  // Predictable position on the primary display so the eye is easy to find.
  wm.win.setBounds({ x: 120, y: 120, width: 160, height: 200 })

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
  const display = screen.getPrimaryDisplay()
  const sources = await desktopCapturer.getSources({
    types: ['screen'],
    thumbnailSize: {
      width: Math.round(display.size.width * display.scaleFactor),
      height: Math.round(display.size.height * display.scaleFactor)
    }
  })
  const source = sources.find((s) => s.display_id === String(display.id)) ?? sources[0]
  if (source) {
    writeFileSync(join(dir, 'smoke-eye-visible.png'), source.thumbnail.toPNG())
    console.log('[smoke] wrote smoke-eye-visible.png')
  }

  // 2. Real pipeline: the eye must be absent from its own capture.
  try {
    const dataUrl = await captureDisplayUnderCursor(wm.win)
    const jpeg = Buffer.from(dataUrl.split(',')[1], 'base64')
    writeFileSync(join(dir, 'smoke-pipeline.jpg'), jpeg)
    console.log(`[smoke] wrote smoke-pipeline.jpg (${jpeg.length} bytes)`)

    // 3. Optional live API round trip.
    if (process.env.CRITICAL_EYE_SMOKE_OPENAI === '1' && hasApiKey()) {
      console.log('[smoke] calling OpenAI...')
      const t0 = Date.now()
      const finding = await analyseImage(dataUrl, 'general')
      console.log(`[smoke] finding in ${Date.now() - t0}ms: ${JSON.stringify(finding)}`)
    } else if (process.env.CRITICAL_EYE_SMOKE_OPENAI === '1') {
      console.log('[smoke] skipped OpenAI call: no API key configured')
    }
  } catch (err) {
    console.error(`[smoke] pipeline failed: ${(err as Error).name}: ${(err as Error).message}`)
  }

  console.log('[smoke] done, quitting')
  app.quit()
}

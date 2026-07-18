import { app } from 'electron'
import { config as loadDotenv } from 'dotenv'
import { dirname, join } from 'node:path'
import { PrefsStore } from './prefs'
import { WindowManager } from './window'
import { AnalysisController } from './analysis'
import { DragController } from './drag'
import { registerIpc } from './ipc'
import { attachContextMenu } from './context-menu'
import { registerShortcuts, unregisterShortcuts } from './shortcuts'
import { startCursorFeed } from './cursor'
import { maybeRunSmoke } from './smoke'

function main(): void {
  // One eye is quite enough: a second launch focuses the existing instance.
  if (!app.requestSingleInstanceLock()) {
    app.quit()
    return
  }

  // Dev: .env at the project root. Packaged: also read a .env placed beside
  // the exe (demo machines rarely have system-wide variables set). Portable
  // builds extract to a temp dir, so PORTABLE_EXECUTABLE_DIR is the real
  // location. dotenv never overrides variables already in the environment.
  loadDotenv()
  if (app.isPackaged) {
    const exeDir = process.env.PORTABLE_EXECUTABLE_DIR ?? dirname(process.execPath)
    loadDotenv({ path: join(exeDir, '.env') })
  }

  void app.whenReady().then(() => {
    const prefs = new PrefsStore()
    const wm = new WindowManager(prefs)
    const controller = new AnalysisController(wm, prefs)

    // First run: open at compact size so the privacy notice has room.
    if (!prefs.get().privacyNoticeDismissed) wm.setMode('compact')

    registerIpc(controller, prefs, new DragController(wm.win))
    attachContextMenu(wm, controller)
    registerShortcuts({
      analyse: () => void controller.runScreen(),
      toggleVisibility: () => wm.toggleVisibility(),
      togglePause: () => controller.togglePause()
    })
    const stopCursorFeed = startCursorFeed(wm.win)

    app.on('second-instance', () => {
      if (!wm.win.isDestroyed()) wm.win.showInactive()
    })
    app.on('will-quit', () => {
      unregisterShortcuts()
      stopCursorFeed()
    })

    void maybeRunSmoke(wm)
  })

  app.on('window-all-closed', () => app.quit())
}

main()

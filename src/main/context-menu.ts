import { Menu } from 'electron'
import type { AnalysisController } from './analysis'
import type { WindowManager } from './window'

/** Right-click remains a keyboard/pointer fallback for the hover input tray. */
export function attachContextMenu(wm: WindowManager, controller: AnalysisController): void {
  wm.win.webContents.on('context-menu', (event) => {
    event.preventDefault()
    if (wm.mode === 'eye') {
      wm.win.webContents.send('ui', { action: 'open-launcher' })
      return
    }

    // Panel modes keep operational controls available for the frameless,
    // taskbar-less app, including its guaranteed Quit affordance.
    const openInput = (action: 'open-screen' | 'open-window' | 'open-text' | 'open-voice'): void => {
      controller.setWindowMode('expanded')
      wm.win.webContents.send('ui', { action })
    }
    const menu = Menu.buildFromTemplate([
      { label: 'Share a screen…', click: () => openInput('open-screen') },
      { label: 'Share a window…', click: () => openInput('open-window') },
      { label: 'Write a text note…', click: () => openInput('open-text') },
      { label: 'Record a voice note…', click: () => openInput('open-voice') },
      { type: 'separator' },
      {
        label: 'Quick analyse screen under pointer',
        click: () => void controller.runScreen()
      },
      { type: 'separator' },
      { label: controller.isPaused ? 'Resume' : 'Pause', click: () => controller.togglePause() },
      { label: wm.win.isVisible() ? 'Hide' : 'Show', click: () => wm.toggleVisibility() },
      { type: 'separator' },
      { label: 'Quit AllSeeingEye', click: () => controller.quit() }
    ])
    menu.popup({ window: wm.win })
  })
}

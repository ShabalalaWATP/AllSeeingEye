import { Menu } from 'electron'
import type { AnalysisController } from './analysis'
import type { WindowManager } from './window'

/**
 * Minimal right-click menu. Handled entirely in main via the context-menu
 * event, which only fires over no-drag regions, exactly where we want it.
 * This is also the guaranteed quit affordance for a frameless, taskbar-less,
 * always-on-top window.
 */
export function attachContextMenu(wm: WindowManager, controller: AnalysisController): void {
  wm.win.webContents.on('context-menu', (event) => {
    event.preventDefault()
    const menu = Menu.buildFromTemplate([
      { label: 'Analyse this screen', click: () => void controller.runScreen() },
      {
        label: 'Open text analysis',
        click: () => {
          controller.setWindowMode('expanded')
          wm.win.webContents.send('ui', { action: 'open-text' })
        }
      },
      { label: controller.isPaused ? 'Resume' : 'Pause', click: () => controller.togglePause() },
      { label: wm.win.isVisible() ? 'Hide' : 'Show', click: () => wm.toggleVisibility() },
      { type: 'separator' },
      { label: 'Quit Critical Eye', click: () => controller.quit() }
    ])
    menu.popup({ window: wm.win })
  })
}

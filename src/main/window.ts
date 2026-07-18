import { app, BrowserWindow, screen } from 'electron'
import { join } from 'node:path'
import {
  WINDOW_MODES,
  clampContentHeight,
  defaultPosition,
  isVisibleOnAny,
  placeWindow
} from './core/window-modes'
import type { PrefsStore } from './prefs'
import type { WindowMode } from '../shared/types'

const SAVE_DEBOUNCE_MS = 500

export class WindowManager {
  readonly win: BrowserWindow
  private windowMode: WindowMode = 'eye'
  private saveTimer: ReturnType<typeof setTimeout> | null = null

  constructor(private prefs: PrefsStore) {
    const size = WINDOW_MODES.eye
    const saved = prefs.get()
    const workAreas = screen.getAllDisplays().map((d) => d.workArea)
    const primary = screen.getPrimaryDisplay().workArea
    const pos =
      saved.x >= 0 && isVisibleOnAny({ x: saved.x, y: saved.y }, size, workAreas)
        ? { x: saved.x, y: saved.y }
        : defaultPosition(primary, size)

    this.win = new BrowserWindow({
      ...pos,
      width: size.width,
      height: size.height,
      show: false,
      frame: false,
      transparent: true,
      resizable: false,
      alwaysOnTop: true,
      skipTaskbar: true,
      hasShadow: false,
      minimizable: false,
      maximizable: false,
      fullscreenable: false,
      webPreferences: {
        preload: join(__dirname, '../preload/index.js'),
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        spellcheck: false
      }
    })
    this.win.setAlwaysOnTop(true, 'screen-saver')
    this.win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
    this.win.webContents.on('will-navigate', (e) => e.preventDefault())
    this.win.on('moved', () => this.scheduleSave())
    // showInactive keeps focus with whatever the user is working on.
    this.win.once('ready-to-show', () => this.win.showInactive())

    if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
      void this.win.loadURL(process.env['ELECTRON_RENDERER_URL'])
    } else {
      void this.win.loadFile(join(__dirname, '../renderer/index.html'))
    }
    if (!app.isPackaged && process.env.CRITICAL_EYE_DEVTOOLS === '1') {
      this.win.webContents.openDevTools({ mode: 'detach' })
    }
  }

  get mode(): WindowMode {
    return this.windowMode
  }

  /** Resize in one shot (the animate flag is macOS-only); clamp to work area. */
  setMode(mode: WindowMode): void {
    this.windowMode = mode
    const bounds = this.win.getBounds()
    const workArea = screen.getDisplayMatching(bounds).workArea
    this.win.setBounds(placeWindow(bounds, WINDOW_MODES[mode], workArea))
  }

  /** Fit the panel height to the renderer's measured content height. */
  fitHeight(contentHeight: number): void {
    const bounds = this.win.getBounds()
    const workArea = screen.getDisplayMatching(bounds).workArea
    const height = clampContentHeight(this.windowMode, contentHeight, workArea.height)
    if (height === null || height === bounds.height) return
    const width = WINDOW_MODES[this.windowMode].width
    this.win.setBounds(placeWindow(bounds, { width, height }, workArea))
  }

  toggleVisibility(): void {
    if (this.win.isVisible()) this.win.hide()
    else this.win.showInactive()
  }

  private scheduleSave(): void {
    if (this.saveTimer) clearTimeout(this.saveTimer)
    this.saveTimer = setTimeout(() => {
      if (this.win.isDestroyed()) return
      const b = this.win.getBounds()
      this.prefs.set({ x: b.x, y: b.y })
    }, SAVE_DEBOUNCE_MS)
  }
}

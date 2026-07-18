import { app, BrowserWindow, screen } from 'electron'
import { join } from 'node:path'
import {
  EYE_TRAY_SIZE,
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
  private ignoreNextMovedEvent = false

  constructor(private prefs: PrefsStore) {
    const size = WINDOW_MODES.eye
    const safeEyeSize = EYE_TRAY_SIZE
    const saved = prefs.get()
    const workAreas = screen.getAllDisplays().map((d) => d.workArea)
    const primary = screen.getPrimaryDisplay().workArea
    const savedPosition = { x: saved.x, y: saved.y }
    const pos = saved.x >= 0 && isVisibleOnAny(savedPosition, safeEyeSize, workAreas)
      ? (() => {
          const workArea = screen.getDisplayMatching({ ...savedPosition, ...safeEyeSize }).workArea
          const placed = placeWindow(savedPosition, safeEyeSize, workArea)
          return { x: placed.x, y: placed.y }
        })()
      : defaultPosition(primary, safeEyeSize)

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
    const ownsRequest = (contents: Electron.WebContents | null, requestingUrl: string): boolean =>
      contents === this.win.webContents && requestingUrl.split('#')[0] === this.win.webContents.getURL().split('#')[0]
    this.win.webContents.session.setPermissionCheckHandler(
      (contents, permission, requestingOrigin, details) =>
        permission === 'media' &&
        details.isMainFrame &&
        details.mediaType === 'audio' &&
        ownsRequest(contents, details.requestingUrl ?? requestingOrigin)
    )
    this.win.webContents.session.setPermissionRequestHandler(
      (contents, permission, callback, details) => {
        const mediaTypes = 'mediaTypes' in details ? details.mediaTypes ?? [] : []
        callback(
          permission === 'media' &&
          details.isMainFrame &&
          mediaTypes.length > 0 &&
          mediaTypes.every((item) => item === 'audio') &&
          ownsRequest(contents, details.requestingUrl)
        )
      }
    )
    this.win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }))
    this.win.webContents.on('will-navigate', (e) => e.preventDefault())
    this.win.on('moved', () => {
      if (this.ignoreNextMovedEvent) {
        this.ignoreNextMovedEvent = false
        return
      }
      const { x, y } = this.win.getBounds()
      this.scheduleSave({ x, y })
    })
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
    if (mode === 'eye') {
      const safe = placeWindow(bounds, EYE_TRAY_SIZE, workArea)
      this.win.setBounds({ x: safe.x, y: safe.y, ...WINDOW_MODES.eye })
      return
    }
    this.win.setBounds(placeWindow(bounds, WINDOW_MODES[mode], workArea))
  }

  /** Expand only the eye surface so its input tray can sit below the eye. */
  setEyeTrayOpen(open: boolean): void {
    if (this.windowMode !== 'eye') return
    const bounds = this.win.getBounds()
    const workArea = screen.getDisplayMatching(bounds).workArea
    const target = open ? EYE_TRAY_SIZE : WINDOW_MODES.eye
    const placed = placeWindow(bounds, target, workArea)
    if (placed.x !== bounds.x || placed.y !== bounds.y) this.ignoreNextMovedEvent = true
    this.win.setBounds(placed)
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

  private scheduleSave(position: { x: number; y: number }): void {
    if (this.saveTimer) clearTimeout(this.saveTimer)
    this.saveTimer = setTimeout(() => {
      if (this.win.isDestroyed()) return
      if (this.windowMode !== 'eye') {
        this.prefs.set(position)
        return
      }
      const workArea = screen.getDisplayMatching({ ...position, ...EYE_TRAY_SIZE }).workArea
      const safe = placeWindow(position, EYE_TRAY_SIZE, workArea)
      if (safe.x !== position.x || safe.y !== position.y) {
        this.ignoreNextMovedEvent = true
        this.win.setPosition(safe.x, safe.y)
      }
      this.prefs.set({ x: safe.x, y: safe.y })
    }, SAVE_DEBOUNCE_MS)
  }
}

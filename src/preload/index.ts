import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron'

// The renderer sees ONLY this narrow, typed surface. Raw ipcRenderer, send,
// invoke and event objects are never exposed.

type Unsubscribe = () => void

function subscribe(channel: string, callback: (payload: unknown) => void): Unsubscribe {
  const listener = (_event: IpcRendererEvent, payload: unknown): void => callback(payload)
  ipcRenderer.on(channel, listener)
  return () => ipcRenderer.removeListener(channel, listener)
}

const api = {
  analyseScreen: (): Promise<void> => ipcRenderer.invoke('analysis:screen'),
  analyseText: (text: string, mode: string): Promise<void> =>
    ipcRenderer.invoke('analysis:text', { text, mode }),
  setWindowMode: (mode: string): Promise<void> => ipcRenderer.invoke('window:set-mode', mode),
  getPreferences: (): Promise<unknown> => ipcRenderer.invoke('prefs:get'),
  updatePreferences: (update: unknown): Promise<unknown> =>
    ipcRenderer.invoke('prefs:update', update),
  togglePause: (): Promise<void> => ipcRenderer.invoke('app:toggle-pause'),
  dismiss: (): Promise<void> => ipcRenderer.invoke('app:dismiss'),
  collapse: (): Promise<void> => ipcRenderer.invoke('app:collapse'),
  quit: (): Promise<void> => ipcRenderer.invoke('app:quit'),
  requestState: (): Promise<void> => ipcRenderer.invoke('state:request'),
  onState: (callback: (payload: unknown) => void): Unsubscribe => subscribe('state', callback),
  onCursor: (callback: (payload: unknown) => void): Unsubscribe =>
    subscribe('cursor:pos', callback),
  onUi: (callback: (payload: unknown) => void): Unsubscribe => subscribe('ui', callback)
}

contextBridge.exposeInMainWorld('criticalEye', api)

export type CriticalEyeBridge = typeof api

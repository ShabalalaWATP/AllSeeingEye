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
  analyseScreen: (focusQuestion = '', depth?: string, target?: unknown): Promise<void> =>
    ipcRenderer.invoke('analysis:screen', { focusQuestion, depth, target }),
  listCaptureSources: (kind: string): Promise<unknown> =>
    ipcRenderer.invoke('capture:list-sources', kind),
  dragBegin: (): Promise<void> => ipcRenderer.invoke('drag:begin'),
  dragEnd: (): Promise<unknown> => ipcRenderer.invoke('drag:end'),
  analyseText: (text: string, mode: string, focusQuestion = '', depth?: string): Promise<void> =>
    ipcRenderer.invoke('analysis:text', { text, mode, focusQuestion, depth }),
  analyseVoice: (
    sessionId: string,
    bytes: ArrayBuffer,
    mimeType: string,
    durationMs: number,
    mode: string,
    focusQuestion = '',
    depth?: string
  ): Promise<boolean | undefined> => ipcRenderer.invoke(
    'analysis:voice',
    { sessionId, bytes, mimeType, durationMs, mode, focusQuestion, depth }
  ),
  beginVoiceRecording: (): Promise<string | undefined> =>
    ipcRenderer.invoke('voice:begin-recording'),
  cancelVoiceRecording: (sessionId: string): Promise<void> =>
    ipcRenderer.invoke('voice:cancel-recording', sessionId),
  runFullReview: (runId: string): Promise<boolean | undefined> =>
    ipcRenderer.invoke('analysis:full-review', { runId }),
  setWindowMode: (mode: string): Promise<void> => ipcRenderer.invoke('window:set-mode', mode),
  setEyeTrayOpen: (open: boolean): Promise<void> =>
    ipcRenderer.invoke('window:set-eye-tray-open', open),
  fitHeight: (height: number): Promise<void> => ipcRenderer.invoke('window:fit-height', height),
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

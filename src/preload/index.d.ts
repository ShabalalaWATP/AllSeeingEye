import type {
  AnalysisMode,
  CursorPayload,
  Preferences,
  StatePayload,
  WindowMode
} from '../shared/types'

type Unsubscribe = () => void

export interface CriticalEyeApi {
  analyseScreen: () => Promise<void>
  dragBegin: () => Promise<void>
  dragEnd: () => Promise<{ wasClick: boolean }>
  analyseText: (text: string, mode: AnalysisMode) => Promise<void>
  setWindowMode: (mode: WindowMode) => Promise<void>
  fitHeight: (height: number) => Promise<void>
  getPreferences: () => Promise<Preferences>
  updatePreferences: (
    update: Partial<Pick<Preferences, 'mode' | 'privacyNoticeDismissed' | 'startPaused'>>
  ) => Promise<Preferences>
  togglePause: () => Promise<void>
  dismiss: () => Promise<void>
  collapse: () => Promise<void>
  quit: () => Promise<void>
  requestState: () => Promise<void>
  onState: (callback: (payload: StatePayload) => void) => Unsubscribe
  onCursor: (callback: (payload: CursorPayload) => void) => Unsubscribe
  onUi: (callback: (payload: { action: string }) => void) => Unsubscribe
}

declare global {
  interface Window {
    criticalEye: CriticalEyeApi
  }
}

export {}

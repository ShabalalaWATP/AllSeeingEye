import type {
  AnalysisMode,
  CaptureSourceBatch,
  CaptureSourceKind,
  CaptureTarget,
  CursorPayload,
  Preferences,
  ReviewDepth,
  StatePayload,
  VoiceMimeType,
  WindowMode
} from '../shared/types'

type Unsubscribe = () => void

export interface CriticalEyeApi {
  analyseScreen: (
    focusQuestion?: string,
    depth?: ReviewDepth,
    target?: CaptureTarget
  ) => Promise<void>
  listCaptureSources: (kind: CaptureSourceKind) => Promise<CaptureSourceBatch | undefined>
  dragBegin: () => Promise<void>
  dragEnd: () => Promise<{ wasClick: boolean }>
  analyseText: (
    text: string,
    mode: AnalysisMode,
    focusQuestion?: string,
    depth?: ReviewDepth
  ) => Promise<void>
  analyseVoice: (
    sessionId: string,
    bytes: ArrayBuffer,
    mimeType: VoiceMimeType,
    durationMs: number,
    mode: AnalysisMode,
    focusQuestion?: string,
    depth?: ReviewDepth
  ) => Promise<boolean | undefined>
  beginVoiceRecording: () => Promise<string | undefined>
  cancelVoiceRecording: (sessionId: string) => Promise<void>
  runFullReview: (runId: string) => Promise<boolean | undefined>
  setWindowMode: (mode: WindowMode) => Promise<void>
  setEyeTrayOpen: (open: boolean) => Promise<void>
  fitHeight: (height: number) => Promise<void>
  getPreferences: () => Promise<Preferences>
  updatePreferences: (
    update: Partial<
      Pick<Preferences, 'mode' | 'reviewDepth' | 'privacyNoticeDismissed' | 'startPaused'>
    >
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

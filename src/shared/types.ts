// Types shared between the main process, preload and renderer.
// This module must stay dependency-free and side-effect-free.

export const WINDOW_MODE_NAMES = ['eye', 'compact', 'expanded'] as const
export type WindowMode = (typeof WINDOW_MODE_NAMES)[number]

export const ANALYSIS_MODES = ['general', 'strategy', 'security', 'writing', 'delivery'] as const
export type AnalysisMode = (typeof ANALYSIS_MODES)[number]

export const SEVERITIES = ['low', 'medium', 'high'] as const
export type Severity = (typeof SEVERITIES)[number]

export const CATEGORIES = [
  'assumption',
  'logical_gap',
  'contradiction',
  'missing_evidence',
  'security',
  'privacy',
  'feasibility',
  'stakeholder',
  'clarity',
  'bias',
  'other'
] as const
export type FindingCategory = (typeof CATEGORIES)[number]

export interface RedTeamFinding {
  hasMaterialIssue: boolean
  category: FindingCategory
  severity: Severity
  headline: string
  explanation: string
  visibleEvidence: string
  recommendation: string
  confidence: number
}

export type ErrorCode =
  | 'missing_key'
  | 'invalid_key'
  | 'model_unavailable'
  | 'quota'
  | 'rate_limited'
  | 'timeout'
  | 'network'
  | 'bad_response'
  | 'capture_failed'
  | 'unknown'

export interface UserError {
  code: ErrorCode
  message: string
}

export type CompanionState =
  | 'idle'
  | 'capturing'
  | 'analysing'
  | 'result'
  | 'no_issue'
  | 'paused'
  | 'error'

export interface Preferences {
  x: number
  y: number
  mode: AnalysisMode
  privacyNoticeDismissed: boolean
  startPaused: boolean
}

/** Full snapshot pushed from main to the renderer on every change. */
export interface StatePayload {
  state: CompanionState
  windowMode: WindowMode
  analysisMode: AnalysisMode
  paused: boolean
  privacyNoticeDismissed: boolean
  finding: RedTeamFinding | null
  error: UserError | null
}

/** Cursor position relative to the eye centre, in desktop pixels. */
export interface CursorPayload {
  dx: number
  dy: number
}

export const MAX_TEXT_LENGTH = 12_000

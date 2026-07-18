import type { CompanionState } from '../../shared/types'

export const TRANSITIONS: Record<CompanionState, readonly CompanionState[]> = {
  idle: ['capturing', 'recording', 'transcribing', 'analysing', 'paused'],
  capturing: ['analysing', 'error', 'idle'],
  recording: ['transcribing', 'error', 'idle'],
  transcribing: ['analysing', 'error'],
  analysing: ['quick_result', 'result', 'no_issue', 'error'],
  quick_result: ['idle', 'capturing', 'recording', 'transcribing', 'analysing'],
  result: ['idle', 'capturing', 'recording', 'transcribing', 'analysing'],
  no_issue: ['idle', 'capturing', 'recording', 'transcribing', 'analysing'],
  error: ['idle', 'capturing', 'recording', 'transcribing', 'analysing'],
  paused: ['idle']
}

export function canTransition(from: CompanionState, to: CompanionState): boolean {
  return TRANSITIONS[from].includes(to)
}

/** A new analysis may start only when unpaused and nothing is in flight. */
export function canTrigger(paused: boolean, busy: boolean): boolean {
  return !paused && !busy
}

/** The state shown to the user: the paused flag masks a quiet idle state. */
export function displayState(state: CompanionState, paused: boolean): CompanionState {
  if (paused && (state === 'idle' || state === 'paused')) return 'paused'
  return state
}
